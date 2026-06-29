use std::io::BufRead;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use tauri::{Emitter, Manager};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};

mod config;
mod hotkey;
mod sidecar;
pub mod tray;

pub struct SidecarState(pub Mutex<Option<sidecar::Sidecar>>);
pub struct RecordingState(pub Arc<AtomicBool>);
pub struct LogBuffer(pub Mutex<Vec<String>>);

// ─── Commandes Tauri ───────────────────────────────────────────────────────

#[tauri::command]
fn start_recording(
    sidecar: tauri::State<SidecarState>,
    recording: tauri::State<RecordingState>,
    app: tauri::AppHandle,
) -> Result<(), String> {
    recording.0.store(true, Ordering::SeqCst);
    tray::set_recording(&app);
    sidecar.0.lock().unwrap().as_mut().ok_or("sidecar not running")?.send_cmd("start")
}

#[tauri::command]
fn stop_recording(
    sidecar: tauri::State<SidecarState>,
    recording: tauri::State<RecordingState>,
    app: tauri::AppHandle,
) -> Result<(), String> {
    recording.0.store(false, Ordering::SeqCst);
    tray::set_transcribing(&app);
    sidecar.0.lock().unwrap().as_mut().ok_or("sidecar not running")?.send_cmd("stop")
}

/// Retourne l'historique des logs (sidecar + Rust) pour le rejouer à l'ouverture de debug.
#[tauri::command]
fn get_logs(buf: tauri::State<LogBuffer>) -> Vec<String> {
    buf.0.lock().unwrap().clone()
}

/// Relance le téléchargement du modèle (bouton "Réessayer" dans l'UI download).
#[tauri::command]
fn retry_download(state: tauri::State<SidecarState>) -> Result<(), String> {
    state.0.lock().unwrap().as_mut()
        .ok_or("sidecar not running")?
        .send_cmd("download_model")
}

/// Recharge le hotkey à chaud. Appelé par save_settings si hotkey change.
#[tauri::command]
fn reload_hotkey(hotkey_str: String, app: tauri::AppHandle) -> Result<(), String> {
    let shortcut = hotkey::parse_hotkey(&hotkey_str)?;
    app.global_shortcut().unregister_all().map_err(|e| e.to_string())?;
    app.global_shortcut().register(shortcut).map_err(|e| e.to_string())
}

/// Retourne la configuration actuelle pour pré-remplir l'UI settings.
#[tauri::command]
fn get_settings() -> serde_json::Value {
    let cfg = config::read();
    serde_json::json!({
        "model": cfg.model,
        "language": cfg.language,
        "hotkey": cfg.hotkey,
    })
}

#[derive(serde::Deserialize)]
struct Settings {
    model: String,
    language: String,
    hotkey: String,
}

const VALID_MODELS: &[&str] = &["tiny", "base", "small", "medium", "large"];
const VALID_LANGUAGES: &[&str] = &[
    "fr", "en", "de", "es", "it", "pt", "nl", "ru", "zh", "ja", "ko", "auto",
];

/// Persiste les settings, recharge le hotkey, redémarre le sidecar si modèle/langue change.
#[tauri::command]
fn save_settings(
    settings: Settings,
    app: tauri::AppHandle,
    sidecar_st: tauri::State<SidecarState>,
    recording: tauri::State<RecordingState>,
) -> Result<(), String> {
    // Validation
    if !VALID_MODELS.contains(&settings.model.as_str()) {
        return Err(format!("Modèle invalide : {}", settings.model));
    }
    if !VALID_LANGUAGES.contains(&settings.language.as_str()) {
        return Err(format!("Langue invalide : {}", settings.language));
    }
    let shortcut = hotkey::parse_hotkey(&settings.hotkey)
        .map_err(|e| format!("Raccourci invalide : {e}"))?;

    let current = config::read();
    let model_changed = current.model != settings.model;
    let lang_changed = current.language != settings.language;

    config::write(&settings.model, &settings.language, &settings.hotkey)?;

    // Recharger le hotkey immédiatement
    if let Err(e) = app.global_shortcut().unregister_all() {
        log::warn!("Hotkey unregister_all failed: {e}");
    }
    if let Err(e) = app.global_shortcut().register(shortcut) {
        log::warn!("Hotkey reload failed: {e}");
    }

    if model_changed || lang_changed {
        log::info!("Modèle/langue changé — redémarrage sidecar");
        restart_sidecar(&app, &sidecar_st, &recording)?;
    }

    Ok(())
}

// ─── Setup ────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, _shortcut, event| {
                    if event.state() != ShortcutState::Pressed {
                        return;
                    }
                    let was_recording = match app.try_state::<RecordingState>() {
                        Some(s) => s.0.fetch_xor(true, Ordering::SeqCst),
                        None => return,
                    };
                    let cmd = if was_recording { "stop" } else { "start" };
                    if was_recording {
                        tray::set_transcribing(app);
                    } else {
                        tray::set_recording(app);
                    }
                    if let Some(sc_state) = app.try_state::<SidecarState>() {
                        if let Some(sc) = sc_state.0.lock().unwrap().as_mut() {
                            if let Err(e) = sc.send_cmd(cmd) {
                                log::error!("hotkey → sidecar '{cmd}' failed: {e}");
                            }
                        }
                    }
                })
                .build(),
        )
        .setup(|app| {
            app.handle().plugin(
                tauri_plugin_log::Builder::default()
                    .level(log::LevelFilter::Info)
                    .targets([
                        tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::Webview),
                        tauri_plugin_log::Target::new(tauri_plugin_log::TargetKind::Stderr),
                    ])
                    .build(),
            )?;

            app.manage(LogBuffer(Mutex::new(Vec::with_capacity(2000))));

            let recording = Arc::new(AtomicBool::new(false));
            app.manage(RecordingState(Arc::clone(&recording)));

            let (program, script) = resolve_sidecar();
            match sidecar::Sidecar::spawn(&program, script.as_deref()) {
                Ok(mut sc) => {
                    spawn_stdout_reader(app.handle().clone(), &mut sc);
                    spawn_stderr_reader(app.handle().clone(), &mut sc);
                    app.manage(SidecarState(Mutex::new(Some(sc))));
                }
                Err(e) => {
                    log::error!("Sidecar non démarré : {e}");
                    app.manage(SidecarState(Mutex::new(None)));
                }
            }

            // Enregistrer le hotkey configuré
            let hotkey_str = hotkey::read_config_hotkey();
            match hotkey::parse_hotkey(&hotkey_str) {
                Ok(shortcut) => {
                    match app.global_shortcut().register(shortcut) {
                        Ok(_) => log::info!("Hotkey '{hotkey_str}' enregistré"),
                        Err(e) => log::warn!("Hotkey '{hotkey_str}' non enregistré : {e}"),
                    }
                }
                Err(e) => log::warn!("Hotkey '{hotkey_str}' invalide : {e}"),
            }

            if let Err(e) = tray::setup(app) {
                log::warn!("Tray non disponible ({e}) — app sans icône tray");
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_recording,
            stop_recording,
            reload_hotkey,
            get_settings,
            save_settings,
            retry_download,
            get_logs,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// ─── Helpers ──────────────────────────────────────────────────────────────

fn resolve_sidecar() -> (String, Option<String>) {
    if let Ok(python) = std::env::var("WHISPER_PYTHON") {
        return (python, Some("whisper_type.py".into()));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let bundled = dir.join(if cfg!(windows) { "whisper_type.exe" } else { "whisper_type" });
            if bundled.exists() {
                return (bundled.to_string_lossy().into_owned(), None);
            }
        }
    }
    (".venv/bin/python3".into(), Some("whisper_type.py".into()))
}

fn push_log(handle: &tauri::AppHandle, line: &str) {
    if let Some(buf) = handle.try_state::<LogBuffer>() {
        let mut v = buf.0.lock().unwrap();
        if v.len() >= 2000 { v.remove(0); }
        v.push(line.to_string());
    }
    let _ = handle.emit("debug-line", line);
}

fn spawn_stderr_reader(handle: tauri::AppHandle, sc: &mut sidecar::Sidecar) {
    if let Some(reader) = sc.take_stderr() {
        std::thread::spawn(move || {
            for line in reader.lines() {
                if let Ok(line) = line {
                    let _ = handle.emit("sidecar-log", &line);
                    push_log(&handle, &format!("[PY ERR] {line}"));
                }
            }
        });
    }
}

fn spawn_stdout_reader(handle: tauri::AppHandle, sc: &mut sidecar::Sidecar) {
    if let Some(reader) = sc.take_stdout() {
        std::thread::spawn(move || {
            for line in reader.lines() {
                if let Ok(line) = line {
                    log::info!("sidecar → {line}");
                    let _ = handle.emit("sidecar-msg", line.clone());
                    push_log(&handle, &format!("[PY] {line}"));
                    update_tray_from_sidecar(&handle, &line);
                    handle_download_events(&handle, &line);
                }
            }
        });
    }
}

fn handle_download_events(app: &tauri::AppHandle, line: &str) {
    if let Ok(msg) = serde_json::from_str::<serde_json::Value>(line) {
        match msg.get("status").and_then(|v| v.as_str()) {
            Some("model_missing") => {
                if let Some(win) = app.get_webview_window("download") {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
                if let Some(state) = app.try_state::<SidecarState>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(sc) = guard.as_mut() {
                            let _ = sc.send_cmd("download_model");
                        }
                    }
                }
            }
            Some("model_ready") | Some("model_cached") => {
                if let Some(win) = app.get_webview_window("download") {
                    let _ = win.hide();
                }
            }
            _ => {}
        }
    }
}

fn restart_sidecar(
    app: &tauri::AppHandle,
    state: &tauri::State<SidecarState>,
    recording: &tauri::State<RecordingState>,
) -> Result<(), String> {
    recording.0.store(false, Ordering::SeqCst);
    tray::set_idle(app);

    {
        let mut guard = state.0.lock().unwrap();
        if let Some(ref mut sc) = *guard {
            sc.kill();
        }
        *guard = None;
    }

    let (program, script) = resolve_sidecar();
    let mut sc = sidecar::Sidecar::spawn(&program, script.as_deref())
        .map_err(|e| format!("Sidecar restart failed: {e}"))?;

    spawn_stdout_reader(app.clone(), &mut sc);
    spawn_stderr_reader(app.clone(), &mut sc);
    *state.0.lock().unwrap() = Some(sc);
    Ok(())
}

fn update_tray_from_sidecar(app: &tauri::AppHandle, line: &str) {
    if let Ok(msg) = serde_json::from_str::<serde_json::Value>(line) {
        match msg.get("status").and_then(|v| v.as_str()) {
            Some("recording") => tray::set_recording(app),
            Some("transcribing") => tray::set_transcribing(app),
            Some("done") | Some("model_loading") | Some("error") => {
                if let Some(rec) = app.try_state::<RecordingState>() {
                    rec.0.store(false, Ordering::SeqCst);
                }
                tray::set_idle(app);
            }
            _ => {}
        }
    }
}

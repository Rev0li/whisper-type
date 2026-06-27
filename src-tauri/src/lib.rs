use std::io::BufRead;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use tauri::{Emitter, Manager};

mod config;
mod hotkey;
mod sidecar;
pub mod tray;

pub struct SidecarState(pub Mutex<Option<sidecar::Sidecar>>);
pub struct RecordingState(pub Arc<AtomicBool>);
/// None si GlobalHotKeyManager::new() a échoué (Wayland natif sans XWayland).
pub struct HotkeyManagerState(pub Mutex<Option<hotkey::HotkeyManager>>);

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

/// Relance le téléchargement du modèle (bouton "Réessayer" dans l'UI download).
#[tauri::command]
fn retry_download(state: tauri::State<SidecarState>) -> Result<(), String> {
    state.0.lock().unwrap().as_mut()
        .ok_or("sidecar not running")?
        .send_cmd("download_model")
}

/// Recharge le hotkey à chaud (TICKET-05). Appelé par save_settings si hotkey change.
#[tauri::command]
fn reload_hotkey(
    hotkey_str: String,
    hk_state: tauri::State<HotkeyManagerState>,
) -> Result<(), String> {
    match hk_state.0.lock().unwrap().as_mut() {
        Some(mgr) => mgr.register(&hotkey_str),
        None => Err("Hotkey non disponible (Wayland natif sans XWayland)".into()),
    }
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
    hk_state: tauri::State<HotkeyManagerState>,
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
    hotkey::parse_hotkey(&settings.hotkey)
        .map_err(|e| format!("Raccourci invalide : {e}"))?;

    // Lire la config actuelle pour détecter les changements
    let current = config::read();
    let model_changed = current.model != settings.model;
    let lang_changed = current.language != settings.language;

    // Écrire config.toml
    config::write(&settings.model, &settings.language, &settings.hotkey)?;

    // Recharger le hotkey immédiatement (pas de redémarrage sidecar requis)
    if let Some(mgr) = hk_state.0.lock().unwrap().as_mut() {
        if let Err(e) = mgr.register(&settings.hotkey) {
            log::warn!("Hotkey reload failed: {e}");
        }
    }

    // Redémarrer le sidecar seulement si modèle ou langue change
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
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let recording = Arc::new(AtomicBool::new(false));
            app.manage(RecordingState(Arc::clone(&recording)));

            let (program, script) = resolve_sidecar();
            match sidecar::Sidecar::spawn(&program, script.as_deref()) {
                Ok(mut sc) => {
                    spawn_stdout_reader(app.handle().clone(), &mut sc);
                    app.manage(SidecarState(Mutex::new(Some(sc))));
                }
                Err(e) => {
                    log::error!("Sidecar non démarré : {e}");
                    app.manage(SidecarState(Mutex::new(None)));
                }
            }

            match hotkey::HotkeyManager::new() {
                Ok(mut mgr) => {
                    let hotkey_str = hotkey::read_config_hotkey();
                    if let Err(e) = mgr.register(&hotkey_str) {
                        log::warn!("Hotkey '{hotkey_str}' non enregistré : {e}");
                    } else {
                        log::info!("Hotkey '{hotkey_str}' enregistré");
                    }
                    app.manage(HotkeyManagerState(Mutex::new(Some(mgr))));
                    hotkey::spawn_listener(app.handle().clone(), Arc::clone(&recording));
                }
                Err(e) => {
                    log::warn!("GlobalHotKeyManager::new() échoué ({e}) — hotkey désactivé");
                    app.manage(HotkeyManagerState(Mutex::new(None)));
                }
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
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// ─── Helpers ──────────────────────────────────────────────────────────────

/// Résout (programme, Option<script>) pour spawner le sidecar.
///
/// Ordre de résolution :
/// 1. `WHISPER_PYTHON` défini → dev (python + whisper_type.py)
/// 2. Binaire PyInstaller trouvé à côté de l'exe courant → prod bundlé
/// 3. Fallback → `.venv/bin/python3 whisper_type.py` (dev Linux)
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

/// Attache le thread lecteur stdout au sidecar. À appeler juste après spawn.
fn spawn_stdout_reader(handle: tauri::AppHandle, sc: &mut sidecar::Sidecar) {
    if let Some(reader) = sc.take_stdout() {
        std::thread::spawn(move || {
            for line in reader.lines() {
                if let Ok(line) = line {
                    log::info!("sidecar → {line}");
                    let _ = handle.emit("sidecar-msg", line.clone());
                    update_tray_from_sidecar(&handle, &line);
                    handle_download_events(&handle, &line);
                }
            }
        });
    }
}

/// Gère les events de téléchargement : ouvre/ferme la fenêtre download, lance le DL auto.
fn handle_download_events(app: &tauri::AppHandle, line: &str) {
    if let Ok(msg) = serde_json::from_str::<serde_json::Value>(line) {
        match msg.get("status").and_then(|v| v.as_str()) {
            Some("model_missing") => {
                if let Some(win) = app.get_webview_window("download") {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
                // Lancer le téléchargement automatiquement dès détection
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

/// Tue le sidecar actuel et en démarre un nouveau (après changement modèle/langue).
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
    *state.0.lock().unwrap() = Some(sc);
    Ok(())
}

/// Parse une ligne JSON sidecar et met à jour le tray en conséquence.
fn update_tray_from_sidecar(app: &tauri::AppHandle, line: &str) {
    if let Ok(msg) = serde_json::from_str::<serde_json::Value>(line) {
        match msg.get("status").and_then(|v| v.as_str()) {
            Some("recording") => tray::set_recording(app),
            Some("transcribing") => tray::set_transcribing(app),
            Some("done") => {
                if let Some(rec) = app.try_state::<RecordingState>() {
                    rec.0.store(false, Ordering::SeqCst);
                }
                tray::set_idle(app);
            }
            _ => {}
        }
    }
}

use std::io::BufRead;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use tauri::{Emitter, Manager};

mod hotkey;
mod sidecar;
pub mod tray;

pub struct SidecarState(pub Mutex<Option<sidecar::Sidecar>>);

/// Partagé entre le thread hotkey, le tray et les commandes Tauri.
pub struct RecordingState(pub Arc<AtomicBool>);

/// Stocke le HotkeyManager pour le rechargement à chaud (TICKET-08).
/// None si GlobalHotKeyManager::new() a échoué (Wayland natif sans XWayland).
pub struct HotkeyManagerState(pub Mutex<Option<hotkey::HotkeyManager>>);

#[tauri::command]
fn start_recording(
    sidecar: tauri::State<SidecarState>,
    recording: tauri::State<RecordingState>,
    app: tauri::AppHandle,
) -> Result<(), String> {
    recording.0.store(true, Ordering::SeqCst);
    tray::set_recording(&app);
    sidecar
        .0
        .lock()
        .unwrap()
        .as_mut()
        .ok_or("sidecar not running")?
        .send_cmd("start")
}

#[tauri::command]
fn stop_recording(
    sidecar: tauri::State<SidecarState>,
    recording: tauri::State<RecordingState>,
    app: tauri::AppHandle,
) -> Result<(), String> {
    recording.0.store(false, Ordering::SeqCst);
    tray::set_transcribing(&app);
    sidecar
        .0
        .lock()
        .unwrap()
        .as_mut()
        .ok_or("sidecar not running")?
        .send_cmd("stop")
}

/// Recharge le hotkey global sans redémarrer l'app (TICKET-08).
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

            // Sidecar Python
            let python = std::env::var("WHISPER_PYTHON")
                .unwrap_or_else(|_| ".venv/bin/python3".into());

            let recording = Arc::new(AtomicBool::new(false));
            app.manage(RecordingState(Arc::clone(&recording)));

            match sidecar::Sidecar::spawn(&python, "whisper_type.py") {
                Ok(mut sc) => {
                    let handle = app.handle().clone();
                    if let Some(reader) = sc.take_stdout() {
                        std::thread::spawn(move || {
                            for line in reader.lines() {
                                if let Ok(line) = line {
                                    log::info!("sidecar → {line}");
                                    let _ = handle.emit("sidecar-msg", line.clone());
                                    // Mettre à jour le tray selon l'état sidecar.
                                    update_tray_from_sidecar(&handle, &line);
                                }
                            }
                        });
                    }
                    app.manage(SidecarState(Mutex::new(Some(sc))));
                }
                Err(e) => {
                    log::error!("Sidecar non démarré : {e}");
                    app.manage(SidecarState(Mutex::new(None)));
                }
            }

            // Hotkey global
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

            // System tray + gestion fermeture fenêtre
            if let Err(e) = tray::setup(app) {
                log::warn!("Tray non disponible ({e}) — app sans icône tray");
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_recording,
            stop_recording,
            reload_hotkey,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

/// Parse une ligne JSON sidecar et met à jour l'état du tray en conséquence.
fn update_tray_from_sidecar(app: &tauri::AppHandle, line: &str) {
    if let Ok(msg) = serde_json::from_str::<serde_json::Value>(line) {
        match msg.get("status").and_then(|v| v.as_str()) {
            Some("recording") => tray::set_recording(app),
            Some("transcribing") => tray::set_transcribing(app),
            Some("done") => {
                // Sidecar confirme la fin : reset l'état AtomicBool au cas où
                // start_recording/stop_recording UI et hotkey se désynchronisent.
                if let Some(rec) = app.try_state::<RecordingState>() {
                    rec.0.store(false, Ordering::SeqCst);
                }
                tray::set_idle(app);
            }
            _ => {}
        }
    }
}

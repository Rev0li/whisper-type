use std::io::BufRead;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use tauri::{Emitter, Manager};

mod hotkey;
mod sidecar;

pub struct SidecarState(pub Mutex<Option<sidecar::Sidecar>>);

/// Partagé entre le thread hotkey et les commandes Tauri pour éviter la désynchronisation.
pub struct RecordingState(pub Arc<AtomicBool>);

/// Stocke le HotkeyManager pour permettre le rechargement sans redémarrer (TICKET-08).
pub struct HotkeyManagerState(pub Mutex<hotkey::HotkeyManager>);

#[tauri::command]
fn start_recording(
    sidecar: tauri::State<SidecarState>,
    recording: tauri::State<RecordingState>,
) -> Result<(), String> {
    recording.0.store(true, Ordering::SeqCst);
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
) -> Result<(), String> {
    recording.0.store(false, Ordering::SeqCst);
    sidecar
        .0
        .lock()
        .unwrap()
        .as_mut()
        .ok_or("sidecar not running")?
        .send_cmd("stop")
}

/// Recharge le hotkey global sans redémarrer l'app (appelé depuis TICKET-08 settings).
#[tauri::command]
fn reload_hotkey(
    hotkey_str: String,
    hk_state: tauri::State<HotkeyManagerState>,
) -> Result<(), String> {
    hk_state
        .0
        .lock()
        .unwrap()
        .register(&hotkey_str)
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

            // Chemin Python : WHISPER_PYTHON env var ou venv par défaut.
            let python = std::env::var("WHISPER_PYTHON")
                .unwrap_or_else(|_| ".venv/bin/python3".into());
            let script = "whisper_type.py";

            match sidecar::Sidecar::spawn(&python, script) {
                Ok(mut sc) => {
                    let handle = app.handle().clone();
                    if let Some(reader) = sc.take_stdout() {
                        std::thread::spawn(move || {
                            for line in reader.lines() {
                                if let Ok(line) = line {
                                    log::info!("sidecar → {line}");
                                    let _ = handle.emit("sidecar-msg", line);
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

            // Hotkey global : lu depuis config.toml, enregistré via global-hotkey.
            // Sur Linux : fonctionne via X11/XWayland. Sur Wayland natif, non supporté.
            let recording = Arc::new(AtomicBool::new(false));
            app.manage(RecordingState(Arc::clone(&recording)));

            match hotkey::HotkeyManager::new() {
                Ok(mut mgr) => {
                    let hotkey_str = hotkey::read_config_hotkey();
                    if let Err(e) = mgr.register(&hotkey_str) {
                        log::warn!("Hotkey '{hotkey_str}' non enregistré : {e}");
                    } else {
                        log::info!("Hotkey '{hotkey_str}' enregistré");
                    }
                    app.manage(HotkeyManagerState(Mutex::new(mgr)));
                    hotkey::spawn_listener(app.handle().clone(), recording);
                }
                Err(e) => {
                    log::warn!("GlobalHotKeyManager::new() échoué ({e}) — hotkey désactivé");
                }
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

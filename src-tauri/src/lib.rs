use std::io::BufRead;
use std::sync::Mutex;
use tauri::{Emitter, Manager};

mod sidecar;

pub struct SidecarState(pub Mutex<Option<sidecar::Sidecar>>);

#[tauri::command]
fn start_recording(state: tauri::State<SidecarState>) -> Result<(), String> {
    state
        .0
        .lock()
        .unwrap()
        .as_mut()
        .ok_or("sidecar not running")?
        .send_cmd("start")
}

#[tauri::command]
fn stop_recording(state: tauri::State<SidecarState>) -> Result<(), String> {
    state
        .0
        .lock()
        .unwrap()
        .as_mut()
        .ok_or("sidecar not running")?
        .send_cmd("stop")
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
            // En dev : cwd = racine du repo, donc .venv/bin/python3 est résolu correctement.
            // En prod (TICKET-09) : sidecar sera un binaire bundlé.
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

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![start_recording, stop_recording])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

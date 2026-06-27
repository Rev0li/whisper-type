use global_hotkey::{
    hotkey::{Code, HotKey, Modifiers},
    GlobalHotKeyEvent, GlobalHotKeyManager, HotKeyState,
};
use std::sync::{atomic::AtomicBool, atomic::Ordering, Arc};
use tauri::Manager;

pub struct HotkeyManager {
    inner: GlobalHotKeyManager,
    current: Option<HotKey>,
}

// SAFETY: On Windows, GlobalHotKeyManager wraps a Win32 HWND managed
// by the crate's internal message pump thread. Register/unregister calls
// are serialised by the Mutex in HotkeyManagerState, so cross-thread
// access is safe in practice.
#[cfg(windows)]
unsafe impl Send for HotkeyManager {}
#[cfg(windows)]
unsafe impl Sync for HotkeyManager {}

impl HotkeyManager {
    pub fn new() -> Result<Self, String> {
        Ok(Self {
            inner: GlobalHotKeyManager::new().map_err(|e| e.to_string())?,
            current: None,
        })
    }

    /// Désenregistre le hotkey précédent (si existant) et enregistre le nouveau.
    pub fn register(&mut self, hotkey_str: &str) -> Result<(), String> {
        if let Some(hk) = self.current.take() {
            let _ = self.inner.unregister(hk);
        }
        let hotkey = parse_hotkey(hotkey_str)?;
        self.inner
            .register(hotkey)
            .map_err(|e| e.to_string())?;
        self.current = Some(hotkey);
        Ok(())
    }
}

/// Démarre un thread qui écoute les events globaux et envoie start/stop au sidecar.
pub fn spawn_listener(
    app_handle: tauri::AppHandle,
    recording: Arc<AtomicBool>,
) {
    std::thread::spawn(move || {
        let receiver = GlobalHotKeyEvent::receiver();
        loop {
            match receiver.recv() {
                Ok(event) if event.state == HotKeyState::Pressed => {
                    // fetch_xor(true) flips le bit et retourne l'ancienne valeur.
                    let was_recording = recording.fetch_xor(true, Ordering::SeqCst);
                    let cmd = if was_recording { "stop" } else { "start" };
                    // Mise à jour optimiste du tray (avant confirmation du sidecar).
                    if was_recording {
                        crate::tray::set_transcribing(&app_handle);
                    } else {
                        crate::tray::set_recording(&app_handle);
                    }
                    let state = app_handle.state::<crate::SidecarState>();
                    let mut guard = state.0.lock().unwrap();
                    if let Some(sc) = guard.as_mut() {
                        if let Err(e) = sc.send_cmd(cmd) {
                            log::error!("hotkey → sidecar '{cmd}' failed: {e}");
                        }
                    }
                }
                Ok(_) => {}
                Err(e) => {
                    log::error!("hotkey receiver closed: {e}");
                    break;
                }
            }
        }
    });
}

/// Parse le format config "SUPER+grave", "CTRL+SHIFT+S", etc. vers HotKey.
pub fn parse_hotkey(s: &str) -> Result<HotKey, String> {
    let mut modifiers = Modifiers::empty();
    let mut code: Option<Code> = None;

    for part in s.split('+') {
        match part.trim().to_uppercase().as_str() {
            "SUPER" | "META" | "WIN" => modifiers |= Modifiers::SUPER,
            "CTRL" | "CONTROL" => modifiers |= Modifiers::CONTROL,
            "SHIFT" => modifiers |= Modifiers::SHIFT,
            "ALT" => modifiers |= Modifiers::ALT,
            key => {
                code = Some(str_to_code(key).ok_or_else(|| format!("Unknown key: {key}"))?);
            }
        }
    }

    let code = code.ok_or_else(|| "No key specified in hotkey".to_string())?;
    Ok(HotKey::new(
        if modifiers.is_empty() { None } else { Some(modifiers) },
        code,
    ))
}

fn str_to_code(s: &str) -> Option<Code> {
    match s {
        "GRAVE" | "`" => Some(Code::Backquote),
        "SPACE" => Some(Code::Space),
        "TAB" => Some(Code::Tab),
        "ENTER" | "RETURN" => Some(Code::Enter),
        "BACKSPACE" => Some(Code::Backspace),
        "ESCAPE" | "ESC" => Some(Code::Escape),
        "F1" => Some(Code::F1),
        "F2" => Some(Code::F2),
        "F3" => Some(Code::F3),
        "F4" => Some(Code::F4),
        "F5" => Some(Code::F5),
        "F6" => Some(Code::F6),
        "F7" => Some(Code::F7),
        "F8" => Some(Code::F8),
        "F9" => Some(Code::F9),
        "F10" => Some(Code::F10),
        "F11" => Some(Code::F11),
        "F12" => Some(Code::F12),
        "A" => Some(Code::KeyA),
        "B" => Some(Code::KeyB),
        "C" => Some(Code::KeyC),
        "D" => Some(Code::KeyD),
        "E" => Some(Code::KeyE),
        "F" => Some(Code::KeyF),
        "G" => Some(Code::KeyG),
        "H" => Some(Code::KeyH),
        "I" => Some(Code::KeyI),
        "J" => Some(Code::KeyJ),
        "K" => Some(Code::KeyK),
        "L" => Some(Code::KeyL),
        "M" => Some(Code::KeyM),
        "N" => Some(Code::KeyN),
        "O" => Some(Code::KeyO),
        "P" => Some(Code::KeyP),
        "Q" => Some(Code::KeyQ),
        "R" => Some(Code::KeyR),
        "S" => Some(Code::KeyS),
        "T" => Some(Code::KeyT),
        "U" => Some(Code::KeyU),
        "V" => Some(Code::KeyV),
        "W" => Some(Code::KeyW),
        "X" => Some(Code::KeyX),
        "Y" => Some(Code::KeyY),
        "Z" => Some(Code::KeyZ),
        "0" => Some(Code::Digit0),
        "1" => Some(Code::Digit1),
        "2" => Some(Code::Digit2),
        "3" => Some(Code::Digit3),
        "4" => Some(Code::Digit4),
        "5" => Some(Code::Digit5),
        "6" => Some(Code::Digit6),
        "7" => Some(Code::Digit7),
        "8" => Some(Code::Digit8),
        "9" => Some(Code::Digit9),
        _ => None,
    }
}

pub fn read_config_hotkey() -> String {
    crate::config::read().hotkey
}

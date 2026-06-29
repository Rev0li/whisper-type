use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut};

/// Parse le format config "SUPER+grave", "CTRL+SHIFT+S", etc. vers Shortcut.
pub fn parse_hotkey(s: &str) -> Result<Shortcut, String> {
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
    Ok(Shortcut::new(
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

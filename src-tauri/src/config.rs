use std::path::PathBuf;

pub struct Config {
    pub model: String,
    pub language: String,
    pub hotkey: String,
}

impl Config {
    pub fn defaults() -> Self {
        Self {
            model: "small".into(),
            language: "fr".into(),
            hotkey: "SUPER+grave".into(),
        }
    }
}

pub fn config_path() -> PathBuf {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_else(|_| ".".into());
    PathBuf::from(home).join(".config/whisper-type/config.toml")
}

pub fn read() -> Config {
    let d = Config::defaults();
    let content = match std::fs::read_to_string(config_path()) {
        Ok(c) => c,
        Err(_) => return d,
    };
    let table = match content.parse::<toml::Table>() {
        Ok(t) => t,
        Err(_) => return d,
    };
    Config {
        model: table.get("model").and_then(|v| v.as_str()).unwrap_or(&d.model).into(),
        language: table.get("language").and_then(|v| v.as_str()).unwrap_or(&d.language).into(),
        hotkey: table.get("hotkey").and_then(|v| v.as_str()).unwrap_or(&d.hotkey).into(),
    }
}

pub fn write(model: &str, language: &str, hotkey: &str) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let content = format!("model = \"{model}\"\nlanguage = \"{language}\"\nhotkey = \"{hotkey}\"\n");
    std::fs::write(&path, content).map_err(|e| e.to_string())
}

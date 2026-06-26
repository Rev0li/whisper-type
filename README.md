# whisper-type

Local speech-to-text that types directly into your active input. Press a hotkey, speak, release — the transcribed text appears where your cursor is.

Runs 100% offline using [faster-whisper](https://github.com/SYSTRAN/faster-whisper). No cloud, no subscription.

---

## Current state — Linux / Hyprland (daemon mode)

### Requirements

- Fedora / Linux
- Hyprland (Wayland)
- Python 3.10+
- `wtype` (auto-installed)

### Dev prerequisites (frontend / Tauri)

To work on the Tauri frontend (`src-tauri/`):

- [Rust](https://rustup.rs/) 1.70+ (`rustup` recommended)
- Node.js 18+ + npm
- Tauri v2 system deps: `webkit2gtk4.1-devel`, `openssl-devel`, `libappindicator-gtk3-devel` (Fedora)

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install frontend deps
npm install

# Launch dev build (requires Wayland/X11 display)
npm run dev
```

### Install

```bash
git clone https://github.com/Rev0li/whisper-type
cd whisper-type
./install.sh
```

The install script:
- Installs system deps (`portaudio`, `wtype`, `libnotify`)
- Creates a Python venv and installs `faster-whisper` + `sounddevice`
- Adds to `hyprland.conf`:
  - `exec-once` → daemon auto-starts with Hyprland
  - `bind = SUPER + \`` → toggle recording

### Usage

| Action | Result |
|---|---|
| **SUPER + `** (first press) | Start recording — notification appears |
| **SUPER + `** (second press) | Stop → transcribe → text typed in active input |

The daemon starts automatically with Hyprland. The Whisper model loads in the background (~15s on first launch, instant after).

### Models

```bash
./start.sh tiny    # fastest, less accurate
./start.sh base    # good balance
./start.sh small   # default — best for French
./start.sh medium  # most accurate, slower
```

---

## Roadmap

### v0.2 — Cross-platform CLI
- [ ] Windows support (PowerShell / `pyautogui` for typing)
- [ ] Configurable hotkey via config file (no need to edit hyprland.conf)
- [ ] Auto language detection

### v0.3 — Simple UI
- [ ] Minimal system tray icon (status indicator)
- [ ] Visual recording indicator
- [ ] Settings panel: model size, language, hotkey

### v1.0 — Full cross-platform app
- [ ] Native desktop app (Windows + Linux)
- [ ] Modern, minimal UI
- [ ] One-click installer

---

## How it works

```
SUPER+`
  └─→ toggle.sh sends SIGUSR1 to daemon
        ├─ if idle   → start recording (sounddevice, 16kHz mono)
        └─ if recording → stop → transcribe (faster-whisper) → wtype text
```

The model stays loaded in memory — only the first transcription after launch has a cold start.

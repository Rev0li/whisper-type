#!/home/rev0li/dev/whisper-type/.venv/bin/python3
"""
whisper-type daemon — enregistre le micro, transcrit avec Whisper, tape le texte dans l'input actif.

Config : ~/.config/whisper-type/config.toml (créé automatiquement au premier lancement)

Signals:
  SIGUSR1 → toggle start/stop enregistrement
  SIGTERM → arrête le daemon proprement
"""

import os
import sys
import signal
import threading
import subprocess
import time
import wave
import logging
from pathlib import Path

import json
import config as cfg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

import tempfile as _tempfile
PID_FILE = Path(_tempfile.gettempdir()) / "whisper-type.pid"
IS_WINDOWS = sys.platform == "win32"
SIDECAR_MODE = "--sidecar" in sys.argv
_config = cfg.load()
MODEL_SIZE = _config["model"]
LANGUAGE = _config["language"]

# Taille approximative des modèles (MB) — pour l'UI de téléchargement.
MODEL_SIZES_MB = {
    "tiny": 75, "base": 141, "small": 461,
    "medium": 1530, "large": 3100,
}

# État global
_recording = False
_audio_frames = []
_lock = threading.Lock()
_model = None
_model_ready = threading.Event()
_stream = None


def _sidecar_respond(data: dict) -> None:
    """Envoie une réponse JSON sur stdout (canal IPC vers Rust)."""
    print(json.dumps(data), flush=True)


def notify(title, msg="", icon="dialog-information"):
    if IS_WINDOWS:
        log.info(f"[notif] {title} {msg}")
        return
    subprocess.run(["notify-send", "-i", icon, title, msg], check=False)


def load_model():
    global _model
    log.info(f"Chargement du modèle Whisper '{MODEL_SIZE}'...")
    notify("whisper-type", f"Chargement modèle {MODEL_SIZE}...", "audio-input-microphone")
    from faster_whisper import WhisperModel
    # device="auto" utilise CUDA si dispo, sinon CPU
    _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    _model_ready.set()
    log.info("Modèle chargé.")
    notify("whisper-type", "Prêt — raccourci actif", "audio-input-microphone")


def start_recording():
    global _recording, _audio_frames, _stream
    import sounddevice as sd

    with _lock:
        if _recording:
            return
        _recording = True
        _audio_frames = []

    log.info("Enregistrement démarré...")
    notify("Enregistrement...", "Parle maintenant", "media-record")

    SAMPLERATE = 16000
    CHANNELS = 1

    def callback(indata, frames, time_info, status):
        if _recording:
            _audio_frames.append(indata.copy())

    _stream = sd.InputStream(
        samplerate=SAMPLERATE,
        channels=CHANNELS,
        dtype="int16",
        callback=callback,
    )
    _stream.start()


def stop_and_transcribe():
    global _recording, _stream
    import numpy as np

    with _lock:
        if not _recording:
            return
        _recording = False

    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None

    if not _audio_frames:
        log.warning("Aucun audio enregistré.")
        return

    if _model is None:
        log.error("Modèle non encore chargé — transcription annulée")
        notify("whisper-type", "Modèle en cours de chargement, réessayez dans quelques secondes", "dialog-warning")
        if SIDECAR_MODE:
            _sidecar_respond({"status": "error", "error": "model_not_ready"})
        return

    log.info("Transcription en cours...")
    notify("Transcription...", "", "hourglass")

    audio = np.concatenate(_audio_frames, axis=0).flatten()

    # Sauvegarde en WAV temporaire
    with _tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(16000)
        wf.writeframes(audio.tobytes())

    try:
        lang = None if LANGUAGE == "auto" else LANGUAGE
        segments, info = _model.transcribe(
            tmp_path,
            language=lang,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        log.info(f"Texte transcrit: {text!r}")
    finally:
        os.unlink(tmp_path)

    if not text:
        notify("whisper-type", "Rien détecté", "dialog-warning")
        if SIDECAR_MODE:
            _sidecar_respond({"status": "done", "text": ""})
        return

    type_text(text)
    notify("whisper-type", f"{text[:60]}{'...' if len(text) > 60 else ''}", "emblem-default")
    if SIDECAR_MODE:
        _sidecar_respond({"status": "done", "text": text})


def type_text(text):
    if IS_WINDOWS:
        _type_text_windows(text)
    else:
        _type_text_linux(text)


def _type_text_windows(text):
    """Clipboard + Ctrl+V : gère tout Unicode, fiable dans toutes les apps Windows."""
    try:
        import pyperclip
        import keyboard as kb
        pyperclip.copy(text)
        time.sleep(0.05)
        kb.send("ctrl+v")
        log.info("Texte tapé via clipboard+ctrl+v (Windows)")
    except Exception as e:
        log.error(f"Typing Windows échoué : {e}")
        notify("whisper-type", "Erreur typing — texte dans le clipboard (Ctrl+V)", "dialog-error")


def _type_text_linux(text):
    """Essaie wtype (Wayland) puis xdotool (X11), puis clipboard en fallback."""
    for cmd in [
        ["wtype", text],
        ["xdotool", "type", "--clearmodifiers", "--", text],
        ["ydotool", "type", "--", text],
    ]:
        if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                log.info(f"Texte tapé avec {cmd[0]}")
                return
            log.warning(f"{cmd[0]} a échoué : {result.stderr.decode()}")

    log.warning("Aucun outil de typing disponible — copie dans le clipboard")
    subprocess.run(["wl-copy", text], check=False)
    subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=False)
    notify("whisper-type", "Texte copié dans le clipboard (Ctrl+V)", "edit-paste")


def toggle_handler(signum, frame):
    """SIGUSR1 handler : toggle enregistrement."""
    if _recording:
        threading.Thread(target=stop_and_transcribe, daemon=True).start()
    else:
        threading.Thread(target=start_recording, daemon=True).start()


def cleanup(signum=None, frame=None):
    global _recording
    _recording = False
    if _stream:
        try:
            _stream.stop()
            _stream.close()
        except Exception:
            pass
    PID_FILE.unlink(missing_ok=True)
    log.info("Daemon arrêté.")
    sys.exit(0)


def _hotkey_to_keyboard_lib(hotkey: str) -> str:
    """Convertit le format config (ex: SUPER+grave) vers keyboard lib (windows+`)."""
    mapping = {
        "SUPER": "windows", "CTRL": "ctrl", "SHIFT": "shift", "ALT": "alt",
        "grave": "`", "SPACE": "space", "TAB": "tab",
    }
    return "+".join(mapping.get(p, p.lower()) for p in hotkey.split("+"))


def model_in_cache(model_size: str) -> bool:
    """Vérifie si le modèle faster-whisper est dans le cache HuggingFace local."""
    hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    cache_dir = os.environ.get("HF_HUB_CACHE", os.path.join(hf_home, "hub"))
    safe_name = "models--Systran--faster-whisper-" + model_size
    snapshots = os.path.join(cache_dir, safe_name, "snapshots")
    return os.path.isdir(snapshots) and bool(os.listdir(snapshots))


def download_model_with_progress(model_size: str) -> None:
    """Télécharge le modèle via HuggingFace Hub, émet la progression sur stdout.
    Lève une exception en cas d'erreur réseau (déjà émise sur stdout avant).
    """
    from huggingface_hub import list_repo_files, hf_hub_download

    repo_id = f"Systran/faster-whisper-{model_size}"
    log.info(f"Téléchargement {repo_id}...")

    try:
        files = [f for f in list_repo_files(repo_id) if not f.endswith((".msgpack", ".h5"))]
    except Exception as e:
        _sidecar_respond({"status": "download_error", "error": f"Impossible de lister les fichiers : {e}"})
        raise

    total = len(files)
    for i, filename in enumerate(files):
        _sidecar_respond({
            "status": "download_progress",
            "percent": int(100 * i / total),
            "file": filename,
            "current": i + 1,
            "total": total,
        })
        try:
            hf_hub_download(repo_id=repo_id, filename=filename)
        except Exception as e:
            _sidecar_respond({"status": "download_error", "error": f"{filename} : {e}"})
            raise

    _sidecar_respond({
        "status": "download_progress",
        "percent": 100,
        "file": "",
        "current": total,
        "total": total,
    })


def _download_and_load() -> None:
    """Télécharge le modèle puis le charge (appelé après réception de download_model)."""
    try:
        download_model_with_progress(MODEL_SIZE)
    except Exception:
        return  # erreur déjà émise sur stdout par download_model_with_progress
    _sidecar_respond({"status": "model_ready"})
    load_model()


def sidecar_loop() -> None:
    """Mode IPC : lit les commandes JSON depuis stdin, répond sur stdout.
    Appelé quand le process est lancé avec --sidecar par Rust/Tauri.
    """
    log.info("Mode sidecar (IPC stdin/stdout)")

    # Vérification du cache avant chargement — permet d'afficher la UI de download.
    if model_in_cache(MODEL_SIZE):
        log.info(f"Modèle '{MODEL_SIZE}' en cache → chargement")
        _sidecar_respond({"status": "model_cached"})
        threading.Thread(target=load_model, daemon=True).start()
    else:
        log.info(f"Modèle '{MODEL_SIZE}' absent du cache → en attente de download_model")
        _sidecar_respond({
            "status": "model_missing",
            "model": MODEL_SIZE,
            "size_mb": MODEL_SIZES_MB.get(MODEL_SIZE, 0),
        })

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            _sidecar_respond({"error": "invalid JSON"})
            continue

        cmd = msg.get("cmd")
        if cmd == "start":
            if not _model_ready.is_set():
                _sidecar_respond({"status": "model_loading"})
            else:
                threading.Thread(target=start_recording, daemon=True).start()
                _sidecar_respond({"status": "recording"})
        elif cmd == "stop":
            notify("Transcription...", "", "hourglass")
            _sidecar_respond({"status": "transcribing"})
            threading.Thread(target=stop_and_transcribe, daemon=True).start()
        elif cmd == "download_model":
            threading.Thread(target=_download_and_load, daemon=True).start()
            _sidecar_respond({"status": "downloading"})
        elif cmd == "check_model":
            if model_in_cache(MODEL_SIZE):
                _sidecar_respond({"status": "model_cached"})
            else:
                _sidecar_respond({
                    "status": "model_missing",
                    "model": MODEL_SIZE,
                    "size_mb": MODEL_SIZES_MB.get(MODEL_SIZE, 0),
                })
        elif cmd == "ping":
            _sidecar_respond({"status": "ok"})
        else:
            _sidecar_respond({"error": f"unknown command: {cmd!r}"})

    log.info("stdin fermé — sidecar terminé.")


def main():
    PID_FILE.write_text(str(os.getpid()))
    log.info(f"Daemon démarré (PID {os.getpid()})")

    if SIDECAR_MODE:
        sidecar_loop()
        return

    threading.Thread(target=load_model, daemon=True).start()

    if IS_WINDOWS:
        import keyboard as kb
        hotkey_str = _hotkey_to_keyboard_lib(_config["hotkey"])
        log.info(f"Hotkey Windows : {hotkey_str}")
        kb.add_hotkey(hotkey_str, lambda: toggle_handler(None, None))
        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)
        while True:
            time.sleep(1)
    else:
        signal.signal(signal.SIGUSR1, toggle_handler)
        signal.signal(signal.SIGTERM, cleanup)
        signal.signal(signal.SIGINT, cleanup)
        while True:
            signal.pause()


if __name__ == "__main__":
    main()

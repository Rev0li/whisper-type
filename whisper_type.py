#!/home/rev0li/dev/whisper-type/.venv/bin/python3
"""
whisper-type — enregistre le micro, transcrit avec Whisper, tape le texte dans l'input actif.

Config : ~/.config/whisper-type/config.toml
Signals : SIGUSR1 → toggle start/stop  |  SIGTERM/SIGINT → arrêt propre
"""

import os
import sys
import signal
import threading
import subprocess
import wave
import logging
import tempfile
from pathlib import Path

import json
import config as cfg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PID_FILE = Path(tempfile.gettempdir()) / "whisper-type.pid"
_config = cfg.load()
MODEL_SIZE = _config["model"]
LANGUAGE   = _config["language"]

_recording     = False
_audio_frames  = []
_lock          = threading.Lock()
_model         = None
_stream        = None


def notify(title, msg="", icon="dialog-information"):
    subprocess.run(["notify-send", "-i", icon, title, msg], check=False)


def load_model():
    global _model
    log.info(f"Chargement du modèle Whisper '{MODEL_SIZE}'...")
    notify("whisper-type", f"Chargement modèle {MODEL_SIZE}...", "audio-input-microphone")
    from faster_whisper import WhisperModel
    _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
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

    def callback(indata, frames, time_info, status):
        if _recording:
            _audio_frames.append(indata.copy())

    try:
        _stream = sd.InputStream(samplerate=16000, channels=1, dtype="int16", callback=callback)
        _stream.start()
    except Exception as e:
        log.error(f"Microphone inaccessible : {e}")
        with _lock:
            _recording = False


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
        notify("whisper-type", "Modèle en cours de chargement, réessayez dans quelques secondes", "dialog-warning")
        return

    log.info("Transcription en cours...")
    notify("Transcription...", "", "hourglass")

    audio = np.concatenate(_audio_frames, axis=0).flatten()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio.tobytes())

    try:
        lang = None if LANGUAGE == "auto" else LANGUAGE
        segments, _ = _model.transcribe(tmp_path, language=lang, beam_size=5, vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
        log.info(f"Texte transcrit : {text!r}")
    finally:
        os.unlink(tmp_path)

    if not text:
        notify("whisper-type", "Rien détecté", "dialog-warning")
        return

    type_text(text)
    notify("whisper-type", f"{text[:60]}{'...' if len(text) > 60 else ''}", "emblem-default")


def type_text(text):
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
    subprocess.run(["wl-copy", text], input=text.encode(), check=False)
    notify("whisper-type", "Texte copié dans le clipboard (Ctrl+V)", "edit-paste")


def toggle_handler(signum, frame):
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


def main():
    PID_FILE.write_text(str(os.getpid()))
    log.info(f"Daemon démarré (PID {os.getpid()}, modèle={MODEL_SIZE}, langue={LANGUAGE})")

    threading.Thread(target=load_model, daemon=True).start()

    signal.signal(signal.SIGUSR1, toggle_handler)
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    while True:
        signal.pause()


if __name__ == "__main__":
    main()

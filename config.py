#!/home/rev0li/dev/whisper-type/.venv/bin/python3
"""Lecture et initialisation de ~/.config/whisper-type/config.toml."""

import tomllib
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "whisper-type"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULTS = {
    "model": "small",
    "language": "fr",
    "hotkey": "SUPER+grave",
}

_DEFAULT_TOML = """\
# whisper-type — configuration
# Modifiez ce fichier puis relancez le daemon (stop.sh && start.sh).

# Modèle Whisper : tiny | base | small | medium
# tiny   : ~1s  de transcription, moins précis
# base   : ~2s  bon compromis
# small  : ~4s  meilleur pour le français  ← défaut
# medium : ~8s  le plus précis, plus lent
model = "small"

# Langue : "fr" | "en" | "auto"
# "auto" laisse Whisper détecter automatiquement
language = "fr"

# Raccourci clavier (utilisé par le futur frontend Tauri)
# Exemples : "SUPER+grave", "CTRL+SHIFT+SPACE"
hotkey = "SUPER+grave"
"""


def load() -> dict:
    """Charge la config. Crée le fichier avec les défauts s'il est absent."""
    if not CONFIG_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(_DEFAULT_TOML, encoding="utf-8")

    with CONFIG_PATH.open("rb") as f:
        data = tomllib.load(f)

    # Complète les clés manquantes avec les défauts (fichier partiel toléré)
    return {**DEFAULTS, **data}

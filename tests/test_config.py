"""Tests unitaires pour config.py — TICKET-01."""

import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    """Redirige CONFIG_DIR et CONFIG_PATH vers un répertoire temporaire."""
    cfg_dir = tmp_path / "whisper-type"
    cfg_path = cfg_dir / "config.toml"

    # Recharge le module avec les paths patchés
    if "config" in sys.modules:
        del sys.modules["config"]

    import config
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)
    return config, cfg_dir, cfg_path


class TestConfigAbsent:
    """Config absent → génération automatique avec les défauts."""

    def test_creates_file_on_first_load(self, tmp_config):
        config, _, cfg_path = tmp_config
        assert not cfg_path.exists()
        config.load()
        assert cfg_path.exists()

    def test_created_file_is_valid_toml(self, tmp_config):
        import tomllib
        config, _, cfg_path = tmp_config
        config.load()
        with cfg_path.open("rb") as f:
            data = tomllib.load(f)
        assert "model" in data
        assert "language" in data
        assert "hotkey" in data

    def test_defaults_returned_when_file_absent(self, tmp_config):
        config, _, _ = tmp_config
        result = config.load()
        assert result["model"] == "small"
        assert result["language"] == "fr"
        assert result["hotkey"] == "SUPER+grave"

    def test_creates_parent_dir(self, tmp_config):
        config, cfg_dir, _ = tmp_config
        assert not cfg_dir.exists()
        config.load()
        assert cfg_dir.exists()


class TestConfigPartiel:
    """Config partiel (clé manquante) → merge tolérant avec les défauts."""

    def test_missing_language_falls_back_to_default(self, tmp_config):
        config, cfg_dir, cfg_path = tmp_config
        cfg_dir.mkdir(parents=True)
        cfg_path.write_text('model = "tiny"\nhotkey = "CTRL+SPACE"\n', encoding="utf-8")
        result = config.load()
        assert result["language"] == "fr"      # défaut
        assert result["model"] == "tiny"       # lu depuis le fichier
        assert result["hotkey"] == "CTRL+SPACE"  # lu depuis le fichier

    def test_missing_model_falls_back_to_default(self, tmp_config):
        config, cfg_dir, cfg_path = tmp_config
        cfg_dir.mkdir(parents=True)
        cfg_path.write_text('language = "en"\n', encoding="utf-8")
        result = config.load()
        assert result["model"] == "small"
        assert result["language"] == "en"

    def test_empty_file_returns_all_defaults(self, tmp_config):
        config, cfg_dir, cfg_path = tmp_config
        cfg_dir.mkdir(parents=True)
        cfg_path.write_text("", encoding="utf-8")
        result = config.load()
        assert result == config.DEFAULTS


class TestLanguageAuto:
    """language = "auto" → config retourne "auto", whisper_type passe None à Whisper."""

    def test_auto_language_preserved_in_config(self, tmp_config):
        config, cfg_dir, cfg_path = tmp_config
        cfg_dir.mkdir(parents=True)
        cfg_path.write_text('language = "auto"\n', encoding="utf-8")
        result = config.load()
        assert result["language"] == "auto"

    def test_auto_converts_to_none_for_whisper(self, tmp_config):
        """Reproduit la logique de whisper_type.py ligne 118."""
        config, cfg_dir, cfg_path = tmp_config
        cfg_dir.mkdir(parents=True)
        cfg_path.write_text('language = "auto"\n', encoding="utf-8")
        result = config.load()
        LANGUAGE = result["language"]
        lang = None if LANGUAGE == "auto" else LANGUAGE
        assert lang is None

    def test_fr_language_not_converted(self, tmp_config):
        config, cfg_dir, cfg_path = tmp_config
        cfg_dir.mkdir(parents=True)
        cfg_path.write_text('language = "fr"\n', encoding="utf-8")
        result = config.load()
        LANGUAGE = result["language"]
        lang = None if LANGUAGE == "auto" else LANGUAGE
        assert lang == "fr"

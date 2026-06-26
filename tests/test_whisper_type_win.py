"""Tests unitaires pour les parties cross-platform de whisper_type.py — TICKET-02.

Ces tests couvrent la logique testable sans Windows réel :
- _hotkey_to_keyboard_lib()
- notify() branche Windows (log-only)
- IS_WINDOWS détection
- PID_FILE path cross-platform
"""

import sys
import importlib
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock


def _load_module(monkeypatch, tmp_path, is_windows=False):
    """Charge whisper_type avec config mockée et IS_WINDOWS patchable."""
    # Mock config pour éviter toute lecture/création de fichier réel
    fake_config = MagicMock()
    fake_config.load.return_value = {
        "model": "small",
        "language": "fr",
        "hotkey": "SUPER+grave",
    }
    monkeypatch.setitem(sys.modules, "config", fake_config)

    # Mock des imports optionnels lourds
    for mod in ["faster_whisper", "sounddevice", "numpy", "keyboard", "pyperclip"]:
        monkeypatch.setitem(sys.modules, mod, MagicMock())

    if "whisper_type" in sys.modules:
        del sys.modules["whisper_type"]

    platform = "win32" if is_windows else "linux"
    with patch("sys.platform", platform):
        import whisper_type
    return whisper_type


class TestHotkeyConversion:
    """_hotkey_to_keyboard_lib() — conversion format config → keyboard lib."""

    def test_super_grave(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path)
        assert wt._hotkey_to_keyboard_lib("SUPER+grave") == "windows+`"

    def test_ctrl_shift_space(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path)
        assert wt._hotkey_to_keyboard_lib("CTRL+SHIFT+SPACE") == "ctrl+shift+space"

    def test_alt_tab(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path)
        assert wt._hotkey_to_keyboard_lib("ALT+TAB") == "alt+tab"

    def test_unknown_key_lowercased(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path)
        # Clé inconnue → lowercased telle quelle
        assert wt._hotkey_to_keyboard_lib("CTRL+F12") == "ctrl+f12"

    def test_single_key(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path)
        assert wt._hotkey_to_keyboard_lib("SUPER") == "windows"


class TestNotifyWindows:
    """notify() sur Windows → log uniquement, pas de subprocess."""

    def test_windows_notify_does_not_call_subprocess(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path, is_windows=True)
        monkeypatch.setattr(wt, "IS_WINDOWS", True)
        with patch("whisper_type.subprocess") as mock_sub:
            wt.notify("titre", "message")
            mock_sub.run.assert_not_called()

    def test_linux_notify_calls_notify_send(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path, is_windows=False)
        monkeypatch.setattr(wt, "IS_WINDOWS", False)
        with patch("whisper_type.subprocess") as mock_sub:
            wt.notify("titre", "message")
            mock_sub.run.assert_called_once()
            cmd = mock_sub.run.call_args[0][0]
            assert cmd[0] == "notify-send"

    def test_windows_notify_logs(self, monkeypatch, tmp_path, caplog):
        wt = _load_module(monkeypatch, tmp_path, is_windows=True)
        monkeypatch.setattr(wt, "IS_WINDOWS", True)
        with caplog.at_level(logging.INFO, logger="whisper_type"):
            wt.notify("mon titre", "mon msg")
        assert "mon titre" in caplog.text


class TestIsWindows:
    """IS_WINDOWS reflète bien sys.platform."""

    def test_is_windows_false_on_linux(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path, is_windows=False)
        assert wt.IS_WINDOWS is False

    def test_is_windows_true_on_win32(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path, is_windows=True)
        assert wt.IS_WINDOWS is True


class TestPidFilePath:
    """PID_FILE utilise tempfile.gettempdir() — pas un /tmp hardcodé."""

    def test_pid_file_uses_tempdir(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path)
        import tempfile
        expected = Path(tempfile.gettempdir()) / "whisper-type.pid"
        assert wt.PID_FILE == expected

    def test_pid_file_is_named_correctly(self, monkeypatch, tmp_path):
        wt = _load_module(monkeypatch, tmp_path)
        assert wt.PID_FILE.name == "whisper-type.pid"

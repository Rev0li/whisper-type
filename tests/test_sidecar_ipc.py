"""Tests unitaires protocole IPC sidecar — TICKET-04.

Couvre : _sidecar_respond(), sidecar_loop() (ping, start, stop, JSON invalide,
commande inconnue, ligne vide), SIDECAR_MODE detection.
Pas de micro, pas de cargo requis.
"""

import io
import json
import sys
from unittest.mock import MagicMock, patch


def _load_wt(monkeypatch):
    """Charge whisper_type avec dépendances lourdes mockées."""
    fake_cfg = MagicMock()
    fake_cfg.load.return_value = {"model": "small", "language": "fr", "hotkey": "SUPER+grave"}
    monkeypatch.setitem(sys.modules, "config", fake_cfg)
    for mod in ["faster_whisper", "sounddevice", "numpy", "keyboard", "pyperclip"]:
        monkeypatch.setitem(sys.modules, mod, MagicMock())
    if "whisper_type" in sys.modules:
        del sys.modules["whisper_type"]
    import whisper_type
    return whisper_type


def _run_sidecar(wt, monkeypatch, lines, capsys):
    """Lance sidecar_loop() avec stdin simulé, retourne les dicts JSON reçus sur stdout."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("\n".join(lines) + "\n"))
    monkeypatch.setattr(wt, "load_model", lambda: None)
    monkeypatch.setattr(wt, "start_recording", lambda: None)
    monkeypatch.setattr(wt, "stop_and_transcribe", lambda: None)
    monkeypatch.setattr(wt, "notify", lambda *a, **kw: None)
    wt.sidecar_loop()
    out = capsys.readouterr().out
    return [json.loads(ln) for ln in out.splitlines() if ln.strip()]


class TestSidecarRespond:
    """_sidecar_respond() — écrit du JSON valide sur stdout avec flush."""

    def test_outputs_valid_json(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        wt._sidecar_respond({"status": "ok"})
        out = capsys.readouterr().out
        assert json.loads(out.strip()) == {"status": "ok"}

    def test_outputs_error_json(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        wt._sidecar_respond({"error": "invalid JSON"})
        out = capsys.readouterr().out
        assert json.loads(out.strip()) == {"error": "invalid JSON"}

    def test_outputs_one_line_per_call(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        wt._sidecar_respond({"a": 1})
        wt._sidecar_respond({"b": 2})
        lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
        assert len(lines) == 2


class TestSidecarLoopPing:
    """cmd=ping → {"status": "ok"}"""

    def test_ping_returns_ok(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ['{"cmd": "ping"}'], capsys)
        assert responses == [{"status": "ok"}]

    def test_multiple_pings(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ['{"cmd": "ping"}', '{"cmd": "ping"}'], capsys)
        assert responses == [{"status": "ok"}, {"status": "ok"}]


class TestSidecarLoopInvalidInput:
    """Entrées invalides → réponses d'erreur, pas de crash."""

    def test_invalid_json_returns_error(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ["not valid json{{{"], capsys)
        assert len(responses) == 1
        assert responses[0]["error"] == "invalid JSON"

    def test_unknown_command_returns_error(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ['{"cmd": "reboot"}'], capsys)
        assert len(responses) == 1
        assert "error" in responses[0]
        assert "reboot" in responses[0]["error"]

    def test_empty_lines_ignored(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ["", "   ", '{"cmd": "ping"}', ""], capsys)
        assert responses == [{"status": "ok"}]

    def test_missing_cmd_key_returns_error(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ['{"action": "ping"}'], capsys)
        assert len(responses) == 1
        assert "error" in responses[0]

    def test_null_cmd_returns_error(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ['{"cmd": null}'], capsys)
        assert len(responses) == 1
        assert "error" in responses[0]


class TestSidecarLoopStart:
    """cmd=start → {"status": "recording"} + thread start_recording lancé."""

    def test_start_returns_recording_status(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ['{"cmd": "start"}'], capsys)
        assert {"status": "recording"} in responses

    def test_start_calls_start_recording(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        called = []
        monkeypatch.setattr(sys, "stdin", io.StringIO('{"cmd": "start"}\n'))
        monkeypatch.setattr(wt, "load_model", lambda: None)
        monkeypatch.setattr(wt, "start_recording", lambda: called.append(True))
        monkeypatch.setattr(wt, "stop_and_transcribe", lambda: None)
        monkeypatch.setattr(wt, "notify", lambda *a, **kw: None)
        wt.sidecar_loop()
        # Thread is daemon — give it a moment
        import time; time.sleep(0.05)
        assert called == [True]


class TestSidecarLoopStop:
    """cmd=stop → {"status": "transcribing"} avant de lancer le thread."""

    def test_stop_returns_transcribing_status(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = _run_sidecar(wt, monkeypatch, ['{"cmd": "stop"}'], capsys)
        assert {"status": "transcribing"} in responses

    def test_stop_sends_transcribing_before_thread(self, monkeypatch, capsys):
        """transcribing doit arriver AVANT que stop_and_transcribe soit appelé."""
        wt = _load_wt(monkeypatch)
        order = []
        original_respond = wt._sidecar_respond

        def track_respond(data):
            order.append(("respond", data))
            original_respond(data)

        monkeypatch.setattr(sys, "stdin", io.StringIO('{"cmd": "stop"}\n'))
        monkeypatch.setattr(wt, "load_model", lambda: None)
        monkeypatch.setattr(wt, "start_recording", lambda: None)
        monkeypatch.setattr(wt, "stop_and_transcribe", lambda: order.append(("transcribe",)))
        monkeypatch.setattr(wt, "notify", lambda *a, **kw: None)
        monkeypatch.setattr(wt, "_sidecar_respond", track_respond)
        wt.sidecar_loop()
        import time; time.sleep(0.05)
        # La réponse "transcribing" doit précéder l'appel stop_and_transcribe
        respond_idx = next(i for i, e in enumerate(order) if e == ("respond", {"status": "transcribing"}))
        transcribe_idx = next(i for i, e in enumerate(order) if e == ("transcribe",))
        assert respond_idx < transcribe_idx


class TestSidecarMode:
    """SIDECAR_MODE = '--sidecar' in sys.argv."""

    def test_sidecar_mode_false_by_default(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["whisper_type.py"])
        wt = _load_wt(monkeypatch)
        assert wt.SIDECAR_MODE is False

    def test_sidecar_mode_true_with_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["whisper_type.py", "--sidecar"])
        wt = _load_wt(monkeypatch)
        assert wt.SIDECAR_MODE is True

    def test_sidecar_mode_false_with_other_args(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["whisper_type.py", "--debug"])
        wt = _load_wt(monkeypatch)
        assert wt.SIDECAR_MODE is False

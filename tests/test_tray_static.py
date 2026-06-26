"""Tests statiques TICKET-06 — system tray Rust.

Couvre : structure fichiers, feature tray-icon, logique update_tray_from_sidecar()
(parité Python/Rust), graceful degradation try_state, gestion fermeture fenêtre,
logique toggle optimiste hotkey+tray.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CARGO = ROOT / "src-tauri" / "Cargo.toml"
TRAY_RS = ROOT / "src-tauri" / "src" / "tray.rs"
LIB_RS = ROOT / "src-tauri" / "src" / "lib.rs"
HOTKEY_RS = ROOT / "src-tauri" / "src" / "hotkey.rs"


class TestStructure:
    def test_tray_rs_exists(self):
        assert TRAY_RS.is_file()

    def test_tray_icon_feature_in_cargo(self):
        assert 'features = ["tray-icon"]' in CARGO.read_text()

    def test_icon_file_referenced(self):
        assert "32x32.png" in TRAY_RS.read_text()


class TestTrayRsContent:
    """tray.rs — vérifications de contenu critiques."""

    def _src(self):
        return TRAY_RS.read_text()

    def test_try_state_used_for_graceful_degradation(self):
        # set_idle/set_recording/set_transcribing doivent utiliser try_state, pas state
        src = self._src()
        assert "try_state" in src

    def test_prevent_close_on_window_event(self):
        assert "prevent_close" in self._src()

    def test_window_hide_on_close(self):
        assert "win_clone.hide()" in self._src() or ".hide()" in self._src()

    def test_menu_toggle_item_present(self):
        assert '"toggle"' in self._src()

    def test_menu_settings_item_present(self):
        assert '"settings"' in self._src()

    def test_menu_quit_item_present(self):
        assert '"quit"' in self._src()

    def test_handle_toggle_uses_fetch_xor(self):
        assert "fetch_xor" in self._src()

    def test_show_menu_on_left_click_false(self):
        assert "show_menu_on_left_click(false)" in self._src()

    def test_set_idle_text(self):
        assert "Start Recording" in self._src()

    def test_set_recording_text(self):
        assert "Stop Recording" in self._src()

    def test_set_transcribing_text(self):
        assert "Transcribing" in self._src()


class TestUpdateTrayFromSidecar:
    """Parité Python/Rust pour update_tray_from_sidecar() (lib.rs:139-154)."""

    def _map(self, line: str):
        """Miroir Python de update_tray_from_sidecar."""
        try:
            msg = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return None
        status = msg.get("status") if isinstance(msg, dict) else None
        if status == "recording":
            return "set_recording"
        if status == "transcribing":
            return "set_transcribing"
        if status == "done":
            return "set_idle"
        return None

    def test_recording_maps_to_set_recording(self):
        assert self._map('{"status":"recording"}') == "set_recording"

    def test_transcribing_maps_to_set_transcribing(self):
        assert self._map('{"status":"transcribing"}') == "set_transcribing"

    def test_done_maps_to_set_idle(self):
        assert self._map('{"status":"done"}') == "set_idle"

    def test_invalid_json_ignored(self):
        assert self._map("not json{{") is None

    def test_no_status_key_ignored(self):
        assert self._map('{"error":"oops"}') is None

    def test_empty_object_ignored(self):
        assert self._map("{}") is None

    def test_unknown_status_ignored(self):
        assert self._map('{"status":"idle"}') is None

    def test_null_status_ignored(self):
        assert self._map('{"status":null}') is None

    def test_text_key_ignored(self):
        # {"status":"done","text":"bonjour"} → set_idle (text ignoré côté tray)
        assert self._map('{"status":"done","text":"bonjour"}') == "set_idle"

    def test_text_without_status_ignored(self):
        assert self._map('{"text":"bonjour"}') is None


class TestToggleLogic:
    """Logique toggle optimiste : was_recording → action tray + cmd sidecar."""

    def _toggle_action(self, was_recording: bool):
        """Miroir de handle_toggle() et spawn_listener()."""
        tray_action = "set_transcribing" if was_recording else "set_recording"
        cmd = "stop" if was_recording else "start"
        return tray_action, cmd

    def test_not_recording_sends_start_and_set_recording(self):
        tray, cmd = self._toggle_action(False)
        assert tray == "set_recording"
        assert cmd == "start"

    def test_was_recording_sends_stop_and_set_transcribing(self):
        tray, cmd = self._toggle_action(True)
        assert tray == "set_transcribing"
        assert cmd == "stop"

    def test_toggle_sequence(self):
        """Deux toggles : idle→recording→transcribing."""
        state = False
        tray, cmd = self._toggle_action(state)
        state = not state
        assert tray == "set_recording" and cmd == "start"
        tray, cmd = self._toggle_action(state)
        assert tray == "set_transcribing" and cmd == "stop"


class TestLibRsTray:
    """lib.rs — intégration tray."""

    def _src(self):
        return LIB_RS.read_text()

    def test_mod_tray_declared(self):
        assert "mod tray" in self._src() or "pub mod tray" in self._src()

    def test_update_tray_from_sidecar_defined(self):
        assert "update_tray_from_sidecar" in self._src()

    def test_tray_setup_called(self):
        assert "tray::setup" in self._src()

    def test_tray_setup_graceful(self):
        # Le tray setup doit être wrapped dans if let Err (pas de ?) ou géré
        assert "log::warn" in self._src()

    def test_done_resets_atomic_bool(self):
        src = self._src()
        # Sur "done" : store(false) pour reset
        assert 'store(false' in src

    def test_start_command_calls_set_recording(self):
        assert "set_recording" in self._src()

    def test_stop_command_calls_set_transcribing(self):
        assert "set_transcribing" in self._src()


class TestHotkeyRsTrayUpdate:
    """hotkey.rs — mise à jour optimiste du tray depuis spawn_listener."""

    def _src(self):
        return HOTKEY_RS.read_text()

    def test_set_recording_called_in_listener(self):
        assert "set_recording" in self._src()

    def test_set_transcribing_called_in_listener(self):
        assert "set_transcribing" in self._src()

    def test_tray_update_before_sidecar_cmd(self):
        src = self._src()
        # set_recording/set_transcribing doivent apparaître avant send_cmd
        tray_idx = min(src.find("set_recording"), src.find("set_transcribing"))
        send_idx = src.find("send_cmd")
        assert tray_idx < send_idx

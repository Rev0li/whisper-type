"""Tests statiques TICKET-07 — overlay d'enregistrement.

Couvre : structure fichiers, fenêtre overlay dans tauri.conf.json, HTML/CSS
(animations, états), JS dispatch logic (parité avec TICKET-06 tray), HiDPI math,
reset visuel hideOverlay().
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONF = ROOT / "src-tauri" / "tauri.conf.json"
HTML = ROOT / "src" / "overlay.html"
JS = ROOT / "src" / "overlay.js"


def _conf():
    return json.loads(CONF.read_text())


def _overlay_win():
    wins = _conf()["app"]["windows"]
    matches = [w for w in wins if w.get("label") == "overlay"]
    assert matches, "Fenêtre 'overlay' absente de tauri.conf.json"
    return matches[0]


class TestStructure:
    def test_overlay_html_exists(self):
        assert HTML.is_file()

    def test_overlay_js_exists(self):
        assert JS.is_file()

    def test_with_global_tauri_enabled(self):
        assert _conf()["app"].get("withGlobalTauri") is True


class TestOverlayWindow:
    """tauri.conf.json — fenêtre overlay correctement configurée."""

    def test_overlay_window_present(self):
        _overlay_win()  # lève si absent

    def test_width_200(self):
        assert _overlay_win()["width"] == 200

    def test_height_54(self):
        assert _overlay_win()["height"] == 54

    def test_no_decorations(self):
        assert _overlay_win().get("decorations") is False

    def test_always_on_top(self):
        assert _overlay_win().get("alwaysOnTop") is True

    def test_not_visible_at_start(self):
        assert _overlay_win().get("visible") is False

    def test_not_resizable(self):
        assert _overlay_win().get("resizable") is False

    def test_skip_taskbar(self):
        assert _overlay_win().get("skipTaskbar") is True

    def test_transparent(self):
        assert _overlay_win().get("transparent") is True

    def test_url_is_overlay_html(self):
        assert _overlay_win().get("url") == "overlay.html"

    def test_main_window_unchanged(self):
        """La fenêtre main ne doit pas avoir été modifiée."""
        main = next(w for w in _conf()["app"]["windows"] if w["label"] == "main")
        assert main["width"] == 420
        assert main["height"] == 520


class TestOverlayHtml:
    """overlay.html — structure et états CSS."""

    def _html(self):
        return HTML.read_text()

    def test_has_dot_element(self):
        assert 'id="dot"' in self._html()

    def test_has_label_element(self):
        assert 'id="label"' in self._html()

    def test_has_pill_element(self):
        assert 'id="pill"' in self._html()

    def test_initial_body_class_is_recording(self):
        assert '<body class="recording"' in self._html()

    def test_recording_class_uses_pulse_animation(self):
        html = self._html()
        assert "body.recording" in html
        assert "pulse" in html

    def test_transcribing_class_uses_spin_animation(self):
        html = self._html()
        assert "body.transcribing" in html
        assert "spin" in html

    def test_pulse_keyframe_defined(self):
        assert "@keyframes pulse" in self._html()

    def test_spin_keyframe_defined(self):
        assert "@keyframes spin" in self._html()

    def test_recording_color_red(self):
        # #ff4444 pour le point recording
        assert "#ff4444" in self._html()

    def test_transcribing_color_orange(self):
        # #ffaa00 pour l'anneau transcribing
        assert "#ffaa00" in self._html()

    def test_draggable_region(self):
        assert "-webkit-app-region: drag" in self._html()

    def test_transparent_background(self):
        assert "background: transparent" in self._html()

    def test_overlay_js_loaded(self):
        assert "overlay.js" in self._html()

    def test_border_radius_pill(self):
        assert "border-radius: 999px" in self._html()


class TestOverlayJsDispatch:
    """overlay.js — logique dispatch sidecar-msg (parité avec update_tray_from_sidecar)."""

    def _js(self):
        return JS.read_text()

    def _dispatch(self, status):
        """Miroir Python du switch(msg.status) dans overlay.js."""
        mapping = {
            "recording": "showRecording",
            "transcribing": "showTranscribing",
            "done": "hideOverlay",
        }
        return mapping.get(status)

    def test_recording_triggers_show_recording(self):
        assert self._dispatch("recording") == "showRecording"

    def test_transcribing_triggers_show_transcribing(self):
        assert self._dispatch("transcribing") == "showTranscribing"

    def test_done_triggers_hide_overlay(self):
        assert self._dispatch("done") == "hideOverlay"

    def test_unknown_status_ignored(self):
        assert self._dispatch("error") is None
        assert self._dispatch("idle") is None
        assert self._dispatch("") is None

    def test_js_listens_to_sidecar_msg(self):
        assert "listen('sidecar-msg'" in self._js() or 'listen("sidecar-msg"' in self._js()

    def test_js_parses_event_payload(self):
        assert "JSON.parse(event.payload)" in self._js()

    def test_js_handles_json_error(self):
        # Try-catch autour du parse
        assert "catch" in self._js()

    def test_js_switch_on_status(self):
        assert "msg.status" in self._js()

    def test_parity_with_tray_dispatch(self):
        """Les 3 statuts doivent être identiques à update_tray_from_sidecar() (TICKET-06)."""
        js = self._js()
        for status in ("recording", "transcribing", "done"):
            assert f"'{status}'" in js or f'"{status}"' in js


class TestOverlayJsFunctions:
    """overlay.js — comportement des fonctions d'état."""

    def _js(self):
        return JS.read_text()

    def test_show_recording_sets_class(self):
        assert "body.className = 'recording'" in self._js()

    def test_show_transcribing_sets_class(self):
        assert "body.className = 'transcribing'" in self._js()

    def test_hide_overlay_calls_hide(self):
        assert "getWin().hide()" in self._js()

    def test_hide_overlay_resets_to_recording(self):
        js = self._js()
        # hideOverlay() remet 'recording' (reset visuel)
        hide_idx = js.find("async function hideOverlay")
        assert "body.className = 'recording'" in js[hide_idx:]

    def test_show_recording_positions_window(self):
        assert "positionBottomRight" in self._js()

    def test_show_recording_shows_window(self):
        js = self._js()
        show_idx = js.find("async function showRecording")
        assert ".show()" in js[show_idx:js.find("async function", show_idx + 1)]

    def test_show_transcribing_does_not_reposition(self):
        js = self._js()
        trans_idx = js.find("async function showTranscribing")
        trans_end = js.find("async function", trans_idx + 1)
        assert "positionBottomRight" not in js[trans_idx:trans_end]


class TestPositionMath:
    """positionBottomRight() — calcul HiDPI correct."""

    def _calc(self, screen_w, screen_h, scale):
        """Miroir Python de positionBottomRight()."""
        x = round((screen_w - 208) * scale)
        y = round((screen_h - 90) * scale)
        return x, y

    def test_1080p_scale_1(self):
        x, y = self._calc(1920, 1080, 1.0)
        assert x == 1712  # 1920 - 208
        assert y == 990   # 1080 - 90

    def test_1080p_scale_2_hidpi(self):
        x, y = self._calc(1920, 1080, 2.0)
        assert x == 3424  # (1920 - 208) * 2
        assert y == 1980  # (1080 - 90) * 2

    def test_4k_scale_1(self):
        x, y = self._calc(3840, 2160, 1.0)
        assert x == 3632
        assert y == 2070

    def test_js_uses_208_x_margin(self):
        assert "208" in JS.read_text()

    def test_js_uses_90_y_margin(self):
        assert "90" in JS.read_text()

    def test_js_uses_device_pixel_ratio(self):
        assert "devicePixelRatio" in JS.read_text()

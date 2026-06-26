"""Tests scaffold Tauri v2 — TICKET-03.

Vérifie la structure de fichiers, les valeurs critiques de tauri.conf.json,
le .gitignore, et le package.json sans nécessiter cargo ou display.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC_TAURI = ROOT / "src-tauri"
SRC = ROOT / "src"


class TestScaffoldStructure:
    """Tous les fichiers attendus du scaffold existent."""

    def test_src_tauri_dir(self):
        assert SRC_TAURI.is_dir()

    def test_tauri_conf_json(self):
        assert (SRC_TAURI / "tauri.conf.json").is_file()

    def test_cargo_toml(self):
        assert (SRC_TAURI / "Cargo.toml").is_file()

    def test_cargo_lock(self):
        assert (SRC_TAURI / "Cargo.lock").is_file()

    def test_build_rs(self):
        assert (SRC_TAURI / "build.rs").is_file()

    def test_main_rs(self):
        assert (SRC_TAURI / "src" / "main.rs").is_file()

    def test_lib_rs(self):
        assert (SRC_TAURI / "src" / "lib.rs").is_file()

    def test_capabilities_default(self):
        assert (SRC_TAURI / "capabilities" / "default.json").is_file()

    def test_frontend_index_html(self):
        assert (SRC / "index.html").is_file()

    def test_frontend_styles_css(self):
        assert (SRC / "styles.css").is_file()

    def test_frontend_main_js(self):
        assert (SRC / "main.js").is_file()

    def test_package_json(self):
        assert (ROOT / "package.json").is_file()


class TestTauriConf:
    """tauri.conf.json — valeurs critiques."""

    def _conf(self):
        return json.loads((SRC_TAURI / "tauri.conf.json").read_text())

    def test_identifier(self):
        assert self._conf()["identifier"] == "dev.rev0li.whisper-type"

    def test_product_name(self):
        assert self._conf()["productName"] == "whisper-type"

    def test_window_width(self):
        win = self._conf()["app"]["windows"][0]
        assert win["width"] == 420

    def test_window_height(self):
        win = self._conf()["app"]["windows"][0]
        assert win["height"] == 520

    def test_window_not_resizable(self):
        win = self._conf()["app"]["windows"][0]
        assert win["resizable"] is False

    def test_window_visible_false(self):
        win = self._conf()["app"]["windows"][0]
        assert win["visible"] is False

    def test_frontend_dist_points_to_src(self):
        assert self._conf()["build"]["frontendDist"] == "../src"

    def test_no_android_bundle(self):
        conf = self._conf()
        assert "android" not in conf


class TestGitignore:
    """.gitignore contient les entrées cross-platform nécessaires."""

    def _lines(self):
        return (ROOT / ".gitignore").read_text().splitlines()

    def test_ignores_tauri_target(self):
        assert "src-tauri/target/" in self._lines()

    def test_ignores_node_modules(self):
        assert "node_modules/" in self._lines()


class TestPackageJson:
    """package.json — Tauri v2 CLI déclarée."""

    def _pkg(self):
        return json.loads((ROOT / "package.json").read_text())

    def test_has_tauri_cli_v2(self):
        deps = self._pkg().get("devDependencies", {})
        cli = deps.get("@tauri-apps/cli", "")
        assert cli.startswith("^2") or cli.startswith("2")

    def test_dev_script_uses_tauri_dev(self):
        scripts = self._pkg().get("scripts", {})
        assert scripts.get("dev") == "tauri dev"


class TestCargoToml:
    """Cargo.toml — Tauri v2 comme dépendance."""

    def _content(self):
        return (SRC_TAURI / "Cargo.toml").read_text()

    def test_tauri_v2_dependency(self):
        content = self._content()
        assert 'tauri = { version = "2.' in content

    def test_tauri_build_v2(self):
        content = self._content()
        assert 'tauri-build = { version = "2.' in content

    def test_edition_2021(self):
        assert 'edition = "2021"' in self._content()


class TestFrontend:
    """Contenu frontend — éléments UI attendus présents."""

    def test_html_has_model_select(self):
        html = (SRC / "index.html").read_text()
        assert 'id="model"' in html

    def test_html_has_language_select(self):
        html = (SRC / "index.html").read_text()
        assert 'id="language"' in html

    def test_html_has_hotkey_input(self):
        html = (SRC / "index.html").read_text()
        assert 'id="hotkey"' in html

    def test_html_has_save_button(self):
        html = (SRC / "index.html").read_text()
        assert 'id="save"' in html

    def test_js_hotkey_keydown_listener(self):
        js = (SRC / "main.js").read_text()
        assert "keydown" in js

    def test_js_grave_conversion(self):
        js = (SRC / "main.js").read_text()
        assert '"grave"' in js or "'grave'" in js

    def test_js_todo_ticket_08(self):
        js = (SRC / "main.js").read_text()
        assert "TICKET-08" in js

"""Tests statiques TICKET-08 — settings panel.

Couvre : config.rs (struct, defaults, write format, config_path), validation
whitelist (VALID_MODELS/VALID_LANGUAGES), lib.rs (get/save_settings, restart_sidecar,
fix HotkeyManagerState None), index.html (options élargies), main.js (invoke
namespace, loadSettings, save feedback, fix modificateurs hotkey).
"""

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_RS = ROOT / "src-tauri" / "src" / "config.rs"
LIB_RS    = ROOT / "src-tauri" / "src" / "lib.rs"
HOTKEY_RS = ROOT / "src-tauri" / "src" / "hotkey.rs"
HTML      = ROOT / "src" / "index.html"
JS        = ROOT / "src" / "main.js"


class TestConfigRsStructure:
    """config.rs — structure et présence des symboles."""

    def _src(self):
        return CONFIG_RS.read_text()

    def test_config_rs_exists(self):
        assert CONFIG_RS.is_file()

    def test_config_struct_defined(self):
        assert "pub struct Config" in self._src()

    def test_defaults_defined(self):
        assert "fn defaults" in self._src()

    def test_config_path_defined(self):
        assert "fn config_path" in self._src()

    def test_read_fn_defined(self):
        assert "pub fn read" in self._src()

    def test_write_fn_defined(self):
        assert "pub fn write" in self._src()


class TestConfigRsDefaults:
    """Valeurs par défaut dans config.rs — cohérence avec config.py (TICKET-01)."""

    def _src(self):
        return CONFIG_RS.read_text()

    def test_default_model_is_small(self):
        assert '"small"' in self._src()

    def test_default_language_is_fr(self):
        assert '"fr"' in self._src()

    def test_default_hotkey_is_super_grave(self):
        assert '"SUPER+grave"' in self._src()

    def test_config_path_uses_home(self):
        src = self._src()
        assert '"HOME"' in src

    def test_config_path_uses_userprofile_fallback(self):
        # Windows fallback
        assert '"USERPROFILE"' in self._src()


class TestConfigWriteFormat:
    """config::write() génère un TOML valide parseable."""

    def _simulate_write(self, model, language, hotkey):
        """Miroir Python de config::write() format string."""
        return f'model = "{model}"\nlanguage = "{language}"\nhotkey = "{hotkey}"\n'

    def test_write_format_is_valid_toml(self):
        content = self._simulate_write("small", "fr", "SUPER+grave")
        parsed = tomllib.loads(content)
        assert parsed["model"] == "small"
        assert parsed["language"] == "fr"
        assert parsed["hotkey"] == "SUPER+grave"

    def test_write_format_string_in_config_rs(self):
        src = CONFIG_RS.read_text()
        assert 'model = \\"{model}\\"' in src or "model = \"{model}\"" in src

    def test_write_medium_model(self):
        content = self._simulate_write("medium", "en", "CTRL+SHIFT+SPACE")
        parsed = tomllib.loads(content)
        assert parsed["model"] == "medium"

    def test_write_auto_language(self):
        content = self._simulate_write("base", "auto", "SUPER+grave")
        parsed = tomllib.loads(content)
        assert parsed["language"] == "auto"


class TestValidationWhitelist:
    """VALID_MODELS et VALID_LANGUAGES dans lib.rs."""

    def _src(self):
        return LIB_RS.read_text()

    EXPECTED_MODELS = ["tiny", "base", "small", "medium", "large"]
    EXPECTED_LANGUAGES = ["fr", "en", "de", "es", "it", "pt", "nl", "ru", "zh", "ja", "ko", "auto"]

    def test_valid_models_defined(self):
        assert "VALID_MODELS" in self._src()

    def test_valid_languages_defined(self):
        assert "VALID_LANGUAGES" in self._src()

    def test_all_expected_models_present(self):
        src = self._src()
        for m in self.EXPECTED_MODELS:
            assert f'"{m}"' in src, f"Modèle '{m}' absent de VALID_MODELS"

    def test_all_expected_languages_present(self):
        src = self._src()
        for lang in self.EXPECTED_LANGUAGES:
            assert f'"{lang}"' in src, f"Langue '{lang}' absente de VALID_LANGUAGES"

    def test_large_model_in_whitelist(self):
        assert '"large"' in self._src()

    def test_auto_language_in_whitelist(self):
        assert '"auto"' in self._src()


class TestValidationLogic:
    """Logique validation save_settings — parité Python/Rust."""

    VALID_MODELS = ["tiny", "base", "small", "medium", "large"]
    VALID_LANGUAGES = ["fr", "en", "de", "es", "it", "pt", "nl", "ru", "zh", "ja", "ko", "auto"]

    def _validate(self, model, language, hotkey):
        """Miroir Python de save_settings validation (sans parse_hotkey Rust)."""
        if model not in self.VALID_MODELS:
            return False, f"Modèle invalide : {model}"
        if language not in self.VALID_LANGUAGES:
            return False, f"Langue invalide : {language}"
        return True, None

    def test_valid_small_fr(self):
        ok, _ = self._validate("small", "fr", "SUPER+grave")
        assert ok

    def test_valid_large_auto(self):
        ok, _ = self._validate("large", "auto", "CTRL+SHIFT+SPACE")
        assert ok

    def test_invalid_model_xlarge(self):
        ok, err = self._validate("xlarge", "fr", "SUPER+grave")
        assert not ok
        assert "invalide" in err.lower()

    def test_invalid_language_unknown(self):
        ok, err = self._validate("small", "jp", "SUPER+grave")
        assert not ok
        assert "invalide" in err.lower()

    def test_invalid_model_large_v2(self):
        # "large-v2" pas dans la whitelist
        ok, _ = self._validate("large-v2", "fr", "SUPER+grave")
        assert not ok

    def test_all_valid_models_accepted(self):
        for m in self.VALID_MODELS:
            ok, _ = self._validate(m, "fr", "SUPER+grave")
            assert ok, f"Modèle '{m}' refusé à tort"

    def test_all_valid_languages_accepted(self):
        for lang in self.VALID_LANGUAGES:
            ok, _ = self._validate("small", lang, "SUPER+grave")
            assert ok, f"Langue '{lang}' refusée à tort"


class TestLibRsSettings:
    """lib.rs — structure settings et fix TICKET-05."""

    def _src(self):
        return LIB_RS.read_text()

    def test_mod_config_declared(self):
        assert "mod config" in self._src()

    def test_get_settings_command(self):
        assert "fn get_settings" in self._src()

    def test_save_settings_command(self):
        assert "fn save_settings" in self._src()

    def test_get_save_in_invoke_handler(self):
        src = self._src()
        assert "get_settings" in src and "save_settings" in src

    def test_restart_sidecar_helper(self):
        assert "fn restart_sidecar" in self._src()

    def test_spawn_stdout_reader_extracted(self):
        assert "fn spawn_stdout_reader" in self._src()

    def test_hotkey_manager_state_is_option(self):
        # Fix TICKET-05 : Mutex<Option<hotkey::HotkeyManager>>
        assert "Mutex<Option<hotkey::HotkeyManager>>" in self._src()

    def test_hotkey_manager_managed_on_failure(self):
        # Wayland natif : app.manage(HotkeyManagerState(Mutex::new(None)))
        src = self._src()
        assert "Mutex::new(None)" in src

    def test_restart_only_on_model_lang_change(self):
        src = self._src()
        assert "model_changed || lang_changed" in src or "model_changed" in src

    def test_settings_struct_with_serde(self):
        assert "serde::Deserialize" in self._src()


class TestIndexHtml:
    """index.html — options élargies."""

    def _html(self):
        return HTML.read_text()

    def test_large_model_option(self):
        assert 'value="large"' in self._html()

    def test_german_language_option(self):
        assert 'value="de"' in self._html()

    def test_spanish_language_option(self):
        assert 'value="es"' in self._html()

    def test_italian_language_option(self):
        assert 'value="it"' in self._html()

    def test_portuguese_language_option(self):
        assert 'value="pt"' in self._html()

    def test_auto_language_still_present(self):
        assert 'value="auto"' in self._html()

    def test_all_four_original_models_present(self):
        html = self._html()
        for m in ["tiny", "base", "small", "medium"]:
            assert f'value="{m}"' in html


class TestMainJs:
    """main.js — invoke Tauri v2, loadSettings, save feedback, fix hotkey."""

    def _js(self):
        return JS.read_text()

    def test_uses_core_invoke_namespace(self):
        # Tauri v2 : window.__TAURI__.core.invoke
        assert "__TAURI__.core.invoke" in self._js()

    def test_load_settings_calls_get_settings(self):
        assert "get_settings" in self._js()

    def test_save_settings_command_invoked(self):
        assert "save_settings" in self._js()

    def test_save_payload_has_settings_key(self):
        assert "settings:" in self._js()

    def test_button_disabled_during_save(self):
        assert "saveBtn.disabled = true" in self._js()

    def test_button_re_enabled_in_finally(self):
        assert "saveBtn.disabled = false" in self._js()

    def test_status_saving_feedback(self):
        assert "Enregistrement" in self._js()

    def test_status_saved_feedback(self):
        assert "Sauvegardé" in self._js()

    def test_error_displayed_on_failure(self):
        assert "Erreur" in self._js()

    def test_status_cleared_after_timeout(self):
        assert "setTimeout" in self._js()

    def test_hotkey_ctrl_guard(self):
        # Fix : CTRL seulement si key !== 'Control'
        assert "e.key !== 'Control'" in self._js() or 'e.key !== "Control"' in self._js()

    def test_hotkey_shift_guard(self):
        assert "e.key !== 'Shift'" in self._js() or 'e.key !== "Shift"' in self._js()

    def test_hotkey_alt_guard(self):
        assert "e.key !== 'Alt'" in self._js() or 'e.key !== "Alt"' in self._js()

    def test_fallback_hotkey_on_empty(self):
        assert "SUPER+grave" in self._js()

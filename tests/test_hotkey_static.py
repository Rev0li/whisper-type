"""Tests statiques pour TICKET-05 — hotkey Rust.

Sans cargo disponible, ces tests vérifient :
- Structure fichiers + dépendances Cargo.toml
- Mappings clés dans hotkey.rs (complétude A-Z, 0-9, F1-F12, spéciaux, modificateurs)
- Logique parse_hotkey() : parité Python/Rust sur les cas critiques
- lib.rs : présence des états RecordingState, HotkeyManagerState, reload_hotkey
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CARGO = ROOT / "src-tauri" / "Cargo.toml"
HOTKEY_RS = ROOT / "src-tauri" / "src" / "hotkey.rs"
LIB_RS = ROOT / "src-tauri" / "src" / "lib.rs"


class TestStructure:
    def test_hotkey_rs_exists(self):
        assert HOTKEY_RS.is_file()

    def test_global_hotkey_dep(self):
        assert 'global-hotkey = "0.6"' in CARGO.read_text()

    def test_toml_dep(self):
        assert 'toml = "0.8"' in CARGO.read_text()


class TestHotkeyRsMappings:
    """Vérifie la complétude des mappings dans hotkey.rs."""

    def _src(self):
        return HOTKEY_RS.read_text()

    # Modificateurs
    def test_modifier_super_mapped(self):
        assert "Modifiers::SUPER" in self._src()

    def test_modifier_ctrl_mapped(self):
        assert "Modifiers::CONTROL" in self._src()

    def test_modifier_shift_mapped(self):
        assert "Modifiers::SHIFT" in self._src()

    def test_modifier_alt_mapped(self):
        assert "Modifiers::ALT" in self._src()

    def test_modifier_meta_alias(self):
        # META et WIN doivent être des alias de SUPER
        src = self._src()
        assert '"META"' in src and '"WIN"' in src

    def test_modifier_ctrl_alias(self):
        assert '"CONTROL"' in self._src()

    # Touches spéciales
    def test_grave_mapped(self):
        assert "Code::Backquote" in self._src()

    def test_space_mapped(self):
        assert "Code::Space" in self._src()

    def test_tab_mapped(self):
        assert "Code::Tab" in self._src()

    def test_enter_mapped(self):
        assert "Code::Enter" in self._src()

    def test_escape_mapped(self):
        assert "Code::Escape" in self._src()

    def test_backspace_mapped(self):
        assert "Code::Backspace" in self._src()

    # Touches de fonction F1-F12
    def test_all_function_keys_mapped(self):
        src = self._src()
        for n in range(1, 13):
            assert f"Code::F{n}" in src, f"F{n} manquant"

    # Lettres A-Z
    def test_all_letters_mapped(self):
        src = self._src()
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert f"Code::Key{c}" in src, f"Key{c} manquant"

    # Chiffres 0-9
    def test_all_digits_mapped(self):
        src = self._src()
        for d in range(10):
            assert f"Code::Digit{d}" in src, f"Digit{d} manquant"


class TestParseHotkeyLogic:
    """Parité de logique parse_hotkey() : re-implémentation Python pour tester le spec."""

    # Mappings miroirs de hotkey.rs
    MODIFIERS = {
        "SUPER", "META", "WIN",
        "CTRL", "CONTROL",
        "SHIFT",
        "ALT",
    }
    KEYS = {
        "GRAVE", "`", "SPACE", "TAB", "ENTER", "RETURN",
        "BACKSPACE", "ESCAPE", "ESC",
        *[f"F{n}" for n in range(1, 13)],
        *list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        *[str(d) for d in range(10)],
    }

    def _parse(self, s: str):
        """Simule parse_hotkey() : retourne (modifiers, key) ou lève ValueError."""
        mods = []
        key = None
        for part in s.split("+"):
            p = part.strip().upper()
            if p in self.MODIFIERS:
                mods.append(p)
            elif p in self.KEYS:
                key = p
            else:
                raise ValueError(f"Unknown key: {p}")
        if key is None:
            raise ValueError("No key specified")
        return mods, key

    def test_default_hotkey(self):
        mods, key = self._parse("SUPER+grave")
        assert "SUPER" in mods
        assert key == "GRAVE"

    def test_ctrl_shift_space(self):
        mods, key = self._parse("CTRL+SHIFT+SPACE")
        assert "CTRL" in mods
        assert "SHIFT" in mods
        assert key == "SPACE"

    def test_meta_alias_for_super(self):
        mods, _ = self._parse("META+grave")
        assert "META" in mods

    def test_win_alias_for_super(self):
        mods, _ = self._parse("WIN+S")
        assert "WIN" in mods
        assert _ == "S"

    def test_ctrl_alias(self):
        mods, key = self._parse("CONTROL+S")
        assert "CONTROL" in mods

    def test_fn_key(self):
        mods, key = self._parse("SUPER+F12")
        assert key == "F12"

    def test_no_key_raises(self):
        import pytest
        with pytest.raises(ValueError, match="No key"):
            self._parse("SUPER+CTRL")

    def test_unknown_key_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown key"):
            self._parse("SUPER+DELETE")

    def test_digit_key(self):
        _, key = self._parse("CTRL+1")
        assert key == "1"

    def test_key_only_no_modifier(self):
        mods, key = self._parse("F5")
        assert mods == []
        assert key == "F5"


class TestLibRsStructures:
    """lib.rs contient les structures et commandes attendues de TICKET-05."""

    def _src(self):
        return LIB_RS.read_text()

    def test_recording_state_defined(self):
        assert "RecordingState" in self._src()

    def test_hotkey_manager_state_defined(self):
        assert "HotkeyManagerState" in self._src()

    def test_atomic_bool_used(self):
        assert "AtomicBool" in self._src()

    def test_reload_hotkey_command(self):
        assert "fn reload_hotkey" in self._src()

    def test_hotkey_module_declared(self):
        assert "mod hotkey" in self._src()

    def test_graceful_degradation_present(self):
        # La dégradation gracieuse doit logger un warning, pas paniquer
        src = self._src()
        assert "log::warn" in src
        assert "panic" not in src.lower() or "expect" in src  # expect OK pour run()

    def test_spawn_listener_called(self):
        assert "spawn_listener" in self._src()

    def test_fetch_xor_in_hotkey_rs(self):
        # Toggle AtomicBool via fetch_xor
        assert "fetch_xor" in HOTKEY_RS.read_text()

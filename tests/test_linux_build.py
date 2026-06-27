"""Tests statiques TICKET-11 — build Linux (AppImage) via GitHub Actions.

Couvre : job build-linux dans release.yml (runner, permissions, apt-get deps,
PyInstaller flags bash-syntax, triple Linux, cp sans .exe, artifacts AppImage/.deb,
generate_release_notes: false), cohérence avec build-windows (même pattern),
README (ligne Linux, note XWayland).
"""

from pathlib import Path

ROOT     = Path(__file__).parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
README   = ROOT / "README.md"
LIB_RS   = ROOT / "src-tauri" / "src" / "lib.rs"


def _yml():
    return WORKFLOW.read_text()


# ─── Présence du job build-linux ──────────────────────────────────────────────

class TestBuildLinuxJob:
    """Job build-linux présent et correctement configuré."""

    def test_build_linux_job_defined(self):
        assert "build-linux:" in _yml()

    def test_runs_on_ubuntu_latest(self):
        yml = _yml()
        linux_idx = yml.find("build-linux:")
        snippet = yml[linux_idx:linux_idx + 200]
        assert "ubuntu-latest" in snippet

    def test_permissions_contents_write(self):
        yml = _yml()
        linux_idx = yml.find("build-linux:")
        # Cherche dans le bloc build-linux
        next_job = yml.find("\n  build-", linux_idx + 1)
        block = yml[linux_idx:next_job] if next_job != -1 else yml[linux_idx:]
        assert "contents: write" in block

    def test_both_jobs_present(self):
        yml = _yml()
        assert "build-windows:" in yml
        assert "build-linux:" in yml


# ─── System dependencies (apt-get) ───────────────────────────────────────────

class TestAptGetDeps:
    """Paquets système requis pour Tauri v2 + sounddevice + PyInstaller sur Ubuntu."""

    def test_apt_get_update(self):
        assert "apt-get update" in _yml()

    def test_libwebkit2gtk_41(self):
        # Tauri v2 requiert 4.1 (pas 4.0)
        assert "libwebkit2gtk-4.1-dev" in _yml()

    def test_build_essential(self):
        assert "build-essential" in _yml()

    def test_libssl_dev(self):
        assert "libssl-dev" in _yml()

    def test_libgtk_3_dev(self):
        assert "libgtk-3-dev" in _yml()

    def test_libayatana_appindicator(self):
        # Requis pour le tray icon (TICKET-06)
        assert "libayatana-appindicator3-dev" in _yml()

    def test_librsvg2_dev(self):
        assert "librsvg2-dev" in _yml()

    def test_portaudio19_dev(self):
        # Requis pour sounddevice (PortAudio bindings)
        assert "portaudio19-dev" in _yml()

    def test_libasound2_dev(self):
        assert "libasound2-dev" in _yml()

    def test_patchelf(self):
        # Requis par PyInstaller pour patcher les rpaths sur Linux
        assert "patchelf" in _yml()


# ─── PyInstaller Linux (bash syntax) ─────────────────────────────────────────

class TestPyInstallerLinux:
    """PyInstaller dans build-linux — mêmes flags que Windows, syntaxe bash."""

    def _linux_block(self):
        yml = _yml()
        idx = yml.find("build-linux:")
        return yml[idx:]

    def test_pyinstaller_onefile(self):
        assert "--onefile" in self._linux_block()

    def test_collect_all_faster_whisper(self):
        assert "--collect-all faster_whisper" in self._linux_block()

    def test_collect_all_ctranslate2(self):
        assert "--collect-all ctranslate2" in self._linux_block()

    def test_collect_all_sounddevice(self):
        assert "--collect-all sounddevice" in self._linux_block()

    def test_exclude_module_keyboard(self):
        assert "--exclude-module keyboard" in self._linux_block()

    def test_name_whisper_type(self):
        assert "--name whisper_type" in self._linux_block()

    def test_bash_line_continuation_not_powershell(self):
        # Linux doit utiliser \ (bash), pas ` (PowerShell)
        block = self._linux_block()
        pyinstaller_idx = block.find("pyinstaller --onefile \\")
        assert pyinstaller_idx != -1, "Syntaxe bash \\ attendue dans build-linux"

    def test_requirements_installed(self):
        assert "requirements.txt" in self._linux_block()


# ─── Staging du sidecar (Linux, no .exe) ────────────────────────────────────

class TestSidecarStagingLinux:
    """cp dist/whisper_type → binaries/ avec le triple Linux."""

    def _linux_block(self):
        return _yml()[_yml().find("build-linux:"):]

    def test_cp_command_not_copy_item(self):
        # Linux : cp, pas Copy-Item (PowerShell)
        block = self._linux_block()
        assert "cp dist/whisper_type" in block

    def test_no_exe_extension_in_source(self):
        # Sur Linux, pas de .exe
        block = self._linux_block()
        cp_idx = block.find("cp dist/whisper_type")
        line = block[cp_idx:cp_idx + 80]
        assert "whisper_type.exe" not in line

    def test_linux_triple_in_destination(self):
        assert "whisper_type-x86_64-unknown-linux-gnu" in self._linux_block()

    def test_mkdir_before_cp(self):
        block = self._linux_block()
        assert "mkdir -p src-tauri/binaries" in block

    def test_binaries_target_path(self):
        assert "src-tauri/binaries" in self._linux_block()


# ─── Rust target Linux ────────────────────────────────────────────────────────

class TestRustTargetLinux:
    """Target Rust x86_64-unknown-linux-gnu dans build-linux."""

    def _linux_block(self):
        return _yml()[_yml().find("build-linux:"):]

    def test_linux_rust_target(self):
        assert "x86_64-unknown-linux-gnu" in self._linux_block()

    def test_dtolnay_toolchain_stable(self):
        assert "dtolnay/rust-toolchain@stable" in self._linux_block()

    def test_rust_cache(self):
        assert "Swatinem/rust-cache@v2" in self._linux_block()

    def test_npm_run_build(self):
        assert "npm run build" in self._linux_block()


# ─── Artifacts Linux ──────────────────────────────────────────────────────────

class TestLinuxArtifacts:
    """Upload AppImage + .deb dans la Release GitHub."""

    def _linux_block(self):
        return _yml()[_yml().find("build-linux:"):]

    def test_uploads_appimage(self):
        assert ".AppImage" in self._linux_block()

    def test_appimage_bundle_path(self):
        assert "bundle/appimage" in self._linux_block()

    def test_uploads_deb(self):
        assert ".deb" in self._linux_block()

    def test_deb_bundle_path(self):
        assert "bundle/deb" in self._linux_block()

    def test_generate_release_notes_false(self):
        # Ne doit pas écraser les notes générées par build-windows
        block = self._linux_block()
        assert "generate_release_notes: false" in block

    def test_uses_gh_release_action(self):
        assert "softprops/action-gh-release@v2" in self._linux_block()


# ─── Cohérence Windows vs Linux ───────────────────────────────────────────────

class TestWindowsLinuxParity:
    """Les deux jobs suivent le même pattern — symétrie intentionnelle."""

    def _windows_block(self):
        yml = _yml()
        w_idx = yml.find("build-windows:")
        l_idx = yml.find("build-linux:")
        return yml[w_idx:l_idx]

    def _linux_block(self):
        return _yml()[_yml().find("build-linux:"):]

    def test_both_use_python_311(self):
        assert "python-version: '3.11'" in self._windows_block()
        assert "python-version: '3.11'" in self._linux_block()

    def test_both_use_node_20(self):
        assert "node-version: '20'" in self._windows_block()
        assert "node-version: '20'" in self._linux_block()

    def test_both_use_pyinstaller_onefile(self):
        assert "--onefile" in self._windows_block()
        assert "--onefile" in self._linux_block()

    def test_both_use_npm_run_build(self):
        assert "npm run build" in self._windows_block()
        assert "npm run build" in self._linux_block()

    def test_windows_generates_notes_linux_does_not(self):
        assert "generate_release_notes: true" in self._windows_block()
        assert "generate_release_notes: false" in self._linux_block()

    def test_different_os_runners(self):
        assert "windows-latest" in self._windows_block()
        assert "ubuntu-latest" in self._linux_block()

    def test_different_rust_targets(self):
        assert "x86_64-pc-windows-msvc" in self._windows_block()
        assert "x86_64-unknown-linux-gnu" in self._linux_block()

    def test_different_artifact_formats(self):
        windows = self._windows_block()
        linux = self._linux_block()
        assert ".exe" in windows and ".msi" in windows
        assert ".AppImage" in linux and ".deb" in linux


# ─── resolve_sidecar() Linux — pas d'extension .exe ─────────────────────────

class TestResolveSidecarLinux:
    """Vérification que resolve_sidecar() cherche whisper_type sans .exe sur Linux."""

    def _src(self):
        return LIB_RS.read_text()

    def test_cfg_windows_guards_exe_extension(self):
        # cfg!(windows) doit conditionner la recherche .exe vs sans extension
        assert 'cfg!(windows)' in self._src()

    def test_linux_path_without_exe(self):
        src = self._src()
        # Le Rust doit avoir un branch non-Windows qui cherche juste "whisper_type"
        assert '"whisper_type"' in src

    def test_windows_path_with_exe(self):
        assert '"whisper_type.exe"' in self._src()


# ─── README — section Linux ───────────────────────────────────────────────────

class TestReadmeLinux:
    """README.md — entrée Linux dans le tableau Download + note XWayland."""

    def _readme(self):
        return README.read_text()

    def test_linux_appimage_in_download_table(self):
        assert "AppImage" in self._readme()

    def test_linux_download_link(self):
        readme = self._readme()
        assert "Linux" in readme and "releases" in readme.lower()

    def test_xwayland_note(self):
        assert "XWayland" in self._readme() or "xwayland" in self._readme().lower()

    def test_wayland_hotkey_note(self):
        assert "Wayland" in self._readme()

    def test_display_env_var_mentioned(self):
        assert "DISPLAY" in self._readme()

    def test_deb_uploaded_in_workflow(self):
        # .deb uploadé dans la release (workflow) même si non listé dans README
        assert ".deb" in _yml()

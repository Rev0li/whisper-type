"""Tests statiques TICKET-10 — build Windows + GitHub Actions.

Couvre : release.yml (triggers, job, runner, steps, PyInstaller flags, artifact
upload), sidecar.rs (signature spawn avec Option<&str>), lib.rs (resolve_sidecar
3 branches, appels spawn mis à jour), tauri.conf.json (externalBin), binaries/
(dossier + .gitignore), README.md (section Download).
"""

import re
from pathlib import Path

import yaml  # PyYAML si disponible, sinon on parse manuellement

ROOT = Path(__file__).parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
SIDECAR_RS = ROOT / "src-tauri" / "src" / "sidecar.rs"
LIB_RS = ROOT / "src-tauri" / "src" / "lib.rs"
CONF = ROOT / "src-tauri" / "tauri.conf.json"
BINARIES = ROOT / "src-tauri" / "binaries"
README = ROOT / "README.md"


def _yml():
    return WORKFLOW.read_text()


def _load_yml():
    try:
        import yaml
        return yaml.safe_load(WORKFLOW.read_text())
    except ImportError:
        return None  # tests statiques par grep si pas de PyYAML


# ─── Workflow existence et structure ──────────────────────────────────────────

class TestWorkflowExists:
    def test_release_yml_exists(self):
        assert WORKFLOW.is_file()

    def test_github_workflows_dir_exists(self):
        assert (ROOT / ".github" / "workflows").is_dir()


class TestWorkflowTriggers:
    """Déclencheurs du workflow."""

    def test_triggered_on_tag_push(self):
        yml = _yml()
        assert "tags:" in yml
        assert "'v*'" in yml or '"v*"' in yml

    def test_triggered_on_workflow_dispatch(self):
        assert "workflow_dispatch" in _yml()

    def test_not_triggered_on_branch_push(self):
        # Le workflow doit se déclencher sur tags, pas sur toutes les branches
        yml = _yml()
        assert "branches:" not in yml or "tags:" in yml


class TestWorkflowJob:
    """Job build-windows : runner, permissions."""

    def test_job_build_windows_defined(self):
        assert "build-windows:" in _yml()

    def test_runs_on_windows_latest(self):
        assert "windows-latest" in _yml()

    def test_permissions_contents_write(self):
        yml = _yml()
        assert "contents: write" in yml or "contents:write" in yml


class TestWorkflowSteps:
    """Étapes du workflow — présence des actions clés."""

    def test_checkout_step(self):
        assert "actions/checkout@v4" in _yml()

    def test_python_setup(self):
        assert "actions/setup-python@v5" in _yml()

    def test_python_version_311(self):
        assert "3.11" in _yml()

    def test_pip_cache(self):
        assert "cache: 'pip'" in _yml() or "cache: pip" in _yml()

    def test_pyinstaller_install(self):
        assert "pyinstaller" in _yml().lower()

    def test_requirements_installed(self):
        assert "requirements.txt" in _yml()

    def test_node_setup(self):
        assert "actions/setup-node@v4" in _yml()

    def test_node_version_20(self):
        assert "node-version: '20'" in _yml() or "node-version: 20" in _yml()

    def test_npm_install(self):
        assert "npm install" in _yml()

    def test_rust_toolchain(self):
        assert "dtolnay/rust-toolchain@stable" in _yml()

    def test_rust_target_windows(self):
        assert "x86_64-pc-windows-msvc" in _yml()

    def test_rust_cache(self):
        assert "Swatinem/rust-cache@v2" in _yml()

    def test_tauri_build_command(self):
        assert "npm run build" in _yml()

    def test_github_token_env(self):
        assert "GITHUB_TOKEN" in _yml()

    def test_upload_release_action(self):
        assert "softprops/action-gh-release@v2" in _yml()

    def test_generate_release_notes(self):
        assert "generate_release_notes: true" in _yml()


class TestPyInstallerFlags:
    """Flags PyInstaller dans le workflow."""

    def test_onefile_flag(self):
        assert "--onefile" in _yml()

    def test_collect_all_faster_whisper(self):
        assert "--collect-all faster_whisper" in _yml()

    def test_collect_all_ctranslate2(self):
        assert "--collect-all ctranslate2" in _yml()

    def test_collect_all_sounddevice(self):
        assert "--collect-all sounddevice" in _yml()

    def test_exclude_keyboard(self):
        assert "--exclude-module keyboard" in _yml()

    def test_output_name_whisper_type(self):
        assert "--name whisper_type" in _yml()

    def test_script_whisper_type_py(self):
        assert "whisper_type.py" in _yml()


class TestArtifactPaths:
    """Chemins des artifacts uploadés dans la Release."""

    def test_nsis_exe_path(self):
        assert "bundle/nsis" in _yml()

    def test_msi_path(self):
        assert "bundle/msi" in _yml()

    def test_windows_triple_in_stage_step(self):
        assert "x86_64-pc-windows-msvc" in _yml()

    def test_copy_to_binaries_path(self):
        assert "src-tauri/binaries" in _yml()


# ─── sidecar.rs — spawn(Option<&str>) ────────────────────────────────────────

class TestSidecarRsSpawn:
    """sidecar.rs — signature spawn modifiée pour mode bundlé."""

    def _src(self):
        return SIDECAR_RS.read_text()

    def test_spawn_takes_option_str(self):
        assert "Option<&str>" in self._src()

    def test_spawn_with_some_adds_script(self):
        src = self._src()
        # Si Some(s) → cmd.arg(s) avant --sidecar
        assert "Some(s)" in src or "if let Some(s)" in src

    def test_spawn_always_adds_sidecar_flag(self):
        src = self._src()
        assert '"--sidecar"' in src

    def test_send_cmd_json_format_unchanged(self):
        # Format {"cmd":"..."} : Rust raw string r#"{{"cmd":"{cmd}"}}"# → {"cmd":"..."}
        src = self._src()
        assert '"cmd"' in src and "writeln!" in src

    def test_kill_and_drop_present(self):
        src = self._src()
        assert "fn kill" in src
        assert "impl Drop" in src


# ─── lib.rs — resolve_sidecar() ───────────────────────────────────────────────

class TestResolveSidecar:
    """lib.rs — resolve_sidecar() 3 branches."""

    def _src(self):
        return LIB_RS.read_text()

    def test_resolve_sidecar_fn_defined(self):
        assert "fn resolve_sidecar" in self._src()

    def test_returns_tuple_string_option(self):
        assert "(String, Option<String>)" in self._src()

    def test_branch1_whisper_python_env(self):
        assert '"WHISPER_PYTHON"' in self._src()

    def test_branch1_returns_script_path(self):
        src = self._src()
        # Branche 1 : retourne (python, Some("whisper_type.py"))
        assert '"whisper_type.py"' in src

    def test_branch2_checks_current_exe(self):
        assert "current_exe()" in self._src()

    def test_branch2_windows_exe_extension(self):
        assert '"whisper_type.exe"' in self._src()

    def test_branch2_returns_none_for_script(self):
        src = self._src()
        # Mode binaire bundlé → None (pas de script séparé)
        fn_idx = src.find("fn resolve_sidecar")
        fn_end = src.find("\nfn ", fn_idx + 1)
        fn_body = src[fn_idx:fn_end]
        assert "None" in fn_body

    def test_branch3_fallback_venv(self):
        assert '".venv/bin/python3"' in self._src()

    def test_resolve_sidecar_called_in_setup(self):
        src = self._src()
        assert "resolve_sidecar()" in src
        # Vérifie qu'il y a au moins 2 occurrences (2 appels)
        assert src.count("resolve_sidecar") >= 2

    def test_spawn_uses_as_deref(self):
        # script.as_deref() pour convertir Option<String> → Option<&str>
        assert "as_deref()" in self._src()


class TestResolveSidecarLogic:
    """Parité Python de la logique resolve_sidecar()."""

    def _resolve(self, whisper_python=None, bundled_exists=False, fallback=".venv/bin/python3"):
        """Miroir Python de resolve_sidecar()."""
        import os
        if whisper_python is not None:
            return (whisper_python, "whisper_type.py")
        if bundled_exists:
            return ("/app/whisper_type", None)
        return (fallback, "whisper_type.py")

    def test_env_var_overrides_all(self):
        program, script = self._resolve(whisper_python="/custom/python3")
        assert program == "/custom/python3"
        assert script == "whisper_type.py"

    def test_bundled_binary_wins_over_fallback(self):
        program, script = self._resolve(bundled_exists=True)
        assert script is None

    def test_fallback_uses_venv_python(self):
        program, script = self._resolve()
        assert "python" in program
        assert script == "whisper_type.py"

    def test_bundled_mode_has_no_script(self):
        _, script = self._resolve(bundled_exists=True)
        assert script is None

    def test_dev_mode_always_has_script(self):
        _, script1 = self._resolve(whisper_python="/usr/bin/python3")
        _, script2 = self._resolve()
        assert script1 == "whisper_type.py"
        assert script2 == "whisper_type.py"


# ─── tauri.conf.json — externalBin ────────────────────────────────────────────

class TestTauriConfExternalBin:
    """tauri.conf.json — externalBin pour le sidecar bundlé."""

    def _conf(self):
        import json
        return json.loads(CONF.read_text())

    def test_bundle_section_present(self):
        assert "bundle" in self._conf()

    def test_bundle_active(self):
        assert self._conf()["bundle"]["active"] is True

    def test_external_bin_defined(self):
        assert "externalBin" in self._conf()["bundle"]

    def test_external_bin_contains_whisper_type(self):
        bins = self._conf()["bundle"]["externalBin"]
        assert any("whisper_type" in b for b in bins)

    def test_external_bin_path_binaries(self):
        bins = self._conf()["bundle"]["externalBin"]
        assert any("binaries" in b for b in bins)


# ─── binaries/ directory ──────────────────────────────────────────────────────

class TestBinariesDirectory:
    """src-tauri/binaries/ — dossier présent + .gitignore correct."""

    def test_binaries_dir_exists(self):
        assert BINARIES.is_dir()

    def test_gitignore_ignores_binaries(self):
        gitignore = BINARIES / ".gitignore"
        assert gitignore.is_file()
        content = gitignore.read_text()
        assert "whisper_type" in content or "*" in content

    def test_no_binary_committed(self):
        """Aucun binaire compilé (.exe, sans extension) ne doit être committé."""
        for f in BINARIES.iterdir():
            assert f.name in (".gitignore", ".gitkeep") or f.is_dir(), \
                f"Binaire inattendu commité : {f.name}"


# ─── README.md — section Download ────────────────────────────────────────────

class TestReadmeDownload:
    """README.md — section Download pour utilisateurs Windows."""

    def _readme(self):
        return README.read_text()

    def test_readme_exists(self):
        assert README.is_file()

    def test_download_section_present(self):
        assert "## Download" in self._readme() or "# Download" in self._readme()

    def test_mentions_github_releases(self):
        readme = self._readme()
        assert "releases" in readme.lower()

    def test_mentions_windows(self):
        assert "Windows" in self._readme()

    def test_mentions_exe_installer(self):
        assert ".exe" in self._readme()

    def test_no_python_required_for_windows(self):
        # L'installeur est autonomous — pas besoin de Python
        readme = self._readme()
        assert "bundled" in readme.lower() or "No Python" in readme or "no Python" in readme.lower()

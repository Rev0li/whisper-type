"""Tests statiques TICKET-09 — téléchargement modèle + progress bar.

Couvre : model_in_cache() (paths HF, env vars, logique dir vide), MODEL_SIZES_MB,
download_model_with_progress() (repo_id, filtrage fichiers, events JSON, gestion
erreurs), _download_and_load() (flux nominal + erreur), sidecar_loop() check
proactif (model_cached / model_missing / download_model / check_model), lib.rs
(retry_download, handle_download_events), tauri.conf.json fenêtre download,
download.html, download.js.
"""

import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

ROOT = Path(__file__).parent.parent
LIB_RS = ROOT / "src-tauri" / "src" / "lib.rs"
CONF   = ROOT / "src-tauri" / "tauri.conf.json"
HTML   = ROOT / "src" / "download.html"
JS     = ROOT / "src" / "download.js"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_wt(monkeypatch):
    """Charge whisper_type avec toutes les dépendances lourdes mockées."""
    fake_cfg = MagicMock()
    fake_cfg.load.return_value = {"model": "small", "language": "fr", "hotkey": "SUPER+grave"}
    monkeypatch.setitem(sys.modules, "config", fake_cfg)
    for mod in ["faster_whisper", "sounddevice", "numpy", "keyboard", "pyperclip", "huggingface_hub"]:
        monkeypatch.setitem(sys.modules, mod, MagicMock())
    if "whisper_type" in sys.modules:
        del sys.modules["whisper_type"]
    import whisper_type
    return whisper_type


# ─── MODEL_SIZES_MB ───────────────────────────────────────────────────────────

class TestModelSizesMb:
    """MODEL_SIZES_MB — cohérence avec download.js."""

    def _wt(self, monkeypatch):
        return _load_wt(monkeypatch)

    EXPECTED = {"tiny": 75, "base": 141, "small": 461, "medium": 1530, "large": 3100}

    def test_all_five_models_present(self, monkeypatch):
        wt = self._wt(monkeypatch)
        for m in self.EXPECTED:
            assert m in wt.MODEL_SIZES_MB

    def test_tiny_is_75(self, monkeypatch):
        assert self._wt(monkeypatch).MODEL_SIZES_MB["tiny"] == 75

    def test_small_is_461(self, monkeypatch):
        assert self._wt(monkeypatch).MODEL_SIZES_MB["small"] == 461

    def test_large_is_3100(self, monkeypatch):
        assert self._wt(monkeypatch).MODEL_SIZES_MB["large"] == 3100

    def test_js_sizes_match_python(self):
        """MODEL_SIZES_MB dans download.js doit correspondre à Python."""
        js = JS.read_text()
        for model, mb in self.EXPECTED.items():
            assert str(mb) in js, f"{model}: {mb} MB absent de download.js"


# ─── model_in_cache() ─────────────────────────────────────────────────────────

class TestModelInCache:
    """model_in_cache() — détection du modèle dans le cache HuggingFace."""

    def test_returns_false_when_dir_absent(self, monkeypatch, tmp_path):
        wt = _load_wt(monkeypatch)
        monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
        assert wt.model_in_cache("small") is False

    def test_returns_false_when_snapshots_empty(self, monkeypatch, tmp_path):
        wt = _load_wt(monkeypatch)
        snapshots = tmp_path / "models--Systran--faster-whisper-small" / "snapshots"
        snapshots.mkdir(parents=True)
        monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
        assert wt.model_in_cache("small") is False

    def test_returns_true_when_snapshot_exists(self, monkeypatch, tmp_path):
        wt = _load_wt(monkeypatch)
        snapshots = tmp_path / "models--Systran--faster-whisper-small" / "snapshots"
        snapshots.mkdir(parents=True)
        (snapshots / "abc123").mkdir()
        monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
        assert wt.model_in_cache("small") is True

    def test_uses_hf_hub_cache_env_var(self, monkeypatch, tmp_path):
        wt = _load_wt(monkeypatch)
        custom = tmp_path / "custom_cache"
        snapshots = custom / "models--Systran--faster-whisper-tiny" / "snapshots"
        snapshots.mkdir(parents=True)
        (snapshots / "rev").mkdir()
        monkeypatch.setenv("HF_HUB_CACHE", str(custom))
        monkeypatch.delenv("HF_HOME", raising=False)
        assert wt.model_in_cache("tiny") is True

    def test_uses_hf_home_env_var(self, monkeypatch, tmp_path):
        wt = _load_wt(monkeypatch)
        hf_home = tmp_path / "hf_home"
        snapshots = hf_home / "hub" / "models--Systran--faster-whisper-base" / "snapshots"
        snapshots.mkdir(parents=True)
        (snapshots / "rev").mkdir()
        monkeypatch.setenv("HF_HOME", str(hf_home))
        monkeypatch.delenv("HF_HUB_CACHE", raising=False)
        assert wt.model_in_cache("base") is True

    def test_safe_name_format(self, monkeypatch):
        """Le path contient models--Systran--faster-whisper-{model_size}."""
        import whisper_type
        src = (ROOT / "whisper_type.py").read_text()
        assert "models--Systran--faster-whisper-" in src

    def test_snapshots_subdir_required(self, monkeypatch):
        """La vérification porte sur snapshots/, pas juste le dossier modèle."""
        src = (ROOT / "whisper_type.py").read_text()
        assert "snapshots" in src


# ─── download_model_with_progress() ───────────────────────────────────────────

class TestDownloadModelWithProgress:
    """download_model_with_progress() — repo_id, filtrage, events progress."""

    def _make_hf_mock(self, files):
        """Crée un mock huggingface_hub avec list_repo_files et hf_hub_download."""
        hf = MagicMock()
        hf.list_repo_files.return_value = iter(files)
        hf.hf_hub_download.return_value = "/cache/file"
        return hf

    def test_repo_id_format(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        hf = self._make_hf_mock(["model.bin"])
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
        wt.download_model_with_progress("small")
        call_args = hf.list_repo_files.call_args
        assert "Systran/faster-whisper-small" in str(call_args)

    def test_emits_download_progress_per_file(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        hf = self._make_hf_mock(["model.bin", "config.json"])
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
        wt.download_model_with_progress("small")
        out = capsys.readouterr().out
        events = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
        progress_events = [e for e in events if e.get("status") == "download_progress"]
        assert len(progress_events) >= 2

    def test_filters_msgpack_files(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        hf = self._make_hf_mock(["model.bin", "weights.msgpack", "config.json"])
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
        wt.download_model_with_progress("tiny")
        assert hf.hf_hub_download.call_count == 2  # msgpack filtré

    def test_filters_h5_files(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        hf = self._make_hf_mock(["model.bin", "weights.h5"])
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
        wt.download_model_with_progress("tiny")
        assert hf.hf_hub_download.call_count == 1  # .h5 filtré

    def test_progress_event_has_required_fields(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        hf = self._make_hf_mock(["model.bin"])
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
        wt.download_model_with_progress("small")
        out = capsys.readouterr().out
        events = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
        prog = [e for e in events if e.get("status") == "download_progress"][0]
        assert "percent" in prog
        assert "file" in prog
        assert "current" in prog
        assert "total" in prog

    def test_final_event_is_100_percent(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        hf = self._make_hf_mock(["model.bin", "config.json"])
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
        wt.download_model_with_progress("small")
        out = capsys.readouterr().out
        events = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
        last = [e for e in events if e.get("status") == "download_progress"][-1]
        assert last["percent"] == 100

    def test_emits_download_error_on_list_failure(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        hf = MagicMock()
        hf.list_repo_files.side_effect = ConnectionError("network down")
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
        try:
            wt.download_model_with_progress("small")
        except Exception:
            pass
        out = capsys.readouterr().out
        events = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
        errors = [e for e in events if e.get("status") == "download_error"]
        assert len(errors) == 1
        assert "network down" in errors[0]["error"]

    def test_emits_download_error_on_file_failure(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        hf = MagicMock()
        hf.list_repo_files.return_value = iter(["model.bin"])
        hf.hf_hub_download.side_effect = IOError("disk full")
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf)
        try:
            wt.download_model_with_progress("small")
        except Exception:
            pass
        out = capsys.readouterr().out
        events = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
        errors = [e for e in events if e.get("status") == "download_error"]
        assert len(errors) == 1


# ─── _download_and_load() ─────────────────────────────────────────────────────

class TestDownloadAndLoad:
    """_download_and_load() — séquence download → model_ready → load_model."""

    def test_emits_model_ready_on_success(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        monkeypatch.setattr(wt, "download_model_with_progress", lambda s: None)
        monkeypatch.setattr(wt, "load_model", lambda: None)
        wt._download_and_load()
        out = capsys.readouterr().out
        events = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
        assert {"status": "model_ready"} in events

    def test_does_not_emit_model_ready_on_error(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        monkeypatch.setattr(wt, "download_model_with_progress", lambda s: (_ for _ in ()).throw(IOError("fail")))
        monkeypatch.setattr(wt, "load_model", lambda: None)
        wt._download_and_load()
        out = capsys.readouterr().out
        events = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
        assert {"status": "model_ready"} not in events

    def test_calls_load_model_after_download(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        called = []
        monkeypatch.setattr(wt, "download_model_with_progress", lambda s: None)
        monkeypatch.setattr(wt, "load_model", lambda: called.append(True))
        wt._download_and_load()
        assert called == [True]

    def test_skips_load_model_on_error(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        called = []
        def bad_download(s):
            raise IOError("network")
        monkeypatch.setattr(wt, "download_model_with_progress", bad_download)
        monkeypatch.setattr(wt, "load_model", lambda: called.append(True))
        wt._download_and_load()
        assert called == []


# ─── sidecar_loop() check proactif ────────────────────────────────────────────

class TestSidecarLoopProactiveCheck:
    """sidecar_loop() — check model cache avant stdin."""

    def _run(self, wt, monkeypatch, lines, capsys, *, cache=True):
        monkeypatch.setattr(sys, "stdin", io.StringIO("\n".join(lines) + "\n"))
        monkeypatch.setattr(wt, "load_model", lambda: None)
        monkeypatch.setattr(wt, "start_recording", lambda: None)
        monkeypatch.setattr(wt, "stop_and_transcribe", lambda: None)
        monkeypatch.setattr(wt, "notify", lambda *a, **kw: None)
        monkeypatch.setattr(wt, "_download_and_load", lambda: None)
        monkeypatch.setattr(wt, "model_in_cache", lambda s: cache)
        wt.sidecar_loop()
        out = capsys.readouterr().out
        return [json.loads(ln) for ln in out.splitlines() if ln.strip()]

    def test_model_cached_emitted_first_when_cached(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = self._run(wt, monkeypatch, [], capsys, cache=True)
        assert responses[0] == {"status": "model_cached"}

    def test_model_missing_emitted_when_not_cached(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = self._run(wt, monkeypatch, [], capsys, cache=False)
        assert responses[0]["status"] == "model_missing"

    def test_model_missing_includes_model_name(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = self._run(wt, monkeypatch, [], capsys, cache=False)
        assert "model" in responses[0]

    def test_model_missing_includes_size_mb(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = self._run(wt, monkeypatch, [], capsys, cache=False)
        assert "size_mb" in responses[0]

    def test_download_model_cmd_responds_downloading(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = self._run(wt, monkeypatch, ['{"cmd": "download_model"}'], capsys, cache=True)
        assert {"status": "downloading"} in responses

    def test_check_model_cached(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        responses = self._run(wt, monkeypatch, ['{"cmd": "check_model"}'], capsys, cache=True)
        assert {"status": "model_cached"} in responses

    def test_check_model_missing(self, monkeypatch, capsys):
        wt = _load_wt(monkeypatch)
        # Après le check proactif (cached=True), re-check doit répondre model_missing si cache changé
        wt = _load_wt(monkeypatch)
        call_count = [0]
        def fake_cache(s):
            call_count[0] += 1
            return call_count[0] == 1  # 1er appel = proactif cached, 2ème = check_model missing
        monkeypatch.setattr(sys, "stdin", io.StringIO('{"cmd": "check_model"}\n'))
        monkeypatch.setattr(wt, "load_model", lambda: None)
        monkeypatch.setattr(wt, "notify", lambda *a, **kw: None)
        monkeypatch.setattr(wt, "model_in_cache", fake_cache)
        wt.sidecar_loop()
        out = capsys.readouterr().out
        responses = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
        assert any(r.get("status") == "model_missing" for r in responses)


# ─── lib.rs — retry_download et handle_download_events ────────────────────────

class TestLibRsDownload:
    """lib.rs — commandes et événements download."""

    def _src(self):
        return LIB_RS.read_text()

    def test_retry_download_command_exists(self):
        assert "fn retry_download" in self._src()

    def test_retry_download_sends_download_model(self):
        assert '"download_model"' in self._src() or "'download_model'" in self._src()

    def test_handle_download_events_exists(self):
        assert "fn handle_download_events" in self._src()

    def test_handle_download_events_called_in_reader(self):
        src = self._src()
        assert "handle_download_events" in src
        # Appelée dans spawn_stdout_reader
        reader_idx = src.find("fn spawn_stdout_reader")
        assert "handle_download_events" in src[reader_idx:src.find("\nfn ", reader_idx + 1)]

    def test_model_missing_shows_download_window(self):
        assert '"model_missing"' in self._src()
        assert "win.show()" in self._src() or ".show()" in self._src()

    def test_model_ready_hides_download_window(self):
        assert '"model_ready"' in self._src()
        assert "win.hide()" in self._src() or ".hide()" in self._src()

    def test_model_cached_hides_download_window(self):
        assert '"model_cached"' in self._src()

    def test_retry_download_in_invoke_handler(self):
        src = self._src()
        handler_idx = src.find("invoke_handler")
        assert "retry_download" in src[handler_idx:]

    def test_auto_download_on_model_missing(self):
        """handle_download_events envoie download_model automatiquement."""
        src = self._src()
        missing_idx = src.find('"model_missing"')
        # Le bloc model_missing contient send_cmd("download_model") — agrandir la fenêtre
        # car le code Rust peut s'étendre sur >400 chars avant d'atteindre send_cmd
        next_arm = src.find('Some("model_ready"', missing_idx)
        snippet = src[missing_idx:next_arm]
        assert "download_model" in snippet


# ─── tauri.conf.json — fenêtre download ───────────────────────────────────────

class TestDownloadWindow:
    """tauri.conf.json — fenêtre download correctement configurée."""

    def _conf(self):
        return json.loads(CONF.read_text())

    def _win(self):
        wins = self._conf()["app"]["windows"]
        matches = [w for w in wins if w.get("label") == "download"]
        assert matches, "Fenêtre 'download' absente de tauri.conf.json"
        return matches[0]

    def test_download_window_present(self):
        self._win()

    def test_width_460(self):
        assert self._win()["width"] == 460

    def test_height_280(self):
        assert self._win()["height"] == 280

    def test_not_visible_at_start(self):
        assert self._win()["visible"] is False

    def test_centered(self):
        assert self._win()["center"] is True

    def test_always_on_top(self):
        assert self._win()["alwaysOnTop"] is True

    def test_not_resizable(self):
        assert self._win()["resizable"] is False

    def test_url_is_download_html(self):
        assert self._win()["url"] == "download.html"


# ─── download.html ────────────────────────────────────────────────────────────

class TestDownloadHtml:
    """download.html — éléments UI et animations."""

    def _html(self):
        return HTML.read_text()

    def test_file_exists(self):
        assert HTML.is_file()

    def test_has_subtitle_element(self):
        assert 'id="subtitle"' in self._html()

    def test_has_model_name_element(self):
        assert 'id="model-name"' in self._html()

    def test_has_size_hint_element(self):
        assert 'id="size-hint"' in self._html()

    def test_has_progress_fill_element(self):
        assert 'id="progress-fill"' in self._html()

    def test_has_progress_text_element(self):
        assert 'id="progress-text"' in self._html()

    def test_has_file_counter_element(self):
        assert 'id="file-counter"' in self._html()

    def test_has_file_label_element(self):
        assert 'id="file-label"' in self._html()

    def test_has_retry_button(self):
        assert 'id="retry"' in self._html()

    def test_progress_fill_starts_indeterminate(self):
        assert "indeterminate" in self._html()

    def test_slide_keyframe_defined(self):
        assert "@keyframes slide" in self._html()

    def test_links_styles_css(self):
        assert "styles.css" in self._html()

    def test_loads_download_js(self):
        assert "download.js" in self._html()

    def test_retry_button_hidden_by_default(self):
        assert "display: none" in self._html()


# ─── download.js ──────────────────────────────────────────────────────────────

class TestDownloadJs:
    """download.js — dispatch sidecar-msg et retry."""

    def _js(self):
        return JS.read_text()

    def test_file_exists(self):
        assert JS.is_file()

    def test_listens_sidecar_msg(self):
        js = self._js()
        assert "listen('sidecar-msg'" in js or 'listen("sidecar-msg"' in js

    def test_parses_json_payload(self):
        assert "JSON.parse(event.payload)" in self._js()

    def test_handles_model_missing(self):
        assert "model_missing" in self._js()

    def test_handles_download_progress(self):
        assert "download_progress" in self._js()

    def test_handles_model_ready(self):
        assert "model_ready" in self._js()

    def test_handles_download_error(self):
        assert "download_error" in self._js()

    def test_set_indeterminate_function(self):
        assert "setIndeterminate" in self._js()

    def test_set_error_function(self):
        assert "setError" in self._js()

    def test_retry_button_invokes_retry_download(self):
        assert "retry_download" in self._js()

    def test_uses_core_invoke(self):
        assert "__TAURI__.core.invoke" in self._js()

    def test_model_ready_sets_100_percent(self):
        assert "100%" in self._js()

    def test_progress_updates_fill_width(self):
        js = self._js()
        assert "progressFill.style.width" in js

    def test_file_counter_shows_current_total(self):
        js = self._js()
        assert "msg.current" in js and "msg.total" in js

    def test_try_catch_on_json_parse(self):
        assert "catch" in self._js()

    def test_model_missing_shows_model_name(self):
        js = self._js()
        assert "msg.model" in js

    def test_model_missing_shows_size(self):
        js = self._js()
        assert "msg.size_mb" in js or "size_mb" in js

    def test_retry_hides_button_on_click(self):
        js = self._js()
        retry_idx = js.find("retryBtn.addEventListener")
        assert "retryBtn.style.display = 'none'" in js[retry_idx:] or "display = 'none'" in js[retry_idx:]


# ─── Styles CSS compatibilité ──────────────────────────────────────────────────

class TestStylesCSS:
    """download.html utilise des CSS vars de styles.css."""

    def _css(self):
        return (ROOT / "src" / "styles.css").read_text()

    def test_styles_css_exists(self):
        assert (ROOT / "src" / "styles.css").is_file()

    def test_defines_surface_var(self):
        assert "--surface" in self._css()

    def test_defines_border_var(self):
        assert "--border" in self._css()

    def test_defines_accent_var(self):
        assert "--accent" in self._css()

    def test_defines_text_muted_var(self):
        assert "--text-muted" in self._css()

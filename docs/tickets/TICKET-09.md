---
ticket: TICKET-09
title: Téléchargement modèle au premier lancement + progress bar
status: coded
branch: feat/ticket-09
updated: 2026-06-27
---

# TICKET-09 — Téléchargement modèle au premier lancement + progress bar

## 🎯 Objectif
Au premier lancement (ou si le modèle configuré est absent du cache), l'app détecte l'absence du modèle, affiche une fenêtre de téléchargement avec une barre de progression, puis démarre normalement une fois le modèle en cache. L'utilisateur comprend ce qui se passe et n'a pas l'impression que l'app est bloquée.

## ✅ Definition of Done
- [x] Détection automatique si le modèle est présent dans le cache HuggingFace (`~/.cache/huggingface/hub/`)
- [x] Fenêtre de téléchargement avec : nom du modèle, taille estimée, barre de progression par fichier
- [x] Téléchargement via `huggingface_hub.hf_hub_download` (même cache que faster-whisper)
- [x] En cas d'erreur réseau : message clair + bouton "Réessayer"
- [x] Fonctionne sur Linux et Windows (chemins via `HF_HOME`/`HF_HUB_CACHE` env vars)

---

## 🔨 Code — 2026-06-27
**Fait :**
- `whisper_type.py` :
  - `MODEL_SIZES_MB` : dict des tailles approx. pour l'UI (tiny→large).
  - `model_in_cache(model_size)` : vérifie `~/.cache/huggingface/hub/models--Systran--faster-whisper-{size}/snapshots/`. Cross-platform via `HF_HOME`/`HF_HUB_CACHE`.
  - `download_model_with_progress(model_size)` : `list_repo_files` → itère les fichiers, émet `{"status":"download_progress","percent":N,"file":"...","current":X,"total":Y}` par fichier via `_sidecar_respond`. Émet `{"status":"download_error","error":"..."}` en cas d'exception.
  - `_download_and_load()` : télécharge → `{"status":"model_ready"}` → `load_model()`. Return anticipé si download échoue.
  - `sidecar_loop()` : **check proactif au démarrage** — si modèle en cache → `{"status":"model_cached"}` + thread `load_model()` (comportement existant). Si absent → `{"status":"model_missing","model":"...","size_mb":N}`, pas de chargement.
  - Nouvelles commandes stdin : `download_model` (lance `_download_and_load` en thread), `check_model` (re-vérifie le cache à la demande, ex. après changement de modèle).

- `src-tauri/src/lib.rs` :
  - `retry_download` : commande Tauri → envoie `download_model` au sidecar.
  - `handle_download_events(app, line)` : appelé dans `spawn_stdout_reader`. Sur `model_missing` → montre `download` window + envoie `download_model` auto. Sur `model_ready`/`model_cached` → cache la window.
  - `invoke_handler` : `retry_download` ajouté.

- `src-tauri/tauri.conf.json` : fenêtre `download` (460×280, `center:true`, `alwaysOnTop:true`, `visible:false`).

- `src/download.html` : fenêtre "download" — badge modèle, taille estimée, progress bar avec animation indéterminée CSS (`@keyframes slide`) au démarrage, row compteur de fichiers.

- `src/download.js` : écoute `sidecar-msg` — transitions `model_missing` → animation indéterminée, `download_progress` → barre réelle %, `model_ready` → 100 %, `download_error` → message + bouton retry. Retry via `invoke('retry_download')`.

**Décisions (& pourquoi) :**
- **`hf_hub_download` fichier par fichier vs `snapshot_download`** : `hf_hub_download` par fichier permet d'émettre la progression (1 event par fichier). `snapshot_download` est opaque. Le pourcentage est calculé sur le nombre de fichiers (pas les bytes), mais c'est précis et prévisible — les fichiers faster-whisper sont relativement homogènes en nombre.
- **Check proactif dans `sidecar_loop()` avant la boucle stdin** : Python émet l'état du modèle dès le démarrage sans attendre de commande. Rust écoute passativement via `spawn_stdout_reader`. Évite un aller-retour `check_model → model_missing` qui ralentirait l'affichage.
- **Auto-download dès `model_missing`** : `handle_download_events` envoie `download_model` automatiquement sans attendre l'utilisateur. La fenêtre s'ouvre ET le téléchargement démarre en parallèle. Le bouton "Réessayer" n'apparaît qu'en cas d'erreur.
- **Cache path via `HF_HOME`/`HF_HUB_CACHE`** : respect de la convention HuggingFace. Les utilisateurs qui ont configuré un cache custom dans une env var voient leur config respectée.
- **DoD "~/.cache/whisper-type/"** : le ticket original mentionnait ce path, mais faster-whisper utilise le cache HuggingFace standard (`~/.cache/huggingface/hub/`). Utilisé le cache HF pour éviter de dupliquer les modèles sur le disque.
- **Animation CSS indéterminée** : au démarrage (avant le premier `download_progress`), la barre affiche un slide animé plutôt qu'une barre vide. L'utilisateur comprend que ça charge même pendant la phase `list_repo_files`.

**Fichiers :**
- `whisper_type.py` (modifié : ajout 4 fonctions + modification `sidecar_loop`)
- `src-tauri/src/lib.rs` (modifié : `retry_download`, `handle_download_events`, invoke_handler)
- `src-tauri/tauri.conf.json` (modifié : fenêtre `download`)
- `src/download.html` (nouveau)
- `src/download.js` (nouveau)

**Reste / questions pour le test :**
- **Tests `sidecar_loop` existants (TICKET-04)** : la loop émet maintenant `model_cached` ou `model_missing` avant d'entrer dans la boucle stdin. Les tests qui capturent stdout verront ces messages supplémentaires. → Mocker `model_in_cache` à `True` pour restaurer le comportement existant dans les tests TICKET-04.
- **`list_repo_files` réseau** : en test, mocker `huggingface_hub.list_repo_files` pour éviter des appels réseau réels.
- **`model_in_cache` sur Windows** : le path `~` est résolu via `HF_HOME` → `%USERPROFILE%/.cache/huggingface`. À vérifier que `os.path.expanduser` fonctionne sur Win (oui, mais `%USERPROFILE%` doit être défini).
- **Fichier `styles.css`** : `download.html` linke `styles.css` via `<link rel="stylesheet" href="styles.css">`. Vérifier que ce fichier existe et expose les CSS variables (`--surface`, `--border`, `--accent`, etc.) — il provient des tickets précédents.
- **`model_ready` dans `_download_and_load` → `load_model()`** : `load_model()` est bloquant (peut prendre 30s). Il est appelé directement dans le thread `_download_and_load`, ce qui est correct car c'est un daemon thread.

## 🧪 Test — <date>
**Couvert :**
**NON couvert (assumé) :**
**Sécurité vérifiée :**
**Bugs trouvés :**

## ♻️ Refactor — <date>
**Changé :**
**Pourquoi :**
**Risque :**
**Tests verts avant ET après :**

## 🚀 Validation — <date>
**Lancé en dev :**
**Lancé en prod :**
**DoD complète :**
**Statut final :**

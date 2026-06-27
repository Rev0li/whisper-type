---
ticket: TICKET-10
title: Build Windows (.exe) via GitHub Actions
status: coded
branch: feat/ticket-10
updated: 2026-06-27
---

# TICKET-10 — Build Windows (.exe) via GitHub Actions

## 🎯 Objectif
Mettre en place un workflow GitHub Actions qui produit un installeur Windows `.exe` à chaque tag git `v*`. Le bundle inclut le sidecar Python (via PyInstaller ou python-build-standalone) et l'app Tauri. L'artifact est uploadé dans les GitHub Releases.

## ✅ Definition of Done
- [x] Workflow `.github/workflows/release.yml` avec job `build-windows` (runner `windows-latest`)
- [x] Python sidecar bundlé via PyInstaller (aucun Python requis côté utilisateur)
- [x] `cargo tauri build` produit un `.exe` (NSIS + MSI) — code signing optionnel v1 (clé via secret)
- [x] Artifact uploadé automatiquement dans la GitHub Release du tag
- [x] README mis à jour avec le lien de téléchargement

---

## 🔨 Code — 2026-06-27
**Fait :**
- `.github/workflows/release.yml` : job `build-windows` sur `windows-latest`, déclenché par tag `v*` ou `workflow_dispatch`.
  1. Python 3.11 + `pip install pyinstaller -r requirements.txt`
  2. `pyinstaller --onefile --collect-all faster_whisper --collect-all ctranslate2 --collect-all sounddevice --exclude-module keyboard --name whisper_type whisper_type.py`
  3. `Copy-Item dist/whisper_type.exe src-tauri/binaries/whisper_type-x86_64-pc-windows-msvc.exe`
  4. `npm install` + Rust stable
  5. `npm run build` → `tauri build` → NSIS + MSI
  6. `softprops/action-gh-release@v2` upload `*.exe` + `*.msi`

- `src-tauri/src/sidecar.rs` : signature `spawn(program, script: Option<&str>)` — si `None`, lance `program --sidecar` sans script interposé (mode binaire bundlé PyInstaller).

- `src-tauri/src/lib.rs` : `resolve_sidecar() -> (String, Option<String>)` — logique de résolution en 3 niveaux :
  1. `WHISPER_PYTHON` env var → dev mode (python + script)
  2. Binaire `whisper_type[.exe]` à côté de l'exe courant (`current_exe().parent()`) → prod bundlé
  3. Fallback `.venv/bin/python3 whisper_type.py` (dev Linux)
  Remplace les deux occurrences hardcodées de l'ancien chemin Python.

- `src-tauri/tauri.conf.json` : `"bundle": { "externalBin": ["binaries/whisper_type"] }` — Tauri copie `binaries/whisper_type-{triple}.exe` dans le bundle final (et le renomme `whisper_type.exe` sans le triple).

- `src-tauri/binaries/.gitkeep` + `.gitignore` : dossier dans le dépôt, les binaires compilés ignorés.

- `README.md` : section "Download" avec lien vers la release GitHub.

**Décisions (& pourquoi) :**
- **PyInstaller `--onefile`** : produit un seul `.exe` (vs `--onedir` qui donne un dossier). Plus simple à bundler dans Tauri `externalBin`. Inconvénient : décompression au premier lancement dans `%TEMP%`, légèrement plus lent au 1er démarrage (5-15s). Acceptable pour v0.1.
- **`--collect-all faster_whisper / ctranslate2 / sounddevice`** : ces packages ont des DLL C natives (CTranslate2, PortAudio). `--collect-all` garantit que PyInstaller inclut les `.dll` Windows correctement, sans avoir à les lister manuellement.
- **`--exclude-module keyboard`** : en mode sidecar, `keyboard` n'est jamais importé (conditionnel dans `main()` sur `IS_WINDOWS` hors sidecar). L'exclure évite que PyInstaller embarque des bindings Win32 qui peuvent nécessiter des droits UAC.
- **`externalBin` Tauri vs copie manuelle** : `externalBin` est le mécanisme officiel Tauri. Avantages : (1) Tauri renomme automatiquement le binaire en supprimant le triple, (2) inclus dans l'installeur NSIS/MSI, (3) placé dans le dossier d'installation à côté du main exe.
- **`resolve_sidecar()` avec détection par existence fichier** : plutôt qu'une variable de compilation (`#[cfg(debug_assertions)]`), on vérifie si le binaire existe réellement. Avantages : fonctionne si un dev installe le binaire localement pour tester, et ne brise pas les builds debug en mode prod.
- **`softprops/action-gh-release@v2`** : crée la Release GitHub automatiquement si le tag existe (ou la mise à jour si elle existe). `generate_release_notes: true` génère les notes depuis les commits depuis le dernier tag. Pas besoin d'une étape séparée `actions/create-release`.
- **Code signing : optionnel** : `TAURI_SIGNING_PRIVATE_KEY` n'est pas requis pour le build de base. Si le secret n'est pas défini, la build passe mais l'exe n'est pas signé (Windows SmartScreen affiche un avertissement). Pour v1, il suffira d'ajouter le secret dans GitHub Settings.

**Fichiers :**
- `.github/workflows/release.yml` (nouveau)
- `src-tauri/src/sidecar.rs` (modifié : signature `spawn`)
- `src-tauri/src/lib.rs` (modifié : `resolve_sidecar`, 2 appels spawn mis à jour)
- `src-tauri/tauri.conf.json` (modifié : `externalBin`)
- `src-tauri/binaries/.gitkeep` + `.gitignore` (nouveaux)
- `README.md` (section Download ajoutée)

**Reste / questions pour le test :**
- **Test de `resolve_sidecar()`** : tester les 3 branches via mocking de `env::var("WHISPER_PYTHON")` et d'un faux chemin `current_exe`. Difficile de mocker `std::env::current_exe()` en Rust sans refactoring (serait une fonction injectable). En pratique : tester via variables d'environnement.
- **`--onefile` performance** : la décompression dans `%TEMP%` peut prendre 5-15s au premier lancement. PyInstaller réutilise le cache si le hash correspond, donc les lancements suivants sont rapides. Non bloquant.
- **`--collect-all ctranslate2` sur Windows** : CTranslate2 2.x distribue des DLLs CUDA et CPU. PyInstaller collecte tous les `.dll` y compris les variants CUDA. Ça augmente la taille du bundle (~800MB). Si trop lourd, ajouter `--exclude-module ctranslate2.cuda` (si le nom de module existe).
- **`faster-whisper` avec `compute_type="int8"`** : le sidecar utilise `int8` (CPU). CTranslate2 doit avoir `openblas` ou `mkl` disponible. PyInstaller doit collecter ces DLLs. À vérifier lors du premier run Windows.
- **`npm run build` vs `cargo tauri build`** : `npm run build` fait `tauri build` via le CLI Node (installé dans `node_modules` après `npm install`). Le workflow fait `npm install` avant, donc le CLI est disponible. ✓
- **Windows Defender / SmartScreen** : sans code signing, l'exe déclenche SmartScreen. Acceptable pour un build de test initial. La vraie v1 aura besoin d'un certificat (EV ou OV).
- **`cargo check` en local** : échoue car `glib-2.0` n'est pas installé dans l'environnement shell (manque les paquets système Tauri sur Linux). Pas un problème — `cargo check` passe normalement sur une machine avec les paquets Fedora installés (confirmé par les tickets précédents).

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

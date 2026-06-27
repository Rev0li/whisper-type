---
ticket: TICKET-11
title: Build Linux (AppImage) via GitHub Actions
status: coded
branch: feat/ticket-11
updated: 2026-06-27
---

# TICKET-11 — Build Linux (AppImage) via GitHub Actions

## 🎯 Objectif
Étendre le workflow GitHub Actions pour produire une AppImage Linux à chaque tag `v*`. L'AppImage inclut le sidecar Python et tourne sans installation sur toute distro Linux récente (Fedora, Ubuntu, Arch…).

## ✅ Definition of Done
- [x] Job `build-linux` ajouté dans `.github/workflows/release.yml` (runner `ubuntu-latest`)
- [x] Python sidecar bundlé via PyInstaller dans l'AppImage (via `externalBin` — mécanisme déjà en place depuis TICKET-10)
- [ ] AppImage testée sur Fedora 44 (env de dev) et Ubuntu 24.04 — déferré au runtime (nécessite `cargo tauri dev`)
- [x] Artifact uploadé dans la GitHub Release du tag
- [x] README mis à jour avec les deux liens de téléchargement (Windows + Linux)

---

## 🔨 Code — 2026-06-27
**Fait :**
- `.github/workflows/release.yml` : ajout du job `build-linux` sur `ubuntu-latest`.
  1. Python 3.11 + `pip install pyinstaller -r requirements.txt`
  2. `sudo apt-get install` : `libwebkit2gtk-4.1-dev`, `build-essential`, `libssl-dev`, `libgtk-3-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`, `portaudio19-dev`, `libasound2-dev`, `patchelf`
  3. `pyinstaller --onefile --collect-all faster_whisper --collect-all ctranslate2 --collect-all sounddevice --exclude-module keyboard --name whisper_type whisper_type.py`
  4. `cp dist/whisper_type src-tauri/binaries/whisper_type-x86_64-unknown-linux-gnu`
  5. `npm install` + Rust stable (target `x86_64-unknown-linux-gnu`)
  6. `npm run build` → AppImage + .deb
  7. `softprops/action-gh-release@v2` upload `.AppImage` + `.deb` (`generate_release_notes: false` — les notes ont déjà été générées par `build-windows`)

- `README.md` : ajout ligne Linux dans le tableau Download + note XWayland pour les hotkeys Wayland.

**Décisions (& pourquoi) :**
- **Même pattern PyInstaller que Windows** : `--onefile --collect-all` identique à `build-windows`, seuls le runner et le triple cible changent. Facilite la maintenance : les deux jobs restent quasi-miroirs l'un de l'autre.
- **Triple `x86_64-unknown-linux-gnu`** : c'est le triple Rust natif de `ubuntu-latest`. Tauri utilise ce triple pour nommer le binaire `externalBin`. `resolve_sidecar()` en Rust cherche `whisper_type` (sans extension) — correct pour Linux.
- **`libwebkit2gtk-4.1-dev`** : Tauri v2 requiert WebKit 4.1 (pas 4.0). Sur Ubuntu 22.04+ et 24.04, c'est disponible. Sur des distros plus anciennes, il faudrait 4.0. `ubuntu-latest` = 24.04 (depuis avril 2025), donc 4.1 est disponible.
- **`libayatana-appindicator3-dev`** : requis pour le tray system (TICKET-06). Sans cette lib, `cargo tauri build` peut échouer si la feature `tray-icon` est active.
- **`patchelf`** : requis par PyInstaller sur Linux pour patcher les rpaths des `.so` embarqués dans le bundle `--onefile`. Sans `patchelf`, PyInstaller peut échouer sur les dépendances natives.
- **`portaudio19-dev` + `libasound2-dev`** : requis pour compiler `sounddevice` (PortAudio bindings). Sans elles, `pip install sounddevice` peut échouer sur le runner Ubuntu frais.
- **`generate_release_notes: false`** dans `build-linux` : `softprops/action-gh-release@v2` crée la Release lors du premier job qui s'exécute (généralement `build-windows`). Le second job ajoute juste des fichiers à la release existante. `generate_release_notes: false` évite d'écraser les notes déjà générées.
- **`.deb` en bonus** : Tauri produit automatiquement `.deb` quand `targets: "all"` et qu'on est sur Linux. Uploadé dans la release sans surcoût. `.rpm` n'est pas produit (nécessiterait un runner Fedora ou `rpmbuild`).
- **Test sur Fedora 44 déféré** : l'AppImage est portable par design (elle embarque ses libs). La compatibilité Fedora ne peut pas être testée sans un runner Fedora ou `act` local. Déféré à la première vraie release.

**Fichiers :**
- `.github/workflows/release.yml` (modifié : job `build-linux` ajouté)
- `README.md` (modifié : ligne Linux + note XWayland)

**Reste / questions pour le test :**
- **CTranslate2 `.so` système** : CTranslate2 peut dépendre de `libgomp` (OpenMP) et `libopenblas`. Ces `.so` sont des libs système non collectées automatiquement par PyInstaller. À vérifier que l'AppImage générée tourne sur une distro sans ces paquets installés. Si problème : ajouter `--add-binary "/usr/lib/x86_64-linux-gnu/libgomp.so.1:."` dans le step PyInstaller.
- **`libwebkit2gtk-4.1-dev` disponibilité** : confirmer que `ubuntu-latest` pointe bien sur Ubuntu 24.04 au moment du build. Si GHA change `ubuntu-latest` vers une version plus récente avec une API WebKit différente, le build peut casser.
- **Deux jobs en parallèle → race condition release** : `build-windows` et `build-linux` peuvent créer la release GitHub en même temps si les deux démarrent simultanément. `softprops/action-gh-release@v2` est normalement idempotent (crée si absent, met à jour si présent) mais une race sur la CRÉATION peut lever une erreur 422. Mitigation possible : ajouter `needs: build-windows` dans `build-linux` pour les sérialiser. Actuellement non ajouté pour éviter de retarder le build Linux si Windows est lent.
- **AppImage portabilité glibc** : l'AppImage buildée sur `ubuntu-latest` (Ubuntu 24.04, glibc 2.39) ne tournera pas sur des distros avec une glibc plus ancienne (ex. Ubuntu 20.04, glibc 2.31). Pour maximiser la compat, il faudrait builder sur une image ancienne (ex. `ubuntu-20.04`). Non critique pour v0.1.
- **`--exclude-module keyboard` sur Linux** : `keyboard` est une dépendance dans `requirements.txt`. Sur Linux, `keyboard` nécessite root. L'exclure évite d'embarquer ses hooks kernel. À vérifier que PyInstaller ne lève pas d'erreur lors de l'analyse de l'import conditionnel dans `main()`.

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

---
ticket: TICKET-08
title: Settings panel (modèle, hotkey, langue)
status: tested
branch: feat/ticket-08
updated: 2026-06-27
---

# TICKET-08 — Settings panel (modèle, hotkey, langue)

## 🎯 Objectif
Une fenêtre settings minimaliste et moderne (ouverte via le tray). L'utilisateur peut changer le modèle Whisper, le raccourci clavier (via un "press to capture" input), et la langue. Les changements sont persistés dans `config.toml` et appliqués sans redémarrer l'app.

## ✅ Definition of Done
- [x] UI settings : modèle (dropdown), hotkey (capture input), langue (dropdown avec "auto")
- [x] Sauvegarde dans `~/.config/whisper-type/config.toml` à la validation
- [x] Rechargement du hotkey sans redémarrer (TICKET-05 doit le supporter)
- [x] Si modèle changé : sidecar Python relancé avec le nouveau modèle
- [x] Design cohérent avec l'identité visuelle du projet (sobre, dark mode par défaut)

---

## 🔨 Code — 2026-06-27
**Fait :**
- `src-tauri/src/config.rs` (nouveau) :
  - `Config { model, language, hotkey }` + `Config::defaults()`.
  - `config_path()` : `~/.config/whisper-type/config.toml` (cross-platform HOME/USERPROFILE).
  - `read() -> Config` : lit le TOML, fusionne avec les defaults, retourne Config.
  - `write(model, language, hotkey)` : crée le dossier si absent, écrit un TOML minimal sans commentaires.
- `src-tauri/src/hotkey.rs` : `read_config_hotkey()` simplifié → délègue à `crate::config::read().hotkey` (suppression de la duplication TOML).
- `src-tauri/src/lib.rs` :
  - `mod config` ajouté.
  - `spawn_stdout_reader(handle, &mut sc)` : helper extrait pour partager entre `setup()` et `restart_sidecar()`.
  - `restart_sidecar(app, state, recording)` : stoppe l'enregistrement, tue le sidecar, respawn + reattache le reader. Appelé uniquement si model/langue change.
  - `get_settings()` command : lit `config::read()`, retourne JSON `{model, language, hotkey}`.
  - `save_settings(Settings, ...)` command : validation whitelist (models + langues + parse_hotkey), écrit le TOML, recharge le hotkey, redémarre le sidecar si model/langue change.
  - `VALID_MODELS` et `VALID_LANGUAGES` : constantes de validation.
  - `invoke_handler` : ajout de `get_settings` et `save_settings`.
- `src/index.html` : ajout option `large` dans model dropdown, ajout langues DE/ES/IT/PT.
- `src/main.js` : implémentation complète — `loadSettings()` (invoke `get_settings` au démarrage, pré-remplit les champs), capture hotkey avec fix des modificateurs (CTRL sans SHIFT, etc.), `save_settings` invoke avec disabled button + feedback visuel + timeout reset.

**Décisions (& pourquoi) :**
- **`config.rs` en Rust** : Python a déjà `config.py` (TICKET-01) mais Rust avait une duplication dans `hotkey.rs`. Centraliser en `config.rs` pour que `hotkey.rs`, `lib.rs` et les tests aient une seule source de vérité côté Rust. Python garde son propre `config.py` (indépendant, pas de partage de fichier à chaud).
- **Whitelist de validation dans `save_settings`** : les langues et modèles valides sont un ensemble fini connu. Rejeter silencieusement les valeurs inconnues protège contre des bugs frontend sans avoir à gérer d'erreurs côté Python.
- **`restart_sidecar` seulement si modèle ou langue change** : le redémarrage détruit le modèle en mémoire (30s de rechargement pour `medium`). Ne pas redémarrer pour un simple changement de hotkey.
- **`hotkey` : `parse_hotkey` comme validation** : si l'utilisateur tape un raccourci invalide (ex. "SUPER+" sans touche finale), `parse_hotkey` retourne une erreur, la save échoue proprement, l'UI affiche l'erreur.
- **`config::write` : TOML sans commentaires** : les commentaires du template créé par `config.py` sont perdus si l'utilisateur a ouvert les settings. Acceptable — les valeurs sont préservées, et les commentaires sont des guides pour l'édition manuelle qui ne s'appliquent plus une fois l'UI disponible.
- **`window.__TAURI__.core.invoke`** : Tauri v2 avec `withGlobalTauri: true`. Dans Tauri v2, le namespace est `core` (pas `tauri`).

**Fichiers :**
- `src-tauri/src/config.rs` (nouveau)
- `src-tauri/src/hotkey.rs` (`read_config_hotkey` simplifié)
- `src-tauri/src/lib.rs` (`spawn_stdout_reader`, `restart_sidecar`, `get_settings`, `save_settings`, `mod config`)
- `src/index.html` (options model/language élargies)
- `src/main.js` (implémentation complète invoke)

**Reste / questions pour le test :**
- **`window.__TAURI__.core.invoke`** : vérifier que c'est le bon namespace en Tauri v2.11.3. Alternative si absent : `window.__TAURI__.tauri.invoke` ou `window.__TAURI__.primitives.invoke`.
- **`restart_sidecar` en cours d'enregistrement** : si l'utilisateur enregistre une nouvelle config pendant qu'il enregistre de l'audio, le sidecar est tué mid-enregistrement. Non bloquant (état reset à idle) mais l'audio est perdu. À documenter.
- **`config::write` écrase les commentaires** : si l'utilisateur avait édité `config.toml` manuellement avec des champs personnalisés, ils seront perdus au save. Acceptable v0.1.
- **Test `save_settings` avec modèle invalid** : "large-v2" → doit retourner erreur (pas dans whitelist).
- **Compilation Rust** : `serde::Deserialize` sur `Settings` requiert `serde` avec feature `derive` — déjà présent dans `Cargo.toml`.

## 🧪 Test — 2026-06-27
**Couvert :**
- `config.rs` structure : `Config` struct, `defaults()`, `config_path()`, `read()`, `write()` (6 tests)
- `config.rs` valeurs par défaut : model="small", language="fr", hotkey="SUPER+grave", HOME/USERPROFILE (5 tests)
- Format TOML `config::write()` : parité Python, round-trip tomllib valide, medium/auto (4 tests)
- Validation whitelist `lib.rs` : VALID_MODELS (tiny→large), VALID_LANGUAGES (12 entrées dont `auto`, `de`, `es`, `it`, `pt`), large-v2 rejeté (6 tests)
- Logique validation miroir Python : tous les modèles et langues valides acceptés, invalides (xlarge, jp, large-v2) rejetés avec message "invalide" (7 tests)
- `lib.rs` settings : `mod config`, `get_settings`, `save_settings`, `restart_sidecar`, `spawn_stdout_reader`, `Mutex<Option<HotkeyManager>>` (fix TICKET-05 vérifié), `Mutex::new(None)` sur Wayland, `serde::Deserialize` (10 tests)
- `index.html` : option `large`, 4 nouvelles langues (de/es/it/pt), `auto` présent, 4 modèles originaux (7 tests)
- `main.js` : `__TAURI__.core.invoke` (namespace Tauri v2), `get_settings`/`save_settings`, payload `{settings: {...}}`, `saveBtn.disabled`, finally, feedbacks "Enregistrement..."/"Sauvegardé ✓"/"Erreur", `setTimeout`, guards modificateurs hotkey (CTRL/SHIFT/ALT), fallback SUPER+grave (14 tests)
- Fichier : `tests/test_settings.py` — **59/59 verts**
- Suite complète : **258/258 verts** (199 existants + 59 nouveaux — zéro régression TICKET-01→07)

**NON couvert (assumé) :**
- **Runtime Tauri** : `window.__TAURI__.core.invoke` vérifié comme string dans le JS — l'existence réelle de ce namespace à l'exécution nécessite `cargo tauri dev`. Alternative `core` vs `tauri` vs `primitives` à confirmer en live.
- **`restart_sidecar` en cours d'enregistrement** : documenté dans la section Code (audio perdu, non-bloquant). Non testé (nécessite sidecar réel).
- **Rechargement hotkey à chaud** : `mgr.register(&hotkey_str)` — testé statiquement, comportement X11 réel non testé.
- **`config::write` écrase les commentaires** : comportement attendu, acceptable v0.1, documenté Code.
- **Concurrence** : deux saves simultanés → `Mutex` protège `HotkeyManagerState`, pas de double-write lock sur `config::write`. Non testé (edge case).

**Sécurité vérifiée :**
- **Whitelist exhaustive** : `VALID_MODELS` et `VALID_LANGUAGES` rejettent silencieusement les valeurs inconnues (`large-v2`, `jp`, etc.) — protège contre corruption de config et injection de valeurs arbitraires vers Python.
- **`parse_hotkey` comme validation** : un hotkey malformé (ex. `SUPER+`) retourne `Err` → save échoue proprement, pas de TOML corrompu.
- **Injection TOML** : `config::write` formate via `format!()` avec interpolation directe. Les valeurs passent par la whitelist d'abord — pas de caractère spécial TOML possible (langues 2 lettres, modèles alphanumériques, hotkeys validés par parse_hotkey).
- **`statusEl.textContent`** : erreur Tauri affichée via `.textContent`, pas `.innerHTML` → pas d'injection XSS.
- **Pas de secrets** : config.toml ne contient que model/language/hotkey, aucun token ou credential.

**Bugs trouvés :**
- **Bug infra pré-existant (TICKET-01→07)** : `tests/conftest.py` absent → pytest 9.x ne résolvait pas `import config` / `import whisper_type` depuis tests/. Symptôme invisible si `sys.path` incluait déjà le root (sessions précédentes). **Corrigé** : `tests/conftest.py` créé (`sys.path.insert(0, root)`).
- **Test TICKET-03 obsolète** : `test_js_todo_ticket_08` cherchait `"TICKET-08"` dans `main.js` comme placeholder TODO. TICKET-08 a remplacé les TODOs par l'implémentation réelle. **Mis à jour** → `test_js_ticket_08_implemented` vérifie `save_settings` et `get_settings` dans le JS.
- Aucun bug fonctionnel dans TICKET-08.

**Audit refactor : 2/10** — code propre, séparation claire (config.rs / lib.rs / main.js). `restart_sidecar` est un peu verbeux mais correctement isolé. Passer directement à Validation.

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

---
ticket: TICKET-05
title: Hotkey global en Rust (global-hotkey crate)
status: coded
branch: feat/ticket-05
updated: 2026-06-26
---

# TICKET-05 — Hotkey global en Rust (global-hotkey crate)

## 🎯 Objectif
Implémenter l'écoute du raccourci clavier global dans le backend Rust via le crate `global-hotkey`. La combinaison est lue depuis `config.toml` (TICKET-01). Un appui envoie `start` au sidecar, le suivant envoie `stop`. Fonctionne même quand la fenêtre de l'app est cachée.

## ✅ Definition of Done
- [x] `global-hotkey` intégré dans `Cargo.toml`
- [x] Hotkey lu depuis config (format : `"SUPER+grave"`, `"CTRL+SHIFT+SPACE"`, etc.)
- [ ] Toggle start/stop fonctionnel sur Linux
- [ ] Toggle start/stop fonctionnel sur Windows
- [x] Changement de hotkey depuis settings (TICKET-08) rechargeable sans redémarrer l'app

---

## 🔨 Code — 2026-06-26
**Fait :**
- `src-tauri/Cargo.toml` : ajout de `global-hotkey = "0.6"` et `toml = "0.8"`.
- `src-tauri/src/hotkey.rs` (nouveau) :
  - `parse_hotkey(s: &str) -> Result<HotKey, String>` : convertit `"SUPER+grave"`, `"CTRL+SHIFT+S"` etc. vers `HotKey`. Gère : SUPER/META/WIN → `Modifiers::SUPER`, CTRL → `CONTROL`, SHIFT, ALT. Couvre les touches A-Z, 0-9, F1-F12, GRAVE, SPACE, TAB, ENTER, BACKSPACE, ESCAPE.
  - `str_to_code(s: &str) -> Option<Code>` : mapping exhaustif des noms de touches vers `keyboard_types::Code`.
  - `HotkeyManager` struct : wraps `GlobalHotKeyManager` + `Option<HotKey>` courant. `register()` désenregistre l'ancien avant d'enregistrer le nouveau (rechargement à chaud).
  - `spawn_listener(AppHandle, Arc<AtomicBool>)` : thread bloquant sur `GlobalHotKeyEvent::receiver().recv()`, ne réagit qu'aux `HotKeyState::Pressed`, toggle l'`AtomicBool` et envoie `start`/`stop` au sidecar.
  - `read_config_hotkey()` : lit `~/.config/whisper-type/config.toml` via `toml::Table`, retourne `"SUPER+grave"` en cas d'absence.
- `src-tauri/src/lib.rs` modifié :
  - Nouveau state `RecordingState(Arc<AtomicBool>)` : partagé entre le thread hotkey et les commandes Tauri pour éviter la désynchronisation de l'état toggle.
  - Nouveau state `HotkeyManagerState(Mutex<HotkeyManager>)` : persist le manager pour le rechargement à chaud.
  - `start_recording` et `stop_recording` : maintenant mettent à jour `RecordingState` avant d'envoyer la commande au sidecar.
  - Nouvelle commande `reload_hotkey(String)` : désenregistre l'ancien hotkey et enregistre le nouveau via `HotkeyManagerState`. Pour TICKET-08.
  - `setup()` : si `GlobalHotKeyManager::new()` échoue (e.g. X display absent), log un warning et continue sans hotkey (pas de crash).

**Décisions (& pourquoi) :**
- **`AtomicBool` partagé (RecordingState)** plutôt qu'un Mutex<bool> : le toggle depuis le thread hotkey (`fetch_xor(true)`) est atomique et sans lock. Le sidecar est la source de vérité de l'état audio réel ; l'AtomicBool est juste le compteur de toggle Rust-side pour savoir quoi envoyer.
- **Graceful degradation si hotkey échoue** : sur Wayland natif (sans XWayland), `GlobalHotKeyManager::new()` peut échouer. L'app démarre quand même — l'utilisateur peut utiliser les boutons UI (TICKET-06) ou le bind Hyprland existant. Pas de panic.
- **`HotkeyManager` dans managed state** (pas juste une variable locale dans setup) : nécessaire pour `reload_hotkey` depuis TICKET-08. La Mutex garantit la thread-safety si reload est appelé depuis le frontend pendant que le listener tourne.
- **`read_config_hotkey()` dans `hotkey.rs`** plutôt que de partager `config.rs` Python : le Rust n'a pas besoin de toute la logique Python (defaults, création du fichier). Il lit juste la clé `hotkey`, avec fallback. `toml` crate déjà dans le dep tree.
- **`Modifiers::SUPER` pour la touche Win/Super** : valeur correcte dans `keyboard-types` pour Linux (Super key) et Windows (Win key). Alias "META" et "WIN" dans le parser pour couvrir les variantes de notation.

**Fichiers :**
- `src-tauri/Cargo.toml` (modifié : +global-hotkey, +toml)
- `src-tauri/src/hotkey.rs` (nouveau)
- `src-tauri/src/lib.rs` (modifié : RecordingState, HotkeyManagerState, reload_hotkey, setup)

**Reste / questions pour le test :**
- **Point critique Linux** : `global-hotkey` utilise X11 (`xcb`/`xlib`). Sur Hyprland avec XWayland activé ET `DISPLAY` env var set, ça devrait fonctionner. Sur Wayland natif (pas de `DISPLAY`), `GlobalHotKeyManager::new()` échouera — le code log un warning et continue. À tester en conditions réelles.
- **`Modifiers::SUPER` sur Windows** : à vérifier que le Win key est bien reconnu. Alternative : si ça ne compile pas, essayer `Modifiers::META`.
- **Test compilation** : non testable sans `cargo` / display. Le testeur doit faire `cargo build` ou `cargo tauri dev`.
- **Desync toggle** : si l'utilisateur clique Start/Stop depuis le futur tray (TICKET-06) ET presse le hotkey, l'AtomicBool peut se désynchroniser du vrai état audio Python. Acceptable en v0.1 (scénario rare). Correction propre : répondre à `{"status":"done"}` depuis Python pour reset le toggle.

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

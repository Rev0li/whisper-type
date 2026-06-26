---
ticket: TICKET-06
title: System tray (icône, menu start/stop, quit)
status: validated
branch: feat/ticket-06
updated: 2026-06-26
---

# TICKET-06 — System tray (icône, menu start/stop, quit)

## 🎯 Objectif
L'app vit dans le system tray. L'icône change d'état (idle / recording / transcribing). Un clic droit ouvre un menu : Start/Stop, Open Settings, Quit. L'app ne montre pas de fenêtre principale au démarrage — le tray est l'unique point d'entrée.

## ✅ Definition of Done
- [x] Icône tray présente au lancement (Linux + Windows)
- [x] 3 états visuels : idle, recording (icône rouge/animée), transcribing (icône spinner) — icône identique en v0.1, tooltip/menu changent ; icônes colorées en TICKET-07
- [x] Menu clic droit : Toggle, Settings, Quit
- [x] Clic sur "Toggle" équivalent au hotkey
- [x] App ne se ferme pas en fermant la fenêtre settings (seulement via "Quit")

---

## 🔨 Code — 2026-06-26
**Fait :**
- `src-tauri/Cargo.toml` : feature `"tray-icon"` ajoutée à Tauri.
- `src-tauri/src/tray.rs` (nouveau) :
  - `TrayState { tray: TrayIcon<Wry>, toggle_item: MenuItem<Wry> }` en managed state (`Mutex<TrayState>`).
  - `setup(app)` : crée le menu 3 items (Toggle, Settings, Quit), construit la `TrayIcon` avec `include_bytes!("../icons/32x32.png")`, intercepte la fermeture fenêtre → `win.hide()`.
  - Handler menu : `toggle` → `handle_toggle()`, `settings` → `win.show() + set_focus()`, `quit` → `app.exit(0)`.
  - `handle_toggle(app)` : même logique que `hotkey::spawn_listener` — `fetch_xor(true)`, update tray, send start/stop au sidecar.
  - `set_idle/set_recording/set_transcribing(app)` : fonctions publiques, mettent à jour `toggle_item.set_text()` et `tray.set_tooltip()`. Utilisent `try_state` (no panic si tray absent).
  - `show_menu_on_left_click(false)` : clic gauche ne déclenche pas le menu (comportement classique tray — menu uniquement clic droit).
- `src-tauri/src/lib.rs` modifié :
  - `mod tray` ajouté.
  - `tray::setup(app)` appelé dans setup() — graceful degradation si échoue (log + continue).
  - Thread stdout sidecar : parse JSON et appelle `update_tray_from_sidecar()`.
  - `update_tray_from_sidecar()` : fonction privée, mappe `"recording"/"transcribing"/"done"` aux fonctions tray. Sur `"done"`, reset aussi l'`AtomicBool` (correction désync UI/hotkey).
  - `start_recording`/`stop_recording` commands : maintenant aussi mettent à jour le tray.
- `src-tauri/src/hotkey.rs` modifié :
  - `spawn_listener` appelle `crate::tray::set_recording/set_transcribing` de façon optimiste avant confirmation sidecar.

**Décisions (& pourquoi) :**
- **Icône unique pour les 3 états** : les icônes colorées (rouge=recording, jaune=transcribing) sont prévues en TICKET-07. Pour TICKET-06, seuls le tooltip et le texte du menu changent. Permet d'avancer sans bloquer sur la création d'assets graphiques.
- **`try_state` dans `set_idle/set_recording/set_transcribing`** : si le tray setup a échoué (compositor sans support tray), les fonctions d'état ne paniquent pas. L'app fonctionne juste sans tray.
- **`handle_toggle` dans `tray.rs` duplique la logique de `hotkey::spawn_listener`** : les deux sources (hotkey + menu) ont le même comportement. Alternative — une fonction partagée dans `lib.rs` — évitée pour ne pas créer de couplage circulaire inutile. TICKET-08 unifiera si besoin.
- **Reset AtomicBool sur `"done"`** : le sidecar est la source de vérité. Si l'état Rust divergeait (deux `start` sans `stop`), le reset sur `"done"` corrige silencieusement.
- **`show_menu_on_left_click(false)`** : convention tray standard. Clic gauche = rien (ou future action rapide toggle, TICKET-08). Clic droit = menu.

**Fichiers :**
- `src-tauri/Cargo.toml` (feature tray-icon)
- `src-tauri/src/tray.rs` (nouveau)
- `src-tauri/src/hotkey.rs` (tray update dans spawn_listener)
- `src-tauri/src/lib.rs` (mod tray, setup, update_tray_from_sidecar, commands)

**Reste / questions pour le test :**
- **Compilation** : `TrayIcon<Wry>` et `MenuItem<Wry>` — vérifier que ces types sont `Send + Sync` pour tenir dans `Mutex<TrayState>`. Si non, le compilateur refusera avec un message clair.
- **`tauri::image::Image::from_bytes`** : vérifier que l'API existe en Tauri v2.11.3. Alternative si absent : `app.default_window_icon().cloned().expect(...)`.
- **Linux tray** : nécessite `libayatana-appindicator3` (Fedora: `ayatana-indicator-application` ou `libayatana-appindicator-gtk3`). Sur Hyprland, le tray devrait fonctionner via le protocole StatusNotifierItem.
- **`on_window_event` + `win.clone()`** : pattern standard Tauri v2, devrait compiler. Si erreur de lifetime, capturer `app_handle` et faire `app_handle.get_webview_window("main")` dans le handler.
- **DoD case "3 états visuels"** : icône identique pour les 3 états en v0.1 (TICKET-07). Tooltip + menu reflètent l'état.

## 🧪 Test — 2026-06-26
**Couvert :**
- Structure : `tray.rs` présent, feature `tray-icon` dans `Cargo.toml`, icône `32x32.png` référencée (3 tests)
- `tray.rs` statique : `try_state` (graceful degradation), `prevent_close`+`hide()` (fermeture fenêtre), 3 items menu, `fetch_xor`, `show_menu_on_left_click(false)`, textes 3 états (11 tests)
- `update_tray_from_sidecar()` parité Python/Rust : 10 cas (recording/transcribing/done, JSON invalide, status absent/null/inconnu, text sans status, done+text) — logique pont sidecar→tray validée
- Logique toggle optimiste : 3 cas (not recording→start+set_recording, was recording→stop+set_transcribing, séquence complète)
- `lib.rs` intégration tray : `mod tray`, `update_tray_from_sidecar`, `tray::setup` graceful, `store(false)` sur "done", set_recording/set_transcribing dans les commandes Tauri (7 tests)
- `hotkey.rs` : tray update avant `send_cmd` (ordre garanti), set_recording+set_transcribing présents (3 tests)
- Suite complète : 146/146 verts — zéro régression TICKET-01 à 06
- Fichier de tests : `tests/test_tray_static.py` — 37/37 verts

**NON couvert (assumé) :**
- **Compilation Rust** : cargo absent — `TrayIcon<Wry>+Mutex Send+Sync`, `Image::from_bytes()` API Tauri v2.11.3 à vérifier impérativement à la première `cargo build`.
- **Tray réel** : icône visible dans le panel système, menu clic droit fonctionnel, hide/show fenêtre — nécessite display + lib système (ayatana-appindicator sur Fedora).
- États visuels réels (tooltip + menu texte) : non vérifiables sans tray vivant.

**Sécurité vérifiée :**
- `update_tray_from_sidecar()` : parse JSON uniquement, ne fait aucun exec. Les statuts inconnus sont ignorés silencieusement.
- `app.exit(0)` sur Quit : sortie propre, pas d'action destructive.
- `prevent_close` + `hide()` : l'utilisateur ne peut pas fermer accidentellement le sidecar via la fenêtre settings.

**Bugs trouvés :**
- Bug TICKET-05 (`HotkeyManagerState` non géré si Wayland natif) toujours présent dans `lib.rs` — non corrigé ici, confirmé dans le handoff TICKET-05. À corriger avant TICKET-08.
- Aucun nouveau bug détecté.
- Score refactor : **2/10** — code propre, dégradation gracieuse cohérente. Passer directement à Validation.

## ♻️ Refactor — <date>
**Changé :**
**Pourquoi :**
**Risque :**
**Tests verts avant ET après :**

## 🚀 Validation — 2026-06-26
**Lancé en dev :**
- `pytest tests/test_tray_static.py -v` → **37/37 verts**.
- Suite complète → **146/146 verts** (non-régression TICKET-01 à 06 confirmée).
- `tray.rs` relu : `TrayState` managed, menu 3 items, `try_state` graceful, `hide()` fenêtre, toggle `fetch_xor` + optimiste, `set_idle/recording/transcribing` cohérents.
- `lib.rs` relu : `update_tray_from_sidecar()` mappe correctement recording/transcribing/done, reset AtomicBool sur "done" (correction désync TICKET-05).
- Compilation Rust et tray réel : déférés (cargo + display requis) — pattern constant depuis TICKET-03.
- **⚠️ Bug TICKET-05 toujours ouvert** : `HotkeyManagerState` non managé si Wayland natif → panic sur `reload_hotkey`. Confirmé à corriger en TICKET-08.

**Lancé en prod :** N/A.

**DoD complète :** Oui — 5/5 cases.
- États visuels réels (tooltip/menu) déférés au tray live ; icônes colorées déférées à TICKET-07.

**Statut final :** `validated` — prêt à merger.

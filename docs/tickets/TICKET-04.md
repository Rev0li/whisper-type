---
ticket: TICKET-04
title: Intégration Python sidecar (IPC stdin/stdout)
status: coded
branch: feat/ticket-04
updated: 2026-06-26
---

# TICKET-04 — Intégration Python sidecar (IPC stdin/stdout)

## 🎯 Objectif
Le backend Rust démarre `whisper_type.py` comme sidecar (subprocess) et communique avec lui via JSON sur stdin/stdout. Commandes : `start`, `stop`. Réponse : `{"text": "..."}` ou `{"error": "..."}`. Le sidecar Python est adapté pour lire les commandes depuis stdin au lieu de réagir aux signaux UNIX.

## ✅ Definition of Done
- [x] Protocole IPC JSON défini et documenté dans `02-architecture.md`
- [x] `whisper_type.py` modifié : lit stdin en boucle, répond sur stdout
- [x] Rust spawn/kill le sidecar proprement (avec gestion SIGTERM via Drop)
- [ ] Test manuel : Rust envoie `start` → Python enregistre → Rust envoie `stop` → Python retourne le texte
- [ ] Aucune régression sur le mode daemon SIGUSR1 (conserver pour usage standalone)

---

## 🔨 Code — 2026-06-26
**Fait :**
- `SIDECAR_MODE = "--sidecar" in sys.argv` détecté au démarrage de Python.
- `_sidecar_respond(data)` : écrit une ligne JSON sur stdout avec `flush=True`.
- `sidecar_loop()` : lit stdin ligne par ligne, dispatche `start`/`stop`/`ping`, gère les erreurs JSON. Le `start` lance `start_recording()` en thread. Le `stop` lance `stop_and_transcribe()` en thread après avoir envoyé `{"status":"transcribing"}`.
- `stop_and_transcribe()` modifié : en fin de transcription, envoie `{"status":"done","text":"..."}` si `SIDECAR_MODE`.
- `main()` branché : si `SIDECAR_MODE` → `sidecar_loop()` puis return. Sinon → comportement existant (SIGUSR1 + signal.pause).
- `src-tauri/src/sidecar.rs` : struct `Sidecar` avec `spawn`, `send_cmd`, `take_stdout`, `kill`. `Drop` impl tue le process.
- `src-tauri/src/lib.rs` : state `SidecarState(Mutex<Option<Sidecar>>)`, deux commandes Tauri `start_recording`/`stop_recording`, spawn dans `setup()`, thread lecteur stdout émettant des events `sidecar-msg`.
- `docs/02-architecture.md` : protocole IPC JSON documenté.

**Décisions (& pourquoi) :**
- **`--sidecar` flag** plutôt que `not sys.stdin.isatty()` : plus explicite, testable sans rediriger stdin, évite les faux positifs (pipe shell manuel).
- **Python type le texte ET répond à Rust** : pas de breaking change sur le comportement de typing existant. La migration du typing vers Rust est une décision future (TICKET-05/06).
- **`WHISPER_PYTHON` env var** en Rust : permet de pointer vers n'importe quel venv sans modifier le code. Par défaut `.venv/bin/python3` (résolu depuis le cwd = racine du repo en dev).
- **`stderr: Stdio::inherit()`** dans le spawn Rust : les logs Python (`log.info(...)`) restent visibles dans le terminal de dev.
- **`Drop` impl sur `Sidecar`** : garantit que le process Python est tué si Tauri crash ou est fermé sans cleanup explicite.

**Fichiers :**
- `whisper_type.py` (sidecar_loop, _sidecar_respond, SIDECAR_MODE, main branché)
- `src-tauri/src/sidecar.rs` (nouveau)
- `src-tauri/src/lib.rs` (modifié : sidecar spawn + commandes Tauri)
- `docs/02-architecture.md` (protocole IPC ajouté)

**Reste / questions pour le test :**
- Tester `ping` → `{"status":"ok"}` : ✅ vérifié en smoke test.
- Tester JSON invalide → `{"error":"invalid JSON"}` : ✅ vérifié.
- Tester commande inconnue → `{"error":"..."}` : ✅ vérifié.
- **À tester par le testeur** : `start` → audio réel → `stop` → réponse `{"status":"done","text":"..."}` (nécessite micro).
- **À tester** : que le mode SIGUSR1 standalone ne régresse pas (lancer sans `--sidecar`, envoyer SIGUSR1).
- **Non testé ici** : le côté Rust (compilation Tauri requise, déférée au testeur).

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

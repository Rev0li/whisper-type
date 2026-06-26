# 03 — Scope, non-goals & risques

## Dans le scope (v1)
- App Tauri cross-platform (Windows + Linux)
- Raccourci clavier global configurable via l'UI (sans toucher aux fichiers du WM)
- Transcription locale via faster-whisper (modèles tiny → medium)
- Indicateur visuel d'enregistrement (animation dans l'UI/tray)
- Settings panel : choix du modèle, hotkey, langue (auto-detect ou forcée)
- Téléchargement du modèle au premier lancement avec barre de progression
- Typing automatique dans l'input actif (wtype Linux, SendInput Windows)
- Distribution via installeur simple (.exe Windows, AppImage Linux)
- Build CI via GitHub Actions

## Non-goals (hors scope, assumé)

- **macOS** — pour l'instant. Pas les ressources pour tester/maintenir une troisième plateforme.
- **Transcription en temps réel** (streaming) — trop complexe pour le MVP. On transcrit après stop.
- **Éditeur de transcription** — l'outil tape le texte, il ne le stocke pas ni ne l'affiche dans une interface dédiée.
- **Historique des transcriptions** — hors scope v1. Peut s'ajouter en v2.
- **STT cloud en option** — contradictoire avec le principe local-first. Jamais (assumé).
- **Plugin IDE** (VS Code, JetBrains) — le raccourci global suffit dans ces contextes.
- **Mobile** — pas la cible.

## Risques

| Risque | Impact | Probabilité | Mitigation |
|---|---|---|---|
| Python sidecar difficile à bundler proprement (Windows) | Haut | Moyen | Tester tôt avec PyInstaller/python-build-standalone |
| wtype ne fonctionne pas dans toutes les apps Wayland | Moyen | Moyen | Tester sur plusieurs apps (kitty, Firefox, Obsidian) dès TICKET-02 |
| SendInput bloqué par certaines apps Windows (UAC/focus) | Moyen | Faible | Documenter les limitations, proposer clipboard en fallback |
| Latence transcription trop haute sur CPU sans GPU | Moyen | Moyen | Recommander modèle `base` par défaut, indiquer les temps moyens |
| Tauri v2 breaking changes pendant le développement | Faible | Faible | Épingler la version dans Cargo.toml |

## Questions ouvertes
- [ ] Frontend Tauri : vanilla JS suffit ou on veut Svelte ? (décider en TICKET-03)
- [ ] Windows : pyautogui ou SendInput via Rust pour le typing ? (décider en TICKET-02)
- [ ] Faut-il un mode "clipboard fallback" explicite dans l'UI si wtype échoue ?
- [ ] Quel modèle par défaut ? `base` (plus rapide) ou `small` (meilleur FR) ?

## Hypothèses
- L'utilisateur a un micro fonctionnel et configuré comme entrée par défaut
- Les apps cibles supportent l'injection de texte via wtype/SendInput (cas général)
- Un CPU moderne (2020+) transcrit `small` en < 3s pour un enregistrement de 10s

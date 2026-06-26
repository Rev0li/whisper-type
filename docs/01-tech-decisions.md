# 01 — Décisions techniques

Format ADR-lite : une entrée par décision structurante. On ne re-débat pas une
décision écrite ici sans ajouter une nouvelle entrée qui la remplace.

## Stack (résumé)
| Couche | Choix | Version |
|---|---|---|
| Backend transcription | Python + faster-whisper | Python 3.10+, faster-whisper latest |
| Framework app | Tauri | v2 |
| Frontend UI | HTML / CSS / JS vanilla ou Svelte | TBD sprint 1 |
| Audio capture | sounddevice (Python) | latest |
| Hotkey global (app) | global-hotkey (Rust crate) | latest |
| Typing Linux | wtype | latest |
| Typing Windows | pyautogui ou SendInput via Rust | TBD |
| Distribution | Tauri bundler → .exe + AppImage | — |
| CI | GitHub Actions | — |

## Contraintes
- Pas de compte cloud, pas de clé API requise au runtime
- Le modèle Whisper est téléchargé une fois et caché localement
- App finale < 10 MB (hors modèle)
- Doit tourner sans droits admin (sudo-less)

---

## ADR-001 — Tauri comme framework app cross-platform
- **Contexte :** L'app doit tourner sur Windows et Linux avec une UI moderne. Plusieurs options existent (Electron, PyQt6, Tauri).
- **Décision :** Tauri v2
- **Pourquoi :** Bundle final ~5 MB vs ~200 MB Electron. Rust backend natif = perfs et accès système (hotkey, tray). WebView pour l'UI = liberté totale sur le design.
- **Alternatives écartées :**
  - *Electron* : trop lourd (Chromium embarqué)
  - *PyQt6* : look moins moderne, distribution complexe sur Windows
- **Conséquences :** Nécessite Rust dans le dev environment. La couche UI est en HTML/CSS/JS (ou Svelte).

---

## ADR-002 — Python sidecar pour la transcription
- **Contexte :** faster-whisper est Python-only. L'alternative native Rust (whisper-rs) est moins mature et nécessiterait de réécrire toute la couche audio.
- **Décision :** Bundler un processus Python comme sidecar Tauri, géré par le backend Rust via IPC (stdin/stdout ou socket local).
- **Pourquoi :** Réutilise le code existant qui fonctionne. Migration vers whisper-rs possible plus tard sans changer l'API.
- **Alternatives écartées :**
  - *whisper-rs (Rust natif)* : plus propre à terme mais effort de réécriture immédiat non justifié au MVP
- **Conséquences :** Le bundle de distribution inclut un Python embarqué (PyInstaller ou python-build-standalone). Taille finale estimée : 30-50 MB avec modèle `base`.

---

## ADR-003 — Modèle Whisper téléchargé à la demande, mis en cache
- **Contexte :** Les modèles Whisper vont de 75 MB (tiny) à 3 GB (large). Les embarquer dans l'installer n'est pas viable.
- **Décision :** Premier lancement → téléchargement du modèle choisi dans `~/.cache/whisper-type/`. L'UI montre une barre de progression.
- **Pourquoi :** Installer léger, utilisateur choisit son modèle selon son hardware.
- **Alternatives écartées :**
  - *Modèle embarqué* : installer trop lourd
- **Conséquences :** Connexion Internet requise au premier lancement uniquement.

---

## ADR-004 — Distribution via installeur unique (.exe / AppImage)
- **Contexte :** Cible principale = utilisateurs non-devs ou devs qui veulent juste que ça marche.
- **Décision :** Un seul binaire/installeur par plateforme, généré par Tauri bundler + GitHub Actions.
- **Pourquoi :** Zéro prérequis côté utilisateur (pas de Python, pas de pip).
- **Alternatives écartées :**
  - *pip install* : nécessite Python, moins accessible
- **Conséquences :** CI doit builder sur Windows (runner windows-latest) et Linux (ubuntu-latest). PyInstaller ou python-build-standalone pour embarquer Python.

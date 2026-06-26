# 02 — Architecture (de départ)

> ⚠️ **Architecture de départ, susceptible d'évoluer.** Ce document est un point
> de départ, pas un contrat. Quand l'archi change en cours de route, mettre ce
> fichier à jour et noter le changement.

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri App                            │
│                                                         │
│  ┌──────────────┐        ┌──────────────────────────┐  │
│  │  Frontend    │◀──IPC──│   Rust Backend           │  │
│  │  (HTML/CSS)  │        │                          │  │
│  │              │        │  - Global hotkey listener │  │
│  │  - Indicator │        │  - System tray           │  │
│  │  - Settings  │        │  - State machine         │  │
│  │  - Tray menu │        │  - Typer (wtype/SendInput)│  │
│  └──────────────┘        └──────────┬───────────────┘  │
│                                     │ stdin/stdout IPC  │
│                          ┌──────────▼───────────────┐  │
│                          │   Python Sidecar         │  │
│                          │                          │  │
│                          │  - sounddevice (record)  │  │
│                          │  - faster-whisper (STT)  │  │
│                          └──────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

Hotkey press ──▶ Rust backend ──▶ Python sidecar (start/stop record)
                                         │
                              Transcribed text
                                         │
                 Rust backend ◀──────────┘
                      │
                 wtype / SendInput ──▶ Active input field
```

## Composants

| Composant | Rôle | Techno |
|---|---|---|
| Frontend UI | Settings, indicateur visuel, menu tray | HTML/CSS/JS (ou Svelte) |
| Rust backend | Hotkey, tray, state machine, IPC, typing | Tauri v2 + Rust |
| Python sidecar | Enregistrement audio + transcription Whisper | Python + faster-whisper + sounddevice |
| Typer Linux | Tape le texte dans l'input actif | wtype (Wayland) / xdotool (X11) |
| Typer Windows | Tape le texte dans l'input actif | pyautogui ou SendInput (WinAPI) |

## Flux principaux

1. **Toggle enregistrement (hotkey)**
   `Hotkey pressé` → Rust détecte → envoie `{"cmd": "start"}` au sidecar Python → Python ouvre le stream audio → UI passe en état "recording" (indicateur pulse)

2. **Stop + transcription**
   `Hotkey pressé` → Rust envoie `{"cmd": "stop"}` → Python ferme le stream, transcrit avec Whisper → retourne `{"text": "..."}` → Rust appelle wtype/SendInput → texte tapé dans l'input actif → UI repasse en idle

3. **Changement de settings**
   `User modifie settings UI` → IPC Tauri → Rust met à jour `config.toml` → relance le sidecar Python avec nouveau modèle si besoin

## Protocole IPC JSON (stdin/stdout) — implémenté en TICKET-04

Communication entre Rust et le sidecar Python via des lignes JSON (une par ligne).

**Rust → Python (stdin) :**
```json
{"cmd": "start"}    // démarre l'enregistrement
{"cmd": "stop"}     // stoppe et transcrit
{"cmd": "ping"}     // health check
```

**Python → Rust (stdout) :**
```json
{"status": "recording"}                       // enregistrement démarré
{"status": "transcribing"}                    // transcription en cours
{"status": "done", "text": "texte transcrit"} // terminé (text peut être "")
{"error": "message d'erreur"}                 // en cas de problème
{"status": "ok"}                              // réponse au ping
```

En mode sidecar, Python tape toujours le texte directement (wtype/SendInput) ET renvoie le texte à Rust. La responsabilité du typing migrera vers Rust dans une version future.

Le sidecar est lancé avec `python whisper_type.py --sidecar`. Sans ce flag, le comportement daemon SIGUSR1 est conservé (mode standalone).

## Données & secrets
- **Config** : `~/.config/whisper-type/config.toml` (hotkey, modèle, langue)
- **Cache modèles** : `~/.cache/whisper-type/<model_size>/`
- **Aucun secret** — pas d'API key, pas de token

## État actuel (v0.1 — pré-Tauri)
Le daemon Python actuel (`whisper_type.py`) joue le rôle de l'ensemble du système. Il sera conservé comme sidecar et wrappé par Tauri en v1.

## Points d'évolution anticipés
- Migration sidecar Python → whisper-rs (Rust natif) si les perfs le justifient
- Support de modèles distillés (whisper-turbo) pour des transcriptions plus rapides
- Mode "streaming" (transcription en temps réel pendant l'enregistrement)

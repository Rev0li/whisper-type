# 04 — Roadmap & ticketing

## Sprints

### Sprint 0 — Fondations cross-platform (daemon stabilisé)
| Ticket | Titre | Dépend de | Statut |
|---|---|---|---|
| TICKET-01 | Config TOML (hotkey, modèle, langue) | — | todo |
| TICKET-02 | Support Windows (typing + hotkey sans WM) | TICKET-01 | todo |

### Sprint 1 — Scaffold Tauri
| Ticket | Titre | Dépend de | Statut |
|---|---|---|---|
| TICKET-03 | Init projet Tauri v2 + structure frontend | — | todo |
| TICKET-04 | Intégration Python sidecar (IPC stdin/stdout) | TICKET-03 | todo |
| TICKET-05 | Hotkey global en Rust (global-hotkey crate) | TICKET-03 | todo |

### Sprint 2 — UI & expérience
| Ticket | Titre | Dépend de | Statut |
|---|---|---|---|
| TICKET-06 | System tray (icône, menu start/stop, quit) | TICKET-04, TICKET-05 | todo |
| TICKET-07 | Indicateur visuel d'enregistrement (animation) | TICKET-06 | todo |
| TICKET-08 | Settings panel (modèle, hotkey, langue) | TICKET-06 | todo |

### Sprint 3 — Distribution
| Ticket | Titre | Dépend de | Statut |
|---|---|---|---|
| TICKET-09 | Téléchargement modèle au premier lancement + progress bar | TICKET-04 | todo |
| TICKET-10 | Build Windows (.exe) via GitHub Actions | TICKET-08 | todo |
| TICKET-11 | Build Linux (AppImage) via GitHub Actions | TICKET-08 | todo |

## Principe de découpage
- 1 ticket = une unité **livrable et testable** (pas un epic).
- Le statut de référence vit dans chaque `docs/tickets/<ID>.md` ; ce tableau est
  une vue d'ensemble, à resynchroniser ponctuellement
  (`grep -l 'status: ...' docs/tickets/*.md`).

## Jalons
- **MVP fonctionnel** : TICKET-01 + TICKET-02 → daemon configurable cross-platform sans UI
- **Alpha UI** : Sprint 1 + Sprint 2 complets → app Tauri utilisable avec tray + settings
- **v1.0** : Sprint 3 complet → installeurs publiés sur GitHub Releases

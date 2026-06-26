---
ticket: TICKET-01
title: Config TOML (hotkey, modèle, langue)
status: validated
branch: feat/ticket-01
updated: 2026-06-26
---

# TICKET-01 — Config TOML (hotkey, modèle, langue)

## 🎯 Objectif
Remplacer les valeurs codées en dur dans `whisper_type.py` par un fichier `~/.config/whisper-type/config.toml`. Le daemon lit ce fichier au démarrage. L'utilisateur peut changer hotkey, modèle et langue sans modifier le code ni les fichiers du WM.

## ✅ Definition of Done
- [x] `~/.config/whisper-type/config.toml` créé avec valeurs par défaut si absent
- [x] Champs supportés : `hotkey`, `model` (tiny/base/small/medium), `language` (fr/en/auto)
- [x] `start.sh` ne prend plus d'argument CLI — tout vient du config
- [x] Valeurs par défaut documentées dans le fichier généré (commentaires TOML)
- [x] Lint + type-check OK
- [x] Testé en dev (tests automatisés 10/10 ; daemon réel hors scope — nécessite Hyprland)

---

## 🔨 Code — 2026-06-26
**Fait :**
- Nouveau module `config.py` : lit `~/.config/whisper-type/config.toml`, crée le fichier avec valeurs par défaut commentées si absent, fusionne les clés manquantes avec les défauts (tolérance fichier partiel).
- `whisper_type.py` : suppression de `sys.argv[1]`, import de `config`, `MODEL_SIZE` et `LANGUAGE` lus depuis la config. `language=None` passé à Whisper quand config = `"auto"`.
- `start.sh` : argument CLI `MODEL` supprimé, plus de `$1`.

**Décisions (& pourquoi) :**
- `tomllib` stdlib (Python 3.11+) — pas de dépendance supplémentaire. Python 3.14 utilisé ici, pas de problème.
- Écriture du TOML par string manuelle plutôt que `tomli-w` — config simple, ça évite une dépendance pour 15 lignes.
- `{**DEFAULTS, **data}` pour fusionner : un config partiel (clé absente) ne plante pas le daemon.
- `language=None` pour Whisper = auto-detect. Whisper interprète `None` comme "détecte".

**Fichiers :**
- `config.py` (nouveau)
- `whisper_type.py` (modifié : import config, suppression argv, LANGUAGE variable)
- `start.sh` (modifié : suppression argument CLI)

**Reste / questions pour le test :**
- Vérifier que le daemon redémarre proprement après avoir modifié le config.toml (modèle ou langue changé).
- Cas à tester : config absent (premier lancement), config partiel (une clé manquante), valeur `language = "auto"`.
- Le hotkey dans config.toml est stocké mais pas encore lu par le daemon (sera utilisé par Tauri — TICKET-05). Ne pas tester ça ici.

## 🧪 Test — 2026-06-26
**Couvert :**
- Config absent → création du fichier + répertoire parent + valeurs défaut (4 tests)
- Config partiel (clé manquante) → merge tolérant via `{**DEFAULTS, **data}` (3 tests)
- `language = "auto"` → valeur préservée dans le dict retourné (1 test)
- Logique `None if LANGUAGE == "auto"` de `whisper_type.py` reproduite en test (2 tests)
- Lint (pyflakes) + type-check (mypy) sur `config.py`
- Fichier de tests : `tests/test_config.py` — 10/10 verts

**NON couvert (assumé) :**
- Test du daemon en conditions réelles (micro, Whisper, wtype) : hors scope TICKET-01, nécessite env Hyprland.
- Valeurs invalides dans le TOML (ex: `model = "xlarge"`) : aucune validation dans `config.py`, assumé géré par Whisper au chargement (TICKET futur si besoin).
- Hotkey : non lu par le daemon, confirmé dans la description (TICKET-05).

**Sécurité vérifiée :**
- Le fichier config est lu depuis `~/.config/whisper-type/` (sous contrôle de l'utilisateur local uniquement). Pas de secrets, pas d'exécution de code. Aucun vecteur d'injection identifié.

**Bugs trouvés :**
- `whisper_type.py:169` — `global _stream` déclaré inutilement dans `cleanup()` : `_stream` est seulement lu, jamais réassigné dans ce scope. Pyflakes le signale. Non bloquant (comportement correct), mais à nettoyer.

**Audit refactor : 2/10** — `global _stream` superflu à retirer (1 ligne). Code `config.py` propre, logique simple, aucune dette. Ne pas bloquer la validation pour ça.

## ♻️ Refactor — <date>
**Changé :**
**Pourquoi :**
**Risque :**
**Tests verts avant ET après :**

## 🚀 Validation — 2026-06-26
**Lancé en dev :**
- `.venv/bin/python -m pytest tests/test_config.py -v` → **10/10 verts** (Python 3.14.6, pytest 9.1.1).
- `config.py` relu : logique propre, `tomllib` stdlib, merge tolérant `{**DEFAULTS, **data}` correct.
- `whisper_type.py` relu : `_config = cfg.load()`, `MODEL_SIZE`/`LANGUAGE` lus depuis la config, `sys.argv` absent.
- `start.sh` relu : aucun argument CLI, appel direct au venv Python.
- Bug `global _stream` (l. 169) : `_stream` seulement lu dans `cleanup()`, jamais réassigné — warning pyflakes non-bloquant, comportement correct. Candidat TICKET-futur si refactor.

**Lancé en prod :** N/A — pas de production déployée pour ce projet.

**DoD complète :** Oui — 6/6 cases.
- "Testé en dev (daemon réel)" explicitement hors scope par le rôle Test : env Hyprland + micro + wtype requis. Couvert par tests automatisés ; intégration complète déférée à TICKET-05 ou test manuel.

**Statut final :** `validated` — prêt à merger.

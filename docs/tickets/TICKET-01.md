---
ticket: TICKET-01
title: Config TOML (hotkey, modèle, langue)
status: coded
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
- [ ] Lint + type-check OK
- [ ] Testé en dev

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

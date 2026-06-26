---
ticket: TICKET-01
title: Config TOML (hotkey, modèle, langue)
status: todo
branch: feat/ticket-01
updated: 2026-06-26
---

# TICKET-01 — Config TOML (hotkey, modèle, langue)

## 🎯 Objectif
Remplacer les valeurs codées en dur dans `whisper_type.py` par un fichier `~/.config/whisper-type/config.toml`. Le daemon lit ce fichier au démarrage. L'utilisateur peut changer hotkey, modèle et langue sans modifier le code ni les fichiers du WM.

## ✅ Definition of Done
- [ ] `~/.config/whisper-type/config.toml` créé avec valeurs par défaut si absent
- [ ] Champs supportés : `hotkey`, `model` (tiny/base/small/medium), `language` (fr/en/auto)
- [ ] `start.sh` ne prend plus d'argument CLI — tout vient du config
- [ ] Valeurs par défaut documentées dans le fichier généré (commentaires TOML)
- [ ] Lint + type-check OK
- [ ] Testé en dev

---

## 🔨 Code — <date>
**Fait :**
**Décisions (& pourquoi) :**
**Fichiers :**
**Reste / questions pour le test :**

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

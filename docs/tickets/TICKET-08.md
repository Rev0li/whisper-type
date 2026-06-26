---
ticket: TICKET-08
title: Settings panel (modèle, hotkey, langue)
status: todo
branch: feat/ticket-08
updated: 2026-06-26
---

# TICKET-08 — Settings panel (modèle, hotkey, langue)

## 🎯 Objectif
Une fenêtre settings minimaliste et moderne (ouverte via le tray). L'utilisateur peut changer le modèle Whisper, le raccourci clavier (via un "press to capture" input), et la langue. Les changements sont persistés dans `config.toml` et appliqués sans redémarrer l'app.

## ✅ Definition of Done
- [ ] UI settings : modèle (dropdown), hotkey (capture input), langue (dropdown avec "auto")
- [ ] Sauvegarde dans `~/.config/whisper-type/config.toml` à la validation
- [ ] Rechargement du hotkey sans redémarrer (TICKET-05 doit le supporter)
- [ ] Si modèle changé : sidecar Python relancé avec le nouveau modèle
- [ ] Design cohérent avec l'identité visuelle du projet (sobre, dark mode par défaut)

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

---
ticket: TICKET-05
title: Hotkey global en Rust (global-hotkey crate)
status: todo
branch: feat/ticket-05
updated: 2026-06-26
---

# TICKET-05 — Hotkey global en Rust (global-hotkey crate)

## 🎯 Objectif
Implémenter l'écoute du raccourci clavier global dans le backend Rust via le crate `global-hotkey`. La combinaison est lue depuis `config.toml` (TICKET-01). Un appui envoie `start` au sidecar, le suivant envoie `stop`. Fonctionne même quand la fenêtre de l'app est cachée.

## ✅ Definition of Done
- [ ] `global-hotkey` intégré dans `Cargo.toml`
- [ ] Hotkey lu depuis config (format : `"SUPER+grave"`, `"CTRL+SHIFT+SPACE"`, etc.)
- [ ] Toggle start/stop fonctionnel sur Linux
- [ ] Toggle start/stop fonctionnel sur Windows
- [ ] Changement de hotkey depuis settings (TICKET-08) rechargeable sans redémarrer l'app

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

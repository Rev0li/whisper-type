---
ticket: TICKET-06
title: System tray (icône, menu start/stop, quit)
status: todo
branch: feat/ticket-06
updated: 2026-06-26
---

# TICKET-06 — System tray (icône, menu start/stop, quit)

## 🎯 Objectif
L'app vit dans le system tray. L'icône change d'état (idle / recording / transcribing). Un clic droit ouvre un menu : Start/Stop, Open Settings, Quit. L'app ne montre pas de fenêtre principale au démarrage — le tray est l'unique point d'entrée.

## ✅ Definition of Done
- [ ] Icône tray présente au lancement (Linux + Windows)
- [ ] 3 états visuels : idle, recording (icône rouge/animée), transcribing (icône spinner)
- [ ] Menu clic droit : Toggle, Settings, Quit
- [ ] Clic sur "Toggle" équivalent au hotkey
- [ ] App ne se ferme pas en fermant la fenêtre settings (seulement via "Quit")

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

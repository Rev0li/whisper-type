---
ticket: TICKET-02
title: Support Windows (typing + hotkey sans WM)
status: todo
branch: feat/ticket-02
updated: 2026-06-26
---

# TICKET-02 — Support Windows (typing + hotkey sans WM)

## 🎯 Objectif
Faire tourner le daemon Python sur Windows. Deux problèmes spécifiques à résoudre : (1) typer dans l'input actif sans wtype (inexistant sur Windows), (2) écouter le hotkey global sans passer par le WM. Choisir et implémenter la solution retenue (pyautogui ou SendInput via ctypes).

## ✅ Definition of Done
- [ ] `type_text()` utilise pyautogui ou SendInput sur Windows (détection automatique de l'OS)
- [ ] Hotkey global fonctionnel sur Windows (lib `keyboard` ou autre)
- [ ] `start.sh` / `start.bat` documenté pour Windows
- [ ] Testé sur Windows 10 ou 11 (VM acceptable)
- [ ] Fallback clipboard si typing échoue (avec notif utilisateur)
- [ ] Lint + type-check OK

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

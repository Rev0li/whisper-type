---
ticket: TICKET-10
title: Build Windows (.exe) via GitHub Actions
status: todo
branch: feat/ticket-10
updated: 2026-06-26
---

# TICKET-10 — Build Windows (.exe) via GitHub Actions

## 🎯 Objectif
Mettre en place un workflow GitHub Actions qui produit un installeur Windows `.exe` à chaque tag git `v*`. Le bundle inclut le sidecar Python (via PyInstaller ou python-build-standalone) et l'app Tauri. L'artifact est uploadé dans les GitHub Releases.

## ✅ Definition of Done
- [ ] Workflow `.github/workflows/release.yml` avec job `build-windows` (runner `windows-latest`)
- [ ] Python sidecar bundlé (aucun Python requis côté utilisateur)
- [ ] `cargo tauri build` produit un `.exe` signable (code signing optionnel v1)
- [ ] Artifact uploadé automatiquement dans la GitHub Release du tag
- [ ] README mis à jour avec le lien de téléchargement

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

---
ticket: TICKET-11
title: Build Linux (AppImage) via GitHub Actions
status: todo
branch: feat/ticket-11
updated: 2026-06-26
---

# TICKET-11 — Build Linux (AppImage) via GitHub Actions

## 🎯 Objectif
Étendre le workflow GitHub Actions pour produire une AppImage Linux à chaque tag `v*`. L'AppImage inclut le sidecar Python et tourne sans installation sur toute distro Linux récente (Fedora, Ubuntu, Arch…).

## ✅ Definition of Done
- [ ] Job `build-linux` ajouté dans `.github/workflows/release.yml` (runner `ubuntu-latest`)
- [ ] Python sidecar bundlé dans l'AppImage
- [ ] AppImage testée sur Fedora 44 (env de dev) et Ubuntu 24.04
- [ ] Artifact uploadé dans la GitHub Release du tag
- [ ] README mis à jour avec les deux liens de téléchargement (Windows + Linux)

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

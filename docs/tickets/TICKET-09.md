---
ticket: TICKET-09
title: Téléchargement modèle au premier lancement + progress bar
status: todo
branch: feat/ticket-09
updated: 2026-06-26
---

# TICKET-09 — Téléchargement modèle au premier lancement + progress bar

## 🎯 Objectif
Au premier lancement (ou si le modèle configuré est absent du cache), l'app détecte l'absence du modèle, affiche une fenêtre de téléchargement avec une barre de progression, puis démarre normalement une fois le modèle en cache. L'utilisateur comprend ce qui se passe et n'a pas l'impression que l'app est bloquée.

## ✅ Definition of Done
- [ ] Détection automatique si le modèle est présent dans `~/.cache/whisper-type/`
- [ ] Fenêtre de téléchargement avec : nom du modèle, taille estimée, barre de progression, ETA
- [ ] Téléchargement via faster-whisper (qui gère le cache HuggingFace)
- [ ] En cas d'erreur réseau : message clair + bouton "Réessayer"
- [ ] Fonctionne sur Linux et Windows

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

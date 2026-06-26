---
ticket: TICKET-04
title: Intégration Python sidecar (IPC stdin/stdout)
status: todo
branch: feat/ticket-04
updated: 2026-06-26
---

# TICKET-04 — Intégration Python sidecar (IPC stdin/stdout)

## 🎯 Objectif
Le backend Rust démarre `whisper_type.py` comme sidecar (subprocess) et communique avec lui via JSON sur stdin/stdout. Commandes : `start`, `stop`. Réponse : `{"text": "..."}` ou `{"error": "..."}`. Le sidecar Python est adapté pour lire les commandes depuis stdin au lieu de réagir aux signaux UNIX.

## ✅ Definition of Done
- [ ] Protocole IPC JSON défini et documenté dans `02-architecture.md`
- [ ] `whisper_type.py` modifié : lit stdin en boucle, répond sur stdout
- [ ] Rust spawn/kill le sidecar proprement (avec gestion SIGTERM)
- [ ] Test manuel : Rust envoie `start` → Python enregistre → Rust envoie `stop` → Python retourne le texte
- [ ] Aucune régression sur le mode daemon SIGUSR1 (conserver pour usage standalone)

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

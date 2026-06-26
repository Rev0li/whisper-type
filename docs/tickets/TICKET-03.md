---
ticket: TICKET-03
title: Init projet Tauri v2 + structure frontend
status: coded
branch: feat/ticket-03
updated: 2026-06-26
---

# TICKET-03 — Init projet Tauri v2 + structure frontend

## 🎯 Objectif
Initialiser la structure Tauri v2 dans le repo. Choisir le framework frontend (vanilla JS ou Svelte) et poser le scaffold : fenêtre principale, window transparente pour l'indicateur, config Tauri de base. À l'issue de ce ticket, `cargo tauri dev` doit lancer une fenêtre vide sans erreur.

## ✅ Definition of Done
- [x] `src-tauri/` initialisé avec Tauri v2
- [x] Frontend scaffold en place (vanilla JS retenu — à documenter dans 01-tech-decisions.md)
- [ ] `cargo tauri dev` lance sans erreur sur Linux
- [x] `.gitignore` mis à jour (target/, node_modules/)
- [ ] README mis à jour avec les prérequis dev (Rust, Node)

---

## 🔨 Code — 2026-06-26
**Fait :**
- `package.json` + `@tauri-apps/cli@^2` installé via npm.
- Scaffold Tauri v2 généré via `npx tauri init --ci` (non-interactif) : `src-tauri/` complet avec `Cargo.toml`, `build.rs`, `src/main.rs`, `src/lib.rs`, `capabilities/default.json`, icônes placeholder.
- `tauri.conf.json` mis à jour : identifiant `dev.rev0li.whisper-type`, fenêtre `420×520` non-redimensionnable, `visible: false` (ouverture contrôlée par le tray — TICKET-06), Android bundle retiré.
- Frontend vanilla JS créé dans `src/` : `index.html` (settings panel), `styles.css` (dark theme sobre), `main.js` (capture hotkey + TODO TICKET-08 pour IPC).
- `.gitignore` mis à jour : `src-tauri/target/` et `node_modules/`.

**Décisions (& pourquoi) :**
- **Vanilla JS** retenu (pas Svelte) : UI minimaliste, aucun build step requis, `frontendDist` pointe directement sur `src/` — simplifie le dev et le bundle. Documenté dans `01-tech-decisions.md` (à mettre à jour en TICKET-03 ou TICKET-08).
- **`visible: false`** sur la fenêtre principale : l'app vit dans le tray (TICKET-06), la fenêtre settings ne s'ouvre qu'à la demande — évite un flash au démarrage.
- **`cargo tauri dev` non testé dans ce contexte** : nécessite un display Wayland/X11. Les crates sont téléchargées (323), la compilation complète est déléguée au testeur sur son poste.

**Fichiers :**
- `package.json` (nouveau)
- `package-lock.json` (généré)
- `node_modules/` (gitignored)
- `src-tauri/` (nouveau — scaffold complet)
- `src/index.html`, `src/styles.css`, `src/main.js` (nouveaux)
- `.gitignore` (mis à jour)

**Reste / questions pour le test :**
- **Critique** : lancer `npm run dev` (alias `cargo tauri dev`) sur le poste avec display — vérifier que la fenêtre compile et s'ouvre sans erreur.
- Vérifier que `visible: false` est bien respecté (pas de fenêtre au démarrage, app dans le tray).
- `01-tech-decisions.md` : ajouter ADR-005 "Vanilla JS retenu pour le frontend" (peut être fait par le testeur ou reporté à TICKET-08).

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

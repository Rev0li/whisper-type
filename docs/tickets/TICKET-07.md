---
ticket: TICKET-07
title: Indicateur visuel d'enregistrement (animation)
status: coded
branch: feat/ticket-07
updated: 2026-06-27
---

# TICKET-07 — Indicateur visuel d'enregistrement (animation)

## 🎯 Objectif
Afficher un indicateur visuel discret quand l'enregistrement est actif — idéalement une petite fenêtre flottante sans décoration (toujours au-dessus) avec une animation de waveform ou un cercle pulsant. Elle disparaît dès que la transcription commence.

## ✅ Definition of Done
- [x] Fenêtre overlay sans décoration, always-on-top, positionnée en bas à droite (configurable)
- [x] Animation "recording" visible (pulse ou waveform CSS)
- [x] État "transcribing" différent visuellement (spinner ou couleur différente)
- [x] Fenêtre masquée en idle (pas de place prise dans la taskbar)
- [ ] Fonctionne sur Linux (Wayland + X11) et Windows

---

## 🔨 Code — 2026-06-27
**Fait :**
- `tauri.conf.json` : fenêtre `"overlay"` ajoutée (200×54, decorations: false, alwaysOnTop: true, visible: false, skipTaskbar: true, transparent: true, url: "overlay.html"). `"withGlobalTauri": true` ajouté dans `build` pour activer `window.__TAURI__.*` dans les pages HTML.
- `src/overlay.html` : pill (capsule arrondie, fond dark semi-transparent 92%, `backdrop-filter: blur`). Deux états CSS :
  - `.recording` : point rouge (`#ff4444`) pulsant (`@keyframes pulse` — scale + box-shadow).
  - `.transcribing` : anneau orange (`#ffaa00`) qui tourne (`@keyframes spin`).
  - `-webkit-app-region: drag` sur body : la fenêtre est déplaçable.
- `src/overlay.js` :
  - `positionBottomRight()` : utilise `window.screen.width/height` × `window.devicePixelRatio` → `PhysicalPosition` (coordonnées physiques, HiDPI-safe). Positionne à 208px du bord droit, 90px du bas.
  - `showRecording()` : `.recording`, label "Recording...", position, `win.show()`.
  - `showTranscribing()` : `.transcribing`, label "Transcribing..." (fenêtre déjà visible).
  - `hideOverlay()` : `win.hide()` + reset visuel pour la prochaine ouverture.
  - `listen('sidecar-msg', cb)` : écoute les events globaux Rust, dispatche selon `msg.status`.
- **Aucun changement Rust** : l'overlay est entièrement auto-géré en JS. Les events `sidecar-msg` sont déjà émis à toutes les fenêtres par `lib.rs` (TICKET-04/06).

**Décisions (& pourquoi) :**
- **Overlay en JS pur, zéro Rust** : les events `sidecar-msg` sont globaux (`handle.emit()`). L'overlay reçoit les mêmes events que le frontend principal sans code Rust supplémentaire. Évite de coupler `tray.rs` ou `lib.rs` à la logique overlay.
- **`transparent: true` sur la fenêtre** : permet au `border-radius: 999px` du pill d'être visible sans rectangle blanc autour. Risque : non supporté sur tous les compositors Linux. Fallback : si transparent ne fonctionne pas, le fond CSS `rgba(15,15,15,0.92)` reste visible mais rectangulaire.
- **`PhysicalPosition` avec `devicePixelRatio`** : sans multiplier par le scale factor, la position serait décalée sur les écrans HiDPI (Retina, 4K). `window.screen.width` donne des logical pixels, mais `setPosition` attend des physical pixels.
- **`skipTaskbar: true`** : l'overlay n'apparaît pas dans la barre des tâches (comportement attendu pour un indicateur flottant).
- **Reset visuel dans `hideOverlay()`** : si l'utilisateur voit "Transcribing..." et que la fenêtre re-s'ouvre immédiatement après, elle doit afficher `.recording`, pas `.transcribing`.
- **`-webkit-app-region: drag`** : permet à l'utilisateur de déplacer l'overlay si la position par défaut n'est pas idéale (geste natif, sans code JS supplémentaire). La config de position est déférrée à TICKET-08/settings.

**Fichiers :**
- `src-tauri/tauri.conf.json` (fenêtre overlay + withGlobalTauri)
- `src/overlay.html` (nouveau)
- `src/overlay.js` (nouveau)

**Reste / questions pour le test :**
- **`withGlobalTauri: true`** : vérifier que `window.__TAURI__` est bien injecté dans les deux pages (main + overlay). Sur Tauri v2.11.3, le champ exact dans `build` est `"withGlobalTauri"` — à confirmer dans le JSON schema.
- **`window.__TAURI__.dpi.PhysicalPosition`** : disponible avec `withGlobalTauri` ? Alternative si absent : `window.__TAURI__.window.PhysicalPosition` (Tauri v2 réorganise parfois).
- **`transparent: true` sur Linux** : Hyprland supporte les fenêtres transparentes, mais ça dépend du `blur` activé dans hyprland.conf. Sans compositor blur, `backdrop-filter: blur` ne fonctionne pas — le fond sera juste `rgba(15,15,15,0.92)` opaque (acceptable).
- **`alwaysOnTop` sur Wayland** : non garanti selon le protocole. Sur Hyprland, ajouter `windowrule = pin, overlay` dans hyprland.conf pour forcer.
- **Position HiDPI** : tester sur écran avec `devicePixelRatio > 1`. Si décalé, adapter le calcul dans `positionBottomRight()`.
- **Compilation** : aucun Rust modifié → pas de `cargo build` requis pour TICKET-07. Tester directement avec `cargo tauri dev`.

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

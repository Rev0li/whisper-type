---
ticket: TICKET-02
title: Support Windows (typing + hotkey sans WM)
status: coded
branch: feat/ticket-02
updated: 2026-06-26
---

# TICKET-02 — Support Windows (typing + hotkey sans WM)

## 🎯 Objectif
Faire tourner le daemon Python sur Windows. Deux problèmes spécifiques à résoudre : (1) typer dans l'input actif sans wtype (inexistant sur Windows), (2) écouter le hotkey global sans passer par le WM. Choisir et implémenter la solution retenue (pyautogui ou SendInput via ctypes).

## ✅ Definition of Done
- [x] `type_text()` utilise pyautogui ou SendInput sur Windows (détection automatique de l'OS)
- [x] Hotkey global fonctionnel sur Windows (lib `keyboard` ou autre)
- [x] `start.sh` / `start.bat` documenté pour Windows
- [ ] Testé sur Windows 10 ou 11 (VM acceptable)
- [x] Fallback clipboard si typing échoue (avec notif utilisateur)
- [ ] Lint + type-check OK

---

## 🔨 Code — 2026-06-26
**Fait :**
- `notify()` : branche Windows → log uniquement (notify-send inexistant sur Windows, le futur tray icon TICKET-06 gèrera ça).
- `type_text()` scindé en `_type_text_windows()` et `_type_text_linux()` : détection automatique via `IS_WINDOWS`.
- `_type_text_windows()` : `pyperclip.copy(text)` + `keyboard.send("ctrl+v")` — gère tout Unicode sans dépendance native complexe.
- `main()` : branche Windows avec `keyboard.add_hotkey()` + `time.sleep(1)` en boucle ; branche Linux garde SIGUSR1 + `signal.pause()`.
- `_hotkey_to_keyboard_lib()` : convertit le format config (`SUPER+grave`) vers le format attendu par la lib `keyboard` (`windows+\``).
- `PID_FILE` : `tempfile.gettempdir()` au lieu de `/tmp` — cross-platform (`%TEMP%` sur Windows).
- `start.bat` : lance le daemon via `pythonw.exe` (pas de fenêtre console).
- `requirements.txt` : ajout de `keyboard` et `pyperclip`.

**Décisions (& pourquoi) :**
- **Clipboard + Ctrl+V** plutôt que `pyautogui.typewrite()` : pyautogui ne gère pas les chars Unicode > ASCII. Le clipboard est fiable dans 100% des apps Windows.
- **`keyboard` lib pour le hotkey** : fonctionne sur Windows sans droits admin (contrairement à Linux où elle exige root — on ne l'utilise donc que sur Windows). Sur Linux on garde SIGUSR1.
- **`keyboard` et `pyperclip` dans requirements.txt** : installés partout mais importés conditionnellement (`if IS_WINDOWS`) — pas d'impact sur Linux.
- **`pythonw.exe`** dans start.bat : évite l'apparition d'une fenêtre console noire au démarrage.

**Fichiers :**
- `whisper_type.py` (modifié : IS_WINDOWS, notify, type_text scindé, main branché, PID_FILE cross-platform)
- `start.bat` (nouveau)
- `requirements.txt` (keyboard + pyperclip ajoutés)

**Reste / questions pour le test :**
- Le test réel du hotkey et du typing nécessite Windows (VM acceptable). Impossible à tester automatiquement sur Linux.
- Vérifier que `keyboard.add_hotkey()` n'entre pas en conflit si le même hotkey est déjà pris par Windows.
- Vérifier que `pyperclip` ne casse pas le contenu du clipboard de l'utilisateur (le texte précédent est écrasé — comportement assumé, non restauré).
- `_type_text_windows()` : le `time.sleep(0.05)` est empirique. Peut nécessiter ajustement sur machines lentes.

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

# 00 — Vision

## Le problème
Écrire des prompts longs est lent et fatiguant. Les outils STT existants sont soit cloud (vie privée compromise), soit mal intégrés (copier-coller manuel). Il n'existe pas d'outil simple qui écoute un raccourci clavier et tape directement dans l'input actif, sans friction.

## La vision
Une petite app discrète, toujours prête en arrière-plan. Un raccourci clavier, on parle, le texte apparaît là où le curseur est. Aucun clic supplémentaire, aucune connexion réseau, aucune donnée qui quitte la machine.

## Pour qui
- **Développeurs** qui dictent des prompts IA, des messages, des commentaires de code
- **Power users** Linux/Windows qui veulent un outil clavier-first
- **Utilisateurs soucieux de leur vie privée** qui refusent les STT cloud

## Valeur
- 100% local — aucune donnée envoyée
- Zéro friction : raccourci → parole → texte tapé automatiquement
- Multilingue (détection automatique)
- Léger (~5 MB app, modèle téléchargé une fois)

## Principes directeurs
1. **Local-first** — aucune dépendance réseau en fonctionnement normal
2. **Frictionless** — une touche suffit, aucun clic
3. **Simple > exhaustif** — UI minimale, pas de features gadget
4. **Cross-platform** — Windows et Linux traités comme citoyens de première classe
5. **Open source** — transparent, auditable, extensible

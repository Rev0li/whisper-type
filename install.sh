#!/usr/bin/env bash
# install.sh — installe toutes les dépendances et configure Hyprland.
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== whisper-type installer ==="

# 1. Dépendances système
echo ""
echo "[1/4] Installation des paquets système..."
sudo dnf install -y --skip-unavailable \
    portaudio \
    portaudio-devel \
    wtype \
    libnotify \
    alsa-utils

# 2. Dépendances Python dans un venv
echo ""
echo "[2/4] Création de l'environnement Python..."
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install --upgrade pip
"$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt"

# Met à jour le shebang du daemon pour utiliser le venv
sed -i "1s|.*|#!$DIR/.venv/bin/python3|" "$DIR/whisper_type.py"

# 3. Rend les scripts exécutables
echo ""
echo "[3/4] Permissions..."
chmod +x "$DIR/whisper_type.py" "$DIR/toggle.sh" "$DIR/start.sh" "$DIR/stop.sh"

# 4. Config Hyprland
echo ""
echo "[4/4] Configuration Hyprland..."

HYPR_CONFIG="$HOME/.config/hypr/hyprland.conf"
TOGGLE_CMD="$DIR/toggle.sh"
BIND_LINE="bind = SUPER, F9, exec, $TOGGLE_CMD"
EXEC_LINE="exec-once = $DIR/start.sh"

if [ -f "$HYPR_CONFIG" ]; then
    if grep -qF "$TOGGLE_CMD" "$HYPR_CONFIG"; then
        echo "  Bind déjà présent dans hyprland.conf"
    else
        echo "" >> "$HYPR_CONFIG"
        echo "# whisper-type — SUPER+F9 pour toggle enregistrement" >> "$HYPR_CONFIG"
        echo "$BIND_LINE" >> "$HYPR_CONFIG"
        echo "  Ajouté : $BIND_LINE"
    fi

    if grep -qF "$DIR/start.sh" "$HYPR_CONFIG"; then
        echo "  exec-once déjà présent."
    else
        echo "$EXEC_LINE" >> "$HYPR_CONFIG"
        echo "  Ajouté : $EXEC_LINE"
    fi
else
    echo "  hyprland.conf non trouvé à $HYPR_CONFIG"
    echo "  Ajoute manuellement dans ta config Hyprland :"
    echo "    $EXEC_LINE"
    echo "    $BIND_LINE"
fi

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Raccourci : SUPER + F9  (change dans hyprland.conf si tu veux autre chose)"
echo "Modèle    : small (fr) — lance './start.sh base' pour un modèle plus rapide"
echo ""
echo "Démarre maintenant avec :"
echo "  $DIR/start.sh"

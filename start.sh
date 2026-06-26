#!/usr/bin/env bash
# start.sh — démarre le daemon whisper-type en arrière-plan.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="/tmp/whisper-type.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Daemon déjà en cours (PID $(cat $PID_FILE))"
    exit 0
fi

MODEL="${1:-small}"

nohup "$DIR/.venv/bin/python3" "$DIR/whisper_type.py" "$MODEL" > "$DIR/whisper-type.log" 2>&1 &
echo "Daemon démarré (PID $!)"

#!/usr/bin/env bash
# stop.sh — arrête le daemon proprement.

PID_FILE="/tmp/whisper-type.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Daemon non démarré."
    exit 0
fi

PID=$(cat "$PID_FILE")
kill -TERM "$PID" 2>/dev/null && echo "Daemon arrêté (PID $PID)" || echo "PID $PID introuvable."
rm -f "$PID_FILE"

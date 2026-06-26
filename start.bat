@echo off
setlocal
set DIR=%~dp0

if not exist "%DIR%.venv\Scripts\python.exe" (
    echo Venv non trouve. Lance install.bat d'abord.
    pause
    exit /b 1
)

:: Verifie si le daemon tourne deja
set PID_FILE=%TEMP%\whisper-type.pid
if exist "%PID_FILE%" (
    echo Daemon deja en cours.
    exit /b 0
)

start /b "" "%DIR%.venv\Scripts\pythonw.exe" "%DIR%whisper_type.py" > "%DIR%whisper-type.log" 2>&1
echo Daemon demarre.

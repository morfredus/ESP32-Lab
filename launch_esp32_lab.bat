@echo off
setlocal

REM Repertoire du projet ESP32-Lab
cd /d "%USERPROFILE%\Codage\Python\ESP32-Lab" || (
    echo Erreur : dossier du projet introuvable.
    pause
    exit /b 1
)

REM Configuration Python
set "PYTHONPATH=src"
set "PYTHON=%CD%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Erreur : environnement virtuel Python introuvable :
    echo %PYTHON%
    pause
    exit /b 1
)

REM Lancer le serveur dans une nouvelle fenetre
start "ESP32-Lab Server" cmd /k ""%PYTHON%" -m web.server"

REM Attendre quelques secondes que le serveur demarre
timeout /t 3 /nobreak >nul

REM Ouvrir l'interface web
start "" "http://127.0.0.1:8765"

endlocal

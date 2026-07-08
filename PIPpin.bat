@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo   Gandalf - Dependency Installer (Var A)
echo ==========================================
echo.

REM --- Check: Python verfügbar?
where python >nul 2>&1
if errorlevel 1 (
  echo [FEHLER] Python wurde nicht gefunden.
  echo Bitte Python installieren und sicherstellen, dass "python" im PATH ist.
  echo.
  pause
  exit /b 1
)

echo [OK] Python gefunden: 
python --version
echo.

REM --- pip aktualisieren (best effort)
echo [INFO] Aktualisiere pip...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo [WARN] pip upgrade ist fehlgeschlagen (wir versuchen trotzdem weiter)...
)
echo.

REM --- requirements installieren
if not exist "requirements.txt" (
  echo [FEHLER] requirements.txt nicht gefunden im aktuellen Ordner:
  echo %cd%
  echo.
  pause
  exit /b 1
)

echo [INFO] Installiere Python-Pakete aus requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [FEHLER] pip install -r requirements.txt ist fehlgeschlagen.
  echo.
  pause
  exit /b 1
)
echo [OK] Python-Pakete installiert.
echo.

REM --- Playwright Browser installieren (Chromium)
echo [INFO] Installiere Playwright Chromium...
python -m playwright install chromium
if errorlevel 1 (
  echo [FEHLER] playwright install chromium ist fehlgeschlagen.
  echo.
  pause
  exit /b 1
)
echo [OK] Playwright Chromium installiert.
echo.

echo ==========================================
echo [FERTIG] Setup abgeschlossen.
echo - Jetzt kannst du Gandalf normal starten.
echo - Beim ersten Upload ggf. im Chrome-Fenster in OrcaScan einloggen.
echo ==========================================
echo.
pause
exit /b 0

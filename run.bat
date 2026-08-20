@echo off
chcp 65001 > nul
title MIA
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"

REM ----------------------------------------------------------------------
REM  MIA launcher (SILENT worker)
REM  Intended to be started by MIA.vbs, which runs this window HIDDEN.
REM  It prepares the environment, refreshes data, starts Streamlit in the
REM  background, and opens the browser only once the app actually answers.
REM  All output goes to mia_last_run.log so problems can still be diagnosed
REM  even though nothing is shown on screen.
REM ----------------------------------------------------------------------
set "LOG=%~dp0mia_last_run.log"
echo MIA launch %date% %time% > "%LOG%"

REM ---------- Python / virtual env ----------
REM Use the local .venv if it exists; system Python is only needed to create it.
if exist ".venv\Scripts\python.exe" goto :venv_ready

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY where python3 >nul 2>&1 && set "PY=python3"
if not defined PY (
  echo [ERROR] Python not installed and no .venv found. >> "%LOG%"
  powershell -NoProfile -Command "Start-Process 'https://www.python.org/downloads/'"
  exit /b 1
)
%PY% -m venv .venv >> "%LOG%" 2>&1
if errorlevel 1 exit /b 1

:venv_ready
set "VENV_PY=.venv\Scripts\python.exe"

REM ---------- dependencies (first run only) ----------
if not exist ".venv\.deps_installed" (
  "%VENV_PY%" -m pip install --upgrade pip >> "%LOG%" 2>&1
  "%VENV_PY%" -m pip install -r requirements.txt >> "%LOG%" 2>&1
  if errorlevel 1 exit /b 1
  echo done > .venv\.deps_installed
)

REM ---------- refresh knowledge banks + demo data ----------
"%VENV_PY%" knowledge_banks\seed_data.py >> "%LOG%" 2>&1
"%VENV_PY%" data\schema.py >> "%LOG%" 2>&1
"%VENV_PY%" seed_demo_elders.py >> "%LOG%" 2>&1

REM ---------- free port 8501 from any previous instance ----------
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do taskkill /F /PID %%P >nul 2>&1


REM ensure Streamlit's first-run email prompt is skipped (it would hang on redirected input)
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit" >nul 2>&1
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
  >"%USERPROFILE%\.streamlit\credentials.toml" echo [general]
  >>"%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

REM ---------- open the browser as soon as Streamlit is listening (detached, hidden) ----------
start "" /b cmd /c "%~dp0_openbrowser.bat"

REM ---------- run Streamlit (this hidden window keeps it alive) ----------
"%VENV_PY%" -m streamlit run ui\app.py --server.headless true --server.port 8501 --server.address localhost --browser.gatherUsageStats false >> "%LOG%" 2>&1

@echo off
REM Helper: wait until Streamlit is actually listening on port 8501, then open
REM the default browser. Uses netstat (no HTTP request, so no proxy/firewall
REM issues) and cmd's built-in START (the reliable way to open the default
REM browser on Windows). Launched hidden+detached by run.bat.
REM Writes its own marker file (NOT the streamlit-locked log) for diagnostics.
setlocal
set "URL=http://localhost:8501"
set "MARK=%~dp0mia_browser.log"
echo [openbrowser] started %date% %time% > "%MARK%"

:waitloop
REM ~1s pause that works without a console (timeout needs a console; ping doesn't)
ping -n 2 127.0.0.1 >nul
netstat -ano | findstr ":8501" | findstr "LISTENING" >nul
if errorlevel 1 goto waitloop

echo [openbrowser] port 8501 up - launching browser %date% %time% >> "%MARK%"
start "" "%URL%"
echo [openbrowser] start issued %date% %time% >> "%MARK%"

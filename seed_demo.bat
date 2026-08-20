@echo off
chcp 65001 > nul
title ElderCare - Demo Seeder
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run run.bat at least once first to set up Python and dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" seed_demo_elders.py
echo.
echo Done. Demo elders are in the database. Run run.bat to view them.
pause

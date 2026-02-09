@echo off
start "" python -m holodeck_web
timeout /t 2 /nobreak >nul
start http://localhost:8000

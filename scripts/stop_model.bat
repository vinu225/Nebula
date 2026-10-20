@echo off
title Sovereign AI - Stop Model & Free Memory
echo =========================================================
echo    Sovereign AI Workbench - Model Unload Utility
echo =========================================================
echo.
echo Stopping Ollama models and freeing GPU VRAM / RAM...
echo.

python "%~dp0auto_stop_model.py" --stop

echo.
echo =========================================================
echo Done! You can close this window.
echo =========================================================
pause

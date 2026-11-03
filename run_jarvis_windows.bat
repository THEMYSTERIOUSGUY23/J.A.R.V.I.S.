@echo off
title J.A.R.V.I.S. // Native Local GPU Desktop Launcher
echo [J.A.R.V.I.S.] Initializing Native Desktop Neural Core...
python -m pip install --quiet psutil pyttsx3 SpeechRecognition
start /B ollama serve >nul 2>&1
python jarvis_desktop.py

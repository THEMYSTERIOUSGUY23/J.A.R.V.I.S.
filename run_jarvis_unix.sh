#!/usr/bin/env bash
set -e
echo "[J.A.R.V.I.S.] Initializing Native Desktop Neural Core..."
python3 -m pip install --quiet psutil pyttsx3 SpeechRecognition || true
python3 jarvis_desktop.py

@echo off
title J.A.R.V.I.S. // Native .EXE Compiler
echo [J.A.R.V.I.S.] Installing PyInstaller and packaging standalone JARVIS_Desktop.exe ...
python -m pip install psutil pyttsx3 SpeechRecognition pyinstaller
pyinstaller --onefile --windowed --name "JARVIS_Desktop" jarvis_desktop.py
echo.
echo [COMPLETE] Your standalone native application is ready at: dist\JARVIS_Desktop.exe
pause

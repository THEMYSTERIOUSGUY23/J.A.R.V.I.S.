J.A.R.V.I.S. // NATIVE LOCAL GPU DESKTOP APPLICATION
=====================================================

This package runs natively as a desktop GUI window on your laptop (Windows, Linux, or macOS)
using Python's native Tkinter hardware canvas — NO web browser or HTML file required.

1. PREREQUISITE (LOCAL GPU LLM ENGINE)
--------------------------------------
Install Ollama (https://ollama.com) so J.A.R.V.I.S. can run models on your laptop GPU:
    ollama pull llama3.2

2. RUN IMMEDIATELY AS A NATIVE DESKTOP APP
------------------------------------------
- Windows: Double-click `run_jarvis_windows.bat` (or run `python jarvis_desktop.py`)
- Linux / macOS: Run `chmod +x run_jarvis_unix.sh && ./run_jarvis_unix.sh` (or `python3 jarvis_desktop.py`)

3. COMPILE INTO A STANDALONE .EXE / DESKTOP BINARY (OPTIONAL)
-------------------------------------------------------------
- Windows: Double-click `build_windows_exe.bat` -> produces `dist/JARVIS_Desktop.exe`
- Linux / macOS:
    pip install pyinstaller psutil pyttsx3 SpeechRecognition
    pyinstaller --onefile --windowed --name "JARVIS_Desktop" jarvis_desktop.py

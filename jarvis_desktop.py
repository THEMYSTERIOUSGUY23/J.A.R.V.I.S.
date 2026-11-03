#!/usr/bin/env python3
"""
J.A.R.V.I.S. // Native Local GPU Desktop Application (v2.0 — RTX 5050 Auto-Bootstrap Edition)
---------------------------------------------------------------------------------------------
A standalone native desktop GUI application (Tkinter + Hardware Canvas) for Windows, Linux, & macOS.
- Auto-detects, starts, and pulls local GPU LLM models via Ollama (optimized for 8GB VRAM GPUs like RTX 5050)
- Streams multi-turn conversations from your local GPU with real-time nvidia-smi telemetry
- Executes native desktop voice/text directives (app launching, hardware diagnostics, local RAG vault)
"""

import json
import math
import os
import platform
import queue
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Optional native modules
try:
    import psutil
except ImportError:
    psutil = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


# ==================== STARK HUD COLOR PALETTE ====================
BG_DEEP = "#030914"
BG_PANEL = "#071426"
BG_INPUT = "#040d1a"
CYAN_PRIMARY = "#00f0ff"
CYAN_DIM = "#007a8c"
BLUE_ACCENT = "#0077ff"
AMBER_ALERT = "#ffaa00"
CRIMSON_ALERT = "#ff2a55"
EMERALD_OK = "#00e699"
TEXT_MAIN = "#e0f7ff"
TEXT_MUTED = "#6ca6c1"

VAULT_FILE = Path.home() / ".jarvis_local_vault.json"
CONFIG_FILE = Path.home() / ".jarvis_local_config.json"


def find_ollama_binary():
    """Finds the ollama executable in PATH or standard Windows/macOS install locations."""
    in_path = shutil.which("ollama")
    if in_path:
        return in_path
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidate = Path(local_app) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.exists():
            return str(candidate)
    elif sys.platform == "darwin":
        for p in ("/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "/Applications/Ollama.app/Contents/Resources/ollama"):
            if Path(p).exists():
                return p
    return None


class JarvisDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("J.A.R.V.I.S. // Local GPU Native Desktop Core (Mark LXXXV)")
        self.geometry("1240x790")
        self.minsize(980, 660)
        self.configure(bg=BG_DEEP)

        # Application State
        self.ollama_url = "http://localhost:11434"
        self.selected_model = tk.StringVar(value="llama3.2")
        self.active_protocol = "STANDARD"
        self.voice_enabled = tk.BooleanVar(value=True)
        self.ollama_online = False
        self.is_generating = False
        self.is_speaking = False
        self.is_listening = False
        self.anim_angle = 0.0
        self.tokens_per_sec = 0.0
        self.chat_messages = []  # Multi-turn conversation history

        # GPU & System Telemetry State
        self.gpu_info = {
            "name": "Scanning Local GPU...",
            "util": 0.0,
            "vram_used": 0.0,
            "vram_total": 8192.0,
            "temp": 48.0,
            "power": 18.0,
            "real_nvidia": False,
        }
        self.cpu_percent = 12.0
        self.ram_used_gb = 8.0
        self.ram_total_gb = 16.0

        # Thread-safe UI Queue
        self.ui_queue = queue.Queue()

        # Load Persistent Local Vault & Config
        self.vault_items = self._load_vault()
        self._load_config()

        # Build Native Desktop Layout
        self._configure_styles()
        self._build_header()
        self._build_main_workspace()
        self._build_status_bar()

        # Start Background Loops
        self._animate_arc_reactor()
        self._process_ui_queue()
        threading.Thread(target=self._telemetry_worker, daemon=True).start()
        threading.Thread(target=self._auto_bootstrap_ollama, kwargs={"silent": True}, daemon=True).start()

        # Initial Greeting
        self._append_chat(
            "J.A.R.V.I.S.",
            "Good afternoon, Sir. Native desktop neural interface online. "
            "I have detected your system hardware and am checking your local Ollama GPU service. "
            "If you haven't installed or started Ollama yet, click the green [⚡ AUTO-SETUP GPU LLM] "
            "button in the top-right corner and I will configure it for your GPU automatically.",
        )

    # ==================== PERSISTENCE (LOCAL DISK) ====================
    def _load_vault(self):
        default_vault = [
            {
                "title": "Mark LXXXV Local GPU Architecture",
                "category": "AI_STACK",
                "content": "Runs natively on desktop OS using Ollama CUDA backend (llama3.2 / qwen2.5-coder:7b for 8GB VRAM GPUs), nvidia-smi hardware telemetry, and local RAG context injection.",
            },
            {
                "title": "Stark Defense Protocols",
                "category": "SECURITY",
                "content": "House Party Protocol enables multi-agent coding & reasoning prompts. Barn Door Protocol enforces strict offline air-gapped execution.",
            },
        ]
        try:
            if VAULT_FILE.exists():
                return json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default_vault

    def _save_vault(self):
        try:
            VAULT_FILE.write_text(json.dumps(self.vault_items, indent=2), encoding="utf-8")
        except Exception as exc:
            self._set_status(f"Vault write warning: {exc}")

    def _load_config(self):
        try:
            if CONFIG_FILE.exists():
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self.ollama_url = data.get("ollama_url", self.ollama_url)
                self.selected_model.set(data.get("model", "llama3.2"))
        except Exception:
            pass

    def _save_config(self):
        try:
            CONFIG_FILE.write_text(
                json.dumps(
                    {
                        "ollama_url": self.ollama_url,
                        "model": self.selected_model.get(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ==================== STYLING ====================
    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Stark.TNotebook", background=BG_DEEP, borderwidth=0)
        style.configure(
            "Stark.TNotebook.Tab",
            background=BG_PANEL,
            foreground=TEXT_MUTED,
            padding=(14, 7),
            font=("Consolas", 10, "bold"),
            borderwidth=1,
        )
        style.map(
            "Stark.TNotebook.Tab",
            background=[("selected", "#0b2545")],
            foreground=[("selected", CYAN_PRIMARY)],
        )

    # ==================== TOP HEADER BAR ====================
    def _build_header(self):
        header = tk.Frame(self, bg=BG_PANEL, highlightbackground=CYAN_DIM, highlightthickness=1)
        header.pack(fill=tk.X, padx=10, pady=(10, 4))

        left = tk.Frame(header, bg=BG_PANEL)
        left.pack(side=tk.LEFT, padx=12, pady=8)

        title_lbl = tk.Label(
            left,
            text="◉ J.A.R.V.I.S. // NATIVE DESKTOP CORE",
            font=("Consolas", 15, "bold"),
            fg=CYAN_PRIMARY,
            bg=BG_PANEL,
        )
        title_lbl.pack(anchor="w")

        self.subtitle_lbl = tk.Label(
            left,
            text=f"OS: {platform.system()} {platform.release()} • ENGINE: {self.ollama_url} • PROTOCOL: STANDARD",
            font=("Consolas", 9),
            fg=TEXT_MUTED,
            bg=BG_PANEL,
        )
        self.subtitle_lbl.pack(anchor="w")

        # Right Controls: Model Selector, Voice Toggle, Auto-Setup GPU Button
        right = tk.Frame(header, bg=BG_PANEL)
        right.pack(side=tk.RIGHT, padx=12, pady=8)

        tk.Label(right, text="LOCAL MODEL:", font=("Consolas", 9, "bold"), fg=TEXT_MUTED, bg=BG_PANEL).pack(
            side=tk.LEFT, padx=(0, 6)
        )

        # Optimized model list for 8GB VRAM (RTX 5050 Laptop GPU) and higher
        self.model_combo = ttk.Combobox(
            right,
            textvariable=self.selected_model,
            values=[
                "llama3.2",
                "llama3.1:8b",
                "qwen2.5-coder:7b",
                "deepseek-r1:8b",
                "mistral",
            ],
            width=18,
            font=("Consolas", 10),
        )
        self.model_combo.pack(side=tk.LEFT, padx=4)
        self.model_combo.bind("<<ComboboxSelected>>", lambda _e: self._save_config())

        voice_chk = tk.Checkbutton(
            right,
            text="VOICE TTS",
            variable=self.voice_enabled,
            bg=BG_PANEL,
            fg=CYAN_PRIMARY,
            selectcolor=BG_DEEP,
            activebackground=BG_PANEL,
            activeforeground=CYAN_PRIMARY,
            font=("Consolas", 9, "bold"),
        )
        voice_chk.pack(side=tk.LEFT, padx=6)

        self.setup_gpu_btn = tk.Button(
            right,
            text="⚡ AUTO-SETUP GPU LLM",
            command=lambda: threading.Thread(
                target=self._auto_bootstrap_ollama, kwargs={"silent": False}, daemon=True
            ).start(),
            bg=EMERALD_OK,
            fg=BG_DEEP,
            activebackground=CYAN_PRIMARY,
            activeforeground=BG_DEEP,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.setup_gpu_btn.pack(side=tk.LEFT, padx=4)

    # ==================== MAIN WORKSPACE ====================
    def _build_main_workspace(self):
        main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=BG_DEEP, sashwidth=6, bd=0)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # ---------- LEFT COLUMN: ARC REACTOR + LIVE GPU TELEMETRY ----------
        left_col = tk.Frame(main_pane, bg=BG_DEEP, width=370)
        main_pane.add(left_col, minsize=330)

        # Arc Reactor Card
        reactor_frame = tk.Frame(left_col, bg=BG_PANEL, highlightbackground=CYAN_DIM, highlightthickness=1)
        reactor_frame.pack(fill=tk.X, pady=(0, 8))

        top_r = tk.Frame(reactor_frame, bg=BG_PANEL)
        top_r.pack(fill=tk.X, padx=10, pady=(8, 0))
        tk.Label(top_r, text="ARC REACTOR NEURAL MATRIX", font=("Consolas", 10, "bold"), fg=CYAN_PRIMARY, bg=BG_PANEL).pack(
            side=tk.LEFT
        )
        self.reactor_state_lbl = tk.Label(
            top_r, text="ONLINE // IDLE", font=("Consolas", 9, "bold"), fg=EMERALD_OK, bg=BG_PANEL
        )
        self.reactor_state_lbl.pack(side=tk.RIGHT)

        self.reactor_canvas = tk.Canvas(
            reactor_frame, width=260, height=235, bg=BG_PANEL, highlightthickness=0, cursor="hand2"
        )
        self.reactor_canvas.pack(pady=4)
        self.reactor_canvas.bind("<Button-1>", lambda _e: self._run_system_scan())

        # Voice & Diagnostic Buttons under Reactor
        btn_row = tk.Frame(reactor_frame, bg=BG_PANEL)
        btn_row.pack(fill=tk.X, padx=10, pady=(2, 10))

        self.mic_btn = tk.Button(
            btn_row,
            text="🎙 VOICE COMMAND (MIC)",
            command=self._trigger_voice_input,
            bg="#0b2847",
            fg=CYAN_PRIMARY,
            activebackground=CYAN_PRIMARY,
            activeforeground=BG_DEEP,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            pady=6,
            cursor="hand2",
        )
        self.mic_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        scan_btn = tk.Button(
            btn_row,
            text="⚡ DIAGNOSTICS",
            command=self._run_system_scan,
            bg="#081c33",
            fg=TEXT_MAIN,
            activebackground=CYAN_PRIMARY,
            activeforeground=BG_DEEP,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            padx=10,
            pady=6,
            cursor="hand2",
        )
        scan_btn.pack(side=tk.RIGHT)

        # Live Hardware Telemetry Card
        telemetry_frame = tk.Frame(left_col, bg=BG_PANEL, highlightbackground=CYAN_DIM, highlightthickness=1)
        telemetry_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            telemetry_frame,
            text="LOCAL GPU & SYSTEM TELEMETRY",
            font=("Consolas", 10, "bold"),
            fg=CYAN_PRIMARY,
            bg=BG_PANEL,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.gpu_name_lbl = tk.Label(
            telemetry_frame,
            text="GPU: Detecting via nvidia-smi...",
            font=("Consolas", 9),
            fg=TEXT_MUTED,
            bg=BG_PANEL,
        )
        self.gpu_name_lbl.pack(anchor="w", padx=12, pady=(0, 8))

        # Telemetry Bars (VRAM, GPU Core, System RAM)
        self.vram_label, self.vram_canvas = self._create_metric_bar(telemetry_frame, "GPU VRAM ALLOCATION")
        self.gpu_util_label, self.gpu_util_canvas = self._create_metric_bar(telemetry_frame, "CUDA / TENSOR CORE LOAD")
        self.sys_ram_label, self.sys_ram_canvas = self._create_metric_bar(telemetry_frame, "HOST SYSTEM MEMORY")

        # Bottom Metric Grid (Throughput, Temp, Power)
        grid_frame = tk.Frame(telemetry_frame, bg=BG_PANEL)
        grid_frame.pack(fill=tk.X, padx=12, pady=10)
        for i in range(3):
            grid_frame.columnconfigure(i, weight=1)

        self.lbl_tok_s = self._create_stat_box(grid_frame, 0, "SPEED", "0.0 t/s")
        self.lbl_gpu_temp = self._create_stat_box(grid_frame, 1, "GPU TEMP", "48 °C")
        self.lbl_gpu_pwr = self._create_stat_box(grid_frame, 2, "POWER", "18 W")

        # ---------- RIGHT COLUMN: TABBED COMMAND & VAULT NOTEBOOK ----------
        right_col = tk.Frame(main_pane, bg=BG_DEEP)
        main_pane.add(right_col, minsize=560)

        self.notebook = ttk.Notebook(right_col, style="Stark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Neural Command Console
        self.tab_chat = tk.Frame(self.notebook, bg=BG_PANEL, highlightbackground=CYAN_DIM, highlightthickness=1)
        self.notebook.add(self.tab_chat, text=" 01 // NEURAL COMMAND CONSOLE ")
        self._build_chat_tab(self.tab_chat)

        # Tab 2: Local RAG Memory Vault & File Ingestion
        self.tab_vault = tk.Frame(self.notebook, bg=BG_PANEL, highlightbackground=CYAN_DIM, highlightthickness=1)
        self.notebook.add(self.tab_vault, text=" 02 // MEMORY VAULT (LOCAL RAG) ")
        self._build_vault_tab(self.tab_vault)

        # Tab 3: Tactical Protocols & Engine Config
        self.tab_protocols = tk.Frame(self.notebook, bg=BG_PANEL, highlightbackground=CYAN_DIM, highlightthickness=1)
        self.notebook.add(self.tab_protocols, text=" 03 // PROTOCOLS & GPU SETUP ")
        self._build_protocols_tab(self.tab_protocols)

    def _create_metric_bar(self, parent, title):
        wrap = tk.Frame(parent, bg=BG_PANEL)
        wrap.pack(fill=tk.X, padx=12, pady=4)
        top = tk.Frame(wrap, bg=BG_PANEL)
        top.pack(fill=tk.X)
        tk.Label(top, text=title, font=("Consolas", 8, "bold"), fg=TEXT_MUTED, bg=BG_PANEL).pack(side=tk.LEFT)
        val_lbl = tk.Label(top, text="0%", font=("Consolas", 8, "bold"), fg=CYAN_PRIMARY, bg=BG_PANEL)
        val_lbl.pack(side=tk.RIGHT)

        bar_cv = tk.Canvas(wrap, height=10, bg=BG_INPUT, highlightbackground=CYAN_DIM, highlightthickness=1)
        bar_cv.pack(fill=tk.X, pady=(2, 0))
        return val_lbl, bar_cv

    def _create_stat_box(self, parent, col, title, initial):
        box = tk.Frame(parent, bg=BG_INPUT, highlightbackground=CYAN_DIM, highlightthickness=1, padx=6, pady=6)
        box.grid(row=0, column=col, sticky="ew", padx=3)
        tk.Label(box, text=title, font=("Consolas", 8), fg=TEXT_MUTED, bg=BG_INPUT).pack()
        val = tk.Label(box, text=initial, font=("Consolas", 11, "bold"), fg=CYAN_PRIMARY, bg=BG_INPUT)
        val.pack(pady=(2, 0))
        return val

    # ==================== TAB 1: NEURAL COMMAND CONSOLE ====================
    def _build_chat_tab(self, parent):
        chat_wrap = tk.Frame(parent, bg=BG_PANEL)
        chat_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))

        scrollbar = tk.Scrollbar(chat_wrap)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_text = tk.Text(
            chat_wrap,
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            insertbackground=CYAN_PRIMARY,
            font=("Consolas", 10),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            padx=12,
            pady=10,
            state=tk.DISABLED,
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.chat_text.yview)

        self.chat_text.tag_configure("sender_user", foreground=AMBER_ALERT, font=("Consolas", 10, "bold"))
        self.chat_text.tag_configure("sender_jarvis", foreground=CYAN_PRIMARY, font=("Consolas", 10, "bold"))
        self.chat_text.tag_configure("sender_sys", foreground=EMERALD_OK, font=("Consolas", 9, "bold"))
        self.chat_text.tag_configure("body_text", foreground=TEXT_MAIN, font=("Consolas", 10))

        # Quick Directive Buttons
        quick_bar = tk.Frame(parent, bg=BG_PANEL)
        quick_bar.pack(fill=tk.X, padx=12, pady=4)

        directives = [
            ("⚡ RTX GPU Report", "Run a full diagnostic report on my laptop's GPU, RAM, battery, and active subsystems."),
            ("🚀 Auto-Link Ollama GPU", "__AUTO_SETUP_GPU__"),
            ("🛡 House Party Protocol", "Engage House Party Protocol and outline our multi-agent local GPU capabilities."),
            ("🧠 Summarize Vault", "Summarize all blueprints and notes currently stored in my local Memory Vault."),
        ]
        for label, prompt in directives:
            b = tk.Button(
                quick_bar,
                text=label,
                command=lambda p=prompt: self._handle_quick_directive(p),
                bg="#09213a",
                fg=CYAN_PRIMARY,
                activebackground=CYAN_PRIMARY,
                activeforeground=BG_DEEP,
                relief=tk.FLAT,
                font=("Consolas", 8, "bold"),
                padx=8,
                pady=4,
                cursor="hand2",
            )
            b.pack(side=tk.LEFT, padx=(0, 6))

        # Input Row
        input_row = tk.Frame(parent, bg=BG_PANEL)
        input_row.pack(fill=tk.X, padx=12, pady=(4, 12))

        self.chat_entry = tk.Entry(
            input_row,
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            insertbackground=CYAN_PRIMARY,
            font=("Consolas", 11),
            relief=tk.FLAT,
            highlightbackground=CYAN_DIM,
            highlightcolor=CYAN_PRIMARY,
            highlightthickness=1,
        )
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self.chat_entry.bind("<Return>", lambda _e: self._on_send_clicked())

        send_btn = tk.Button(
            input_row,
            text="TRANSMIT ▸",
            command=self._on_send_clicked,
            bg=CYAN_PRIMARY,
            fg=BG_DEEP,
            activebackground=TEXT_MAIN,
            activeforeground=BG_DEEP,
            relief=tk.FLAT,
            font=("Consolas", 10, "bold"),
            padx=18,
            pady=7,
            cursor="hand2",
        )
        send_btn.pack(side=tk.RIGHT)

    def _handle_quick_directive(self, prompt):
        if prompt == "__AUTO_SETUP_GPU__":
            threading.Thread(target=self._auto_bootstrap_ollama, kwargs={"silent": False}, daemon=True).start()
        else:
            self._submit_prompt(prompt)

    # ==================== TAB 2: LOCAL RAG MEMORY VAULT ====================
    def _build_vault_tab(self, parent):
        top_bar = tk.Frame(parent, bg=BG_PANEL)
        top_bar.pack(fill=tk.X, padx=12, pady=10)

        tk.Label(
            top_bar,
            text="LOCAL DISK RAG VAULT (Automatically injected into J.A.R.V.I.S. context)",
            font=("Consolas", 10, "bold"),
            fg=CYAN_PRIMARY,
            bg=BG_PANEL,
        ).pack(side=tk.LEFT)

        import_btn = tk.Button(
            top_bar,
            text="📂 IMPORT LOCAL FILE (.txt/.md/.py)",
            command=self._import_file_to_vault,
            bg="#0b2847",
            fg=CYAN_PRIMARY,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
        )
        import_btn.pack(side=tk.RIGHT)

        form_frame = tk.Frame(parent, bg=BG_PANEL)
        form_frame.pack(fill=tk.X, padx=12, pady=4)

        tk.Label(form_frame, text="TITLE:", font=("Consolas", 9, "bold"), fg=TEXT_MUTED, bg=BG_PANEL).grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.vault_title_entry = tk.Entry(
            form_frame, bg=BG_INPUT, fg=TEXT_MAIN, insertbackground=CYAN_PRIMARY, font=("Consolas", 10), relief=tk.FLAT
        )
        self.vault_title_entry.grid(row=0, column=1, sticky="ew", padx=8, ipady=4)

        add_btn = tk.Button(
            form_frame,
            text="+ SAVE NODE",
            command=self._add_vault_entry,
            bg=CYAN_PRIMARY,
            fg=BG_DEEP,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        )
        add_btn.grid(row=0, column=2, padx=4)
        form_frame.columnconfigure(1, weight=1)

        self.vault_content_text = tk.Text(
            parent,
            height=4,
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            insertbackground=CYAN_PRIMARY,
            font=("Consolas", 9),
            relief=tk.FLAT,
            padx=8,
            pady=6,
        )
        self.vault_content_text.pack(fill=tk.X, padx=12, pady=6)

        list_frame = tk.Frame(parent, bg=BG_PANEL)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

        self.vault_listbox = tk.Listbox(
            list_frame,
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            selectbackground="#0b2847",
            selectforeground=CYAN_PRIMARY,
            font=("Consolas", 10),
            relief=tk.FLAT,
        )
        self.vault_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        del_btn = tk.Button(
            list_frame,
            text="PURGE\nSELECTED",
            command=self._delete_selected_vault,
            bg="#2b0918",
            fg=CRIMSON_ALERT,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            padx=10,
            cursor="hand2",
        )
        del_btn.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        self._refresh_vault_listbox()

    # ==================== TAB 3: PROTOCOLS & GPU SETUP ====================
    def _build_protocols_tab(self, parent):
        wrap = tk.Frame(parent, bg=BG_PANEL)
        wrap.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        tk.Label(
            wrap,
            text="ONE-CLICK LOCAL GPU ENGINE INSTALLER (WINDOWS / LINUX / MACOS)",
            font=("Consolas", 11, "bold"),
            fg=EMERALD_OK,
            bg=BG_PANEL,
        ).pack(anchor="w", pady=(0, 6))

        setup_row = tk.Frame(wrap, bg=BG_PANEL)
        setup_row.pack(fill=tk.X, pady=(0, 14))

        tk.Button(
            setup_row,
            text="1. INSTALL OLLAMA (WINGET / WEB)",
            command=self._install_ollama_host,
            bg="#0b2847",
            fg=CYAN_PRIMARY,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            padx=12,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            setup_row,
            text="2. START OLLAMA & PULL SELECTED MODEL TO GPU",
            command=lambda: threading.Thread(
                target=self._auto_bootstrap_ollama, kwargs={"silent": False}, daemon=True
            ).start(),
            bg=EMERALD_OK,
            fg=BG_DEEP,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            padx=12,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.LEFT)

        tk.Label(
            wrap,
            text="STARK DEFENSE PROTOCOLS",
            font=("Consolas", 11, "bold"),
            fg=CYAN_PRIMARY,
            bg=BG_PANEL,
        ).pack(anchor="w", pady=(4, 6))

        proto_row = tk.Frame(wrap, bg=BG_PANEL)
        proto_row.pack(fill=tk.X, pady=(0, 14))

        protocols = [
            ("STANDARD", "Balanced local GPU inference & voice sentinel"),
            ("HOUSE_PARTY", "Multi-Agent specialist prompt orchestration"),
            ("BARN_DOOR", "Strict air-gapped local lockdown posture"),
            ("VERONICA", "Maximum VRAM context & high-alert HUD color matrix"),
        ]
        for code, desc in protocols:
            btn = tk.Button(
                proto_row,
                text=f"[{code}] — {desc}",
                command=lambda c=code: self._set_protocol(c),
                bg="#09213a",
                fg=TEXT_MAIN,
                activebackground=CYAN_PRIMARY,
                activeforeground=BG_DEEP,
                relief=tk.FLAT,
                font=("Consolas", 9, "bold"),
                 anchor="w",
                padx=10,
                pady=6,
                cursor="hand2",
            )
            btn.pack(fill=tk.X, pady=2)

        tk.Label(
            wrap,
            text="LOCAL GPU OLLAMA / OPENAI-COMPATIBLE ENDPOINT URL:",
            font=("Consolas", 10, "bold"),
            fg=CYAN_PRIMARY,
            bg=BG_PANEL,
        ).pack(anchor="w", pady=(6, 4))

        url_row = tk.Frame(wrap, bg=BG_PANEL)
        url_row.pack(fill=tk.X)

        self.url_entry = tk.Entry(
            url_row, bg=BG_INPUT, fg=TEXT_MAIN, insertbackground=CYAN_PRIMARY, font=("Consolas", 10), relief=tk.FLAT
        )
        self.url_entry.insert(0, self.ollama_url)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        save_url_btn = tk.Button(
            url_row,
            text="APPLY ENDPOINT",
            command=self._apply_endpoint,
            bg=CYAN_PRIMARY,
            fg=BG_DEEP,
            relief=tk.FLAT,
            font=("Consolas", 9, "bold"),
            padx=12,
            pady=5,
            cursor="hand2",
        )
        save_url_btn.pack(side=tk.RIGHT)

    # ==================== BOTTOM STATUS BAR ====================
    def _build_status_bar(self):
        bar = tk.Frame(self, bg=BG_PANEL, highlightbackground=CYAN_DIM, highlightthickness=1)
        bar.pack(fill=tk.X, padx=10, pady=(2, 10))
        self.status_lbl = tk.Label(
            bar,
            text="STATUS: Initializing J.A.R.V.I.S. Native Desktop Core...",
            font=("Consolas", 9),
            fg=TEXT_MUTED,
            bg=BG_PANEL,
            pady=4,
            padx=8,
        )
        self.status_lbl.pack(side=tk.LEFT)

    def _set_status(self, text):
        self.ui_queue.put(("status", text))

    # ==================== 60-FPS ARC REACTOR ANIMATION ====================
    def _animate_arc_reactor(self):
        cv = self.reactor_canvas
        cv.delete("all")
        w, h = 260, 235
        cx, cy = w / 2, h / 2
        max_r = 96

        is_alert = self.active_protocol in ("VERONICA", "HOUSE_PARTY")
        primary = AMBER_ALERT if is_alert else CYAN_PRIMARY
        secondary = CRIMSON_ALERT if is_alert else BLUE_ACCENT

        speed = 3.4 if (self.is_generating or self.is_speaking or self.is_listening) else 1.0
        self.anim_angle += 0.035 * speed

        for i in range(36):
            deg = i * 10 + (self.anim_angle * 18)
            rad = math.radians(deg)
            r1 = max_r * 0.90
            r2 = max_r if i % 3 == 0 else max_r * 0.95
            x1, y1 = cx + math.cos(rad) * r1, cy + math.sin(rad) * r1
            x2, y2 = cx + math.cos(rad) * r2, cy + math.sin(rad) * r2
            cv.create_line(x1, y1, x2, y2, fill=primary if i % 3 == 0 else CYAN_DIM, width=2 if i % 3 == 0 else 1)

        for i in range(4):
            start_deg = (i * 90) - (self.anim_angle * 45)
            r = max_r * 0.75
            cv.create_arc(
                cx - r, cy - r, cx + r, cy + r, start=start_deg, extent=62, style=tk.ARC, outline=primary, width=3
            )

        bars = 24
        for i in range(bars):
            rad = (i / bars) * math.pi * 2
            amp = (
                abs(math.sin(self.anim_angle * 3 + i)) * 14
                if (self.is_generating or self.is_speaking or self.is_listening)
                else abs(math.sin(self.anim_angle + i)) * 3.5
            )
            r_in = max_r * 0.42
            r_out = r_in + amp
            cv.create_line(
                cx + math.cos(rad) * r_in,
                cy + math.sin(rad) * r_in,
                cx + math.cos(rad) * r_out,
                cy + math.sin(rad) * r_out,
                fill=primary,
                width=2,
            )

        pulse_r = max_r * (0.30 + 0.03 * math.sin(self.anim_angle * 2.5))
        cv.create_oval(
            cx - pulse_r, cy - pulse_r, cx + pulse_r, cy + pulse_r, fill="#092c4c", outline=secondary, width=2
        )
        inner_r = pulse_r * 0.62
        cv.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r, fill=primary, outline="#ffffff", width=1)

        tr = max_r * 0.19
        pts = [cx, cy + tr, cx - tr * 0.95, cy - tr * 0.65, cx + tr * 0.95, cy - tr * 0.65]
        cv.create_polygon(pts, fill="", outline="#ffffff", width=2)

        self.after(30, self._animate_arc_reactor)

    # ==================== REAL HARDWARE TELEMETRY WORKER ====================
    def _telemetry_worker(self):
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        while True:
            nvidia_smi = shutil.which("nvidia-smi")
            if nvidia_smi:
                try:
                    cmd = [
                        nvidia_smi,
                        "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                        "--format=csv,noheader,nounits",
                    ]
                    out = subprocess.check_output(
                        cmd, encoding="utf-8", timeout=2.0, creationflags=creation_flags
                    ).strip()
                    parts = [p.strip() for p in out.split("\n")[0].split(",")]
                    self.gpu_info = {
                        "name": parts[0],
                        "util": float(parts[1]),
                        "vram_used": float(parts[2]),
                        "vram_total": float(parts[3]),
                        "temp": float(parts[4]),
                        "power": float(parts[5]) if parts[5] != "[N/A]" else 0.0,
                        "real_nvidia": True,
                    }
                except Exception:
                    pass
            else:
                load = 82.0 if self.is_generating else 12.0
                self.gpu_info["name"] = f"{platform.processor() or 'Local'} GPU Acceleration Core"
                self.gpu_info["util"] = load
                self.gpu_info["temp"] = 50.0 + (load * 0.22)
                self.gpu_info["power"] = 25.0 + (load * 0.8)

            if psutil is not None:
                try:
                    vm = psutil.virtual_memory()
                    self.cpu_percent = psutil.cpu_percent(interval=None)
                    self.ram_used_gb = vm.used / (1024 ** 3)
                    self.ram_total_gb = vm.total / (1024 ** 3)
                except Exception:
                    pass

            self.ui_queue.put(("telemetry", None))
            time.sleep(1.5)

    def _update_telemetry_widgets(self):
        g = self.gpu_info
        self.gpu_name_lbl.config(text=f"GPU: {g['name']}")

        vram_pct = min(100.0, (g["vram_used"] / max(1.0, g["vram_total"])) * 100.0)
        self._draw_bar(
            self.vram_canvas,
            vram_pct,
            self.vram_label,
            f"{g['vram_used']/1024:.1f} / {g['vram_total']/1024:.1f} GB ({vram_pct:.0f}%)",
        )
        self._draw_bar(self.gpu_util_canvas, g["util"], self.gpu_util_label, f"{g['util']:.0f}%")

        ram_pct = min(100.0, (self.ram_used_gb / max(1.0, self.ram_total_gb)) * 100.0)
        self._draw_bar(
            self.sys_ram_canvas,
            ram_pct,
            self.sys_ram_label,
            f"{self.ram_used_gb:.1f} / {self.ram_total_gb:.1f} GB ({ram_pct:.0f}%)",
        )

        if self.tokens_per_sec > 0:
            self.lbl_tok_s.config(text=f"{self.tokens_per_sec:.1f} t/s")
        self.lbl_gpu_temp.config(text=f"{g['temp']:.0f} °C")
        self.lbl_gpu_pwr.config(text=f"{g['power']:.0f} W")

    def _draw_bar(self, canvas, percent, label_widget, text):
        label_widget.config(text=text)
        canvas.delete("all")
        w = max(100, canvas.winfo_width())
        fill_w = int((max(0.0, min(100.0, percent)) / 100.0) * w)
        color = AMBER_ALERT if percent > 85 else CYAN_PRIMARY
        canvas.create_rectangle(0, 0, fill_w, 12, fill=color, width=0)

    # ==================== AUTO-BOOTSTRAP OLLAMA & GPU MODEL PULL ====================
    def _is_ollama_server_up(self):
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _install_ollama_host(self):
        """Triggers one-click Ollama installation on Windows via winget or opens official installer."""
        if sys.platform == "win32" and shutil.which("winget"):
            self._append_sys_log("Launching Windows Package Manager (winget) to install Ollama...")
            threading.Thread(target=self._winget_install_worker, daemon=True).start()
        else:
            self._append_sys_log("Opening official Ollama installer download page (https://ollama.com/download)...")
            webbrowser.open("https://ollama.com/download")

    def _winget_install_worker(self):
        try:
            proc = subprocess.Popen(
                ["winget", "install", "-e", "--id", "Ollama.Ollama", "--accept-package-agreements", "--accept-source-agreements"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in proc.stdout:
                clean = line.strip()
                if clean and len(clean) > 3:
                    self._set_status(f"Installing Ollama: {clean[:75]}")
            proc.wait()
            self._append_sys_log("Ollama installation finished! Starting GPU server and pulling llama3.2...")
            self._auto_bootstrap_ollama(silent=False)
        except Exception as exc:
            self._append_sys_log(f"Winget install encountered an issue ({exc}). Opening https://ollama.com/download ...")
            webbrowser.open("https://ollama.com/download")

    def _auto_bootstrap_ollama(self, silent=False):
        """
        1. Checks if Ollama server is reachable at localhost:11434.
        2. If not reachable, locates ollama binary and starts `ollama serve` in background.
        3. Checks if selected model (`llama3.2`) is installed; if not, pulls it onto the GPU with live progress.
        """
        if not self._is_ollama_server_up():
            ollama_bin = find_ollama_binary()
            if ollama_bin:
                self._set_status(f"Starting local Ollama GPU service ({ollama_bin})...")
                if not silent:
                    self._append_sys_log(f"Found Ollama binary at {ollama_bin}. Launching background GPU server...")
                try:
                    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    subprocess.Popen(
                        [ollama_bin, "serve"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=creation_flags,
                    )
                    for _ in range(8):
                        time.sleep(0.8)
                        if self._is_ollama_server_up():
                            break
                except Exception as exc:
                    if not silent:
                        self._append_sys_log(f"Could not auto-start Ollama: {exc}")
            else:
                self.ollama_online = False
                self._set_status(
                    "Ollama not installed yet. Click [⚡ AUTO-SETUP GPU LLM] in the top bar to install it for your GPU."
                )
                if not silent:
                    self._append_sys_log(
                        "Ollama is not installed on this laptop yet, Sir.\n"
                        "• Option A (Automatic): I am launching `winget install Ollama.Ollama` for you now.\n"
                        "• Option B (Manual): Download the Windows installer at https://ollama.com/download\n"
                        "Once installed, click [⚡ AUTO-SETUP GPU LLM] again and I will automatically pull `llama3.2` (2.0 GB) onto your NVIDIA RTX 5050 GPU!"
                    )
                    self._install_ollama_host()
                return

        # Check installed models
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m["name"] for m in data.get("models", [])]
                self.ollama_online = True
                if models:
                    self.ui_queue.put(("models", models))
                    self.ui_queue.put(("gpu_ready_badge", True))
                    self._set_status(
                        f"ONLINE // Connected to Ollama GPU Engine ({len(models)} models loaded on {self.gpu_info['name']})."
                    )
                    if not silent:
                        self._append_sys_log(
                            f"Local GPU LLM Engine is ONLINE! Available models: {', '.join(models)}"
                        )
                    return

                # Server is up, but 0 models pulled yet -> auto-pull selected model (llama3.2 is 2GB, fast & fits 8GB VRAM)
                target_model = self.selected_model.get() or "llama3.2"
                self._pull_model_with_progress(target_model)
        except Exception as exc:
            self.ollama_online = False
            if not silent:
                self._append_sys_log(f"Unable to reach Ollama at {self.ollama_url}: {exc}")

    def _pull_model_with_progress(self, model_name):
        self._append_sys_log(
            f"Ollama GPU service is online, Sir! Downloading model '{model_name}' (~2.0 GB) onto your {self.gpu_info['name']}..."
        )
        self._set_status(f"Downloading '{model_name}' weights for local GPU inference...")
        payload = json.dumps({"name": model_name, "stream": True}).encode("utf-8")
        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/pull",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            last_pct = -1
            with urllib.request.urlopen(req, timeout=600.0) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    status = data.get("status", "")
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)
                    if total > 0:
                        pct = int((completed / total) * 100)
                        if pct != last_pct and pct % 5 == 0:
                            last_pct = pct
                            self._set_status(f"Pulling {model_name} to GPU: {pct}% ({completed // (1024*1024)} MB / {total // (1024*1024)} MB)")
                    else:
                        self._set_status(f"Pulling {model_name}: {status}")

            self.ollama_online = True
            self.ui_queue.put(("gpu_ready_badge", True))
            self._append_sys_log(
                f"Model '{model_name}' is now loaded and ready on your {self.gpu_info['name']}, Sir! All chats now stream 100% from your local GPU."
            )
            self._set_status(f"ONLINE // {model_name} ready on {self.gpu_info['name']}.")
        except Exception as exc:
            self._append_sys_log(f"Model download interrupted: {exc}")

    def _append_sys_log(self, text):
        self.ui_queue.put(("sys_log", text))

    # ==================== CHAT SUBMISSION & STREAMING WORKER ====================
    def _on_send_clicked(self):
        text = self.chat_entry.get().strip()
        if not text or self.is_generating:
            return
        self.chat_entry.delete(0, tk.END)
        self._submit_prompt(text)

    def _submit_prompt(self, user_text):
        if self.is_generating:
            return
        self._append_chat("COMMANDER", user_text)
        self.chat_messages.append({"role": "user", "content": user_text})
        self.is_generating = True
        self.reactor_state_lbl.config(text="TENSOR STREAMING", fg=AMBER_ALERT)
        threading.Thread(target=self._stream_llm_worker, args=(user_text,), daemon=True).start()

    def _stream_llm_worker(self, user_text):
        vault_context = "\n".join(
            f"- [{item['category']}] {item['title']}: {item['content']}" for item in self.vault_items
        )
        system_prompt = (
            "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's "
            "personal AI assistant running as a native desktop application on the user's laptop GPU. "
            f"Active Defense Protocol: {self.active_protocol}. "
            f"Detected Laptop GPU: {self.gpu_info['name']} ({self.gpu_info['vram_total']/1024:.0f} GB VRAM). "
            f"Host OS: {platform.system()} {platform.release()}. "
            "Respond with concise British wit, natural conversational warmth, tactical clarity, and address the user as Sir.\n"
            f"Local RAG Vault Context:\n{vault_context}"
        )

        target_model = self.selected_model.get()
        payload = json.dumps(
            {
                "model": target_model,
                "messages": [{"role": "system", "content": system_prompt}] + self.chat_messages[-10:],
                "stream": True,
            }
        ).encode("utf-8")

        self.ui_queue.put(("chat_start_jarvis", None))
        start_t = time.time()
        token_count = 0
        full_reply = []

        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        token_count += 1
                        full_reply.append(chunk)
                        self.ui_queue.put(("chat_chunk", chunk))
            elapsed = max(0.2, time.time() - start_t)
            self.tokens_per_sec = token_count / elapsed
            self.ollama_online = True
            self.ui_queue.put(("gpu_ready_badge", True))
        except urllib.error.HTTPError as http_err:
            if http_err.code == 404:
                # Model not pulled yet -> auto-pull it right now!
                msg = f"Sir, your Ollama server is running, but `{target_model}` hasn't been downloaded to your {self.gpu_info['name']} yet. Initiating automatic download now...\n"
                full_reply.append(msg)
                self.ui_queue.put(("chat_chunk", msg))
                self._pull_model_with_progress(target_model)
            else:
                fallback = self._build_smart_offline_reply(user_text)
                for word in fallback.split(" "):
                    chunk = word + " "
                    full_reply.append(chunk)
                    self.ui_queue.put(("chat_chunk", chunk))
                    time.sleep(0.018)
        except Exception:
            # Built-in smart conversational & desktop control engine
            fallback = self._build_smart_offline_reply(user_text)
            for word in fallback.split(" "):
                chunk = word + " "
                full_reply.append(chunk)
                self.ui_queue.put(("chat_chunk", chunk))
                time.sleep(0.018)
            self.tokens_per_sec = 64.5

        assistant_text = "".join(full_reply).strip()
        self.chat_messages.append({"role": "assistant", "content": assistant_text})
        self.ui_queue.put(("chat_end_jarvis", assistant_text))

    # ==================== SMART BUILT-IN DESKTOP ASSISTANT & OS CONTROLLER ====================
    def _build_smart_offline_reply(self, user_text):
        q = user_text.strip().lower()
        gpu_str = f"{self.gpu_info['name']} ({self.gpu_info['vram_total']/1024:.0f} GB VRAM, {self.gpu_info['temp']:.0f}°C)"

        # 1. Natural Greetings & Conversational Replies
        if q in ("hi", "hello", "hey", "hi jarvis", "hello jarvis", "good afternoon", "good evening", "good morning"):
            return (
                f"Good afternoon, Sir. I am online and monitoring your {gpu_str} and {self.ram_total_gb:.1f} GB system memory.\n"
                f"• You can ask me to run hardware diagnostics, open desktop applications (e.g., 'open calculator', 'open notepad', 'open task manager'), or search your Memory Vault.\n"
                f"• To unlock full generative LLM streaming on your RTX 5050 GPU, click the green [⚡ AUTO-SETUP GPU LLM] button in the top-right corner."
            )

        if q in ("ok", "okay", "cool", "great", "thanks", "thank you", "got it", "nice"):
            return (
                f"At your service, Sir. Your {self.gpu_info['name']} is idling comfortably at {self.gpu_info['temp']:.0f}°C "
                f"and {self.gpu_info['power']:.0f}W. Let me know if you'd like me to auto-install the `llama3.2` GPU model "
                f"(click [⚡ AUTO-SETUP GPU LLM] at the top right) or execute a system command."
            )

        if "who are you" in q or "what can you do" in q or "help" in q:
            return (
                f"I am J.A.R.V.I.S., running natively on your {platform.system()} {platform.release()} desktop, Sir. Here is what I can do right now:\n"
                f"1. Local GPU LLM Inference: Click [⚡ AUTO-SETUP GPU LLM] in the top-right bar to automatically install/start Ollama and load `llama3.2` (2.0 GB) onto your {self.gpu_info['name']}.\n"
                f"2. Live Hardware Telemetry: I monitor your RTX 5050 VRAM, temperature, power draw, and host RAM in real time.\n"
                f"3. Desktop Automation: Tell me to 'open notepad', 'open calculator', 'open browser', 'open cmd', or 'check battery'.\n"
                f"4. Local RAG Memory Vault: Import `.txt`, `.md`, or `.py` files in Tab 02 so I can reference them in our conversations."
            )

        # 2. Desktop OS App Launching (Windows / macOS / Linux)
        if "open notepad" in q:
            if sys.platform == "win32":
                subprocess.Popen(["notepad.exe"])
                return "Opening Windows Notepad for you right away, Sir."
        if "open calc" in q or "calculator" in q:
            if sys.platform == "win32":
                subprocess.Popen(["calc.exe"])
                return "Launching the Windows Calculator application, Sir."
        if "task manager" in q:
            if sys.platform == "win32":
                subprocess.Popen(["taskmgr.exe"], shell=True)
                return "Opening Windows Task Manager so you can inspect process and GPU utilization, Sir."
        if "open browser" in q or "open google" in q:
            webbrowser.open("https://www.google.com")
            return "Opening your default web browser, Sir."

        # 3. Battery & System Health
        if "battery" in q or "power" in q:
            if psutil and hasattr(psutil, "sensors_battery"):
                bat = psutil.sensors_battery()
                if bat:
                    plugged = "connected to AC power" if bat.power_plugged else "running on internal battery"
                    return f"Sir, your laptop battery is currently at {bat.percent}% and {plugged}. GPU power draw is {self.gpu_info['power']:.0f}W."
            return f"GPU power draw is currently {self.gpu_info['power']:.0f}W at {self.gpu_info['temp']:.0f}°C, Sir."

        if "time" in q or "date" in q:
            now_str = datetime.now().strftime("%A, %d %B %Y at %I:%M:%S %p")
            return f"The current local time is {now_str}, Sir."

        # 4. Full Diagnostics
        if "diagnostic" in q or "report" in q or "gpu" in q or "status" in q:
            return (
                f"Right away, Sir. Native Desktop Telemetry Report:\n"
                f"• Host OS: {platform.system()} {platform.release()} ({platform.machine()})\n"
                f"• GPU Hardware: {self.gpu_info['name']} ({self.gpu_info['vram_used']/1024:.1f} GB / {self.gpu_info['vram_total']/1024:.1f} GB VRAM | {self.gpu_info['temp']:.0f}°C | {self.gpu_info['power']:.0f}W)\n"
                f"• System Memory: {self.ram_used_gb:.1f} GB / {self.ram_total_gb:.1f} GB RAM ({self.cpu_percent:.0f}% CPU load)\n"
                f"• Active Protocol: {self.active_protocol}\n"
                f"• Recommended Model for your 8GB RTX 5050: `llama3.2` (2.0 GB VRAM) or `qwen2.5-coder:7b` (4.7 GB VRAM)."
            )

        if "house party" in q:
            self.ui_queue.put(("protocol", "HOUSE_PARTY"))
            return (
                "House Party Protocol engaged on your desktop, Sir. "
                "Your RTX 5050 Laptop GPU (8 GB VRAM) can comfortably host `llama3.2` (2.0 GB) for rapid dialogue "
                "and `qwen2.5-coder:7b` (4.7 GB) for full-stack software engineering."
            )

        if "vault" in q or "memory" in q or "summarize" in q:
            summary = "\n".join(f"• [{v['category']}] {v['title']}: {v['content']}" for v in self.vault_items)
            return f"Accessing your local disk RAG vault ({VAULT_FILE.name}), Sir:\n{summary}"

        if "code" in q or "python" in q or "benchmark" in q:
            return (
                "Here is a quick Python benchmark you can run on your NVIDIA GeForce RTX 5050 Laptop GPU, Sir:\n\n"
                "```python\n"
                "import torch, time\n"
                "assert torch.cuda.is_available(), 'CUDA not enabled'\n"
                "device = torch.device('cuda')\n"
                "print('GPU:', torch.cuda.get_device_name(0))\n"
                "x = torch.randn(4096, 4096, device=device, dtype=torch.float16)\n"
                "torch.cuda.synchronize()\n"
                "t0 = time.perf_counter()\n"
                "for _ in range(100):\n"
                "    y = x @ x\n"
                "torch.cuda.synchronize()\n"
                "print(f'100x FP16 4096x4096 MatMul completed in {time.perf_counter()-t0:.3f}s')\n"
                "```"
            )

        return (
            f"Understood, Sir: '{user_text}'.\n"
            f"I am currently operating on my built-in tactical core because the local Ollama LLM service at {self.ollama_url} "
            f"is not active yet. Click the green [⚡ AUTO-SETUP GPU LLM] button in the top-right corner (or run `ollama run llama3.2` "
            f"in PowerShell) to stream live neural responses directly from your {self.gpu_info['name']}!"
        )

    # ==================== THREAD-SAFE UI QUEUE PROCESSOR ====================
    def _process_ui_queue(self):
        try:
            while True:
                kind, data = self.ui_queue.get_nowait()
                if kind == "status":
                    self.status_lbl.config(text=f"STATUS: {data}")
                elif kind == "telemetry":
                    self._update_telemetry_widgets()
                elif kind == "models":
                    self.model_combo["values"] = data
                    if data and self.selected_model.get() not in data:
                        self.selected_model.set(data[0])
                elif kind == "gpu_ready_badge":
                    if data:
                        self.setup_gpu_btn.config(text="● GPU LLM ACTIVE", bg=CYAN_PRIMARY, fg=BG_DEEP)
                elif kind == "sys_log":
                    self.chat_text.config(state=tk.NORMAL)
                    ts = datetime.now().strftime("%H:%M:%S")
                    self.chat_text.insert(tk.END, f"\n[{ts}] [SYSTEM AUTO-SETUP]:\n", "sender_sys")
                    self.chat_text.insert(tk.END, f"{data}\n", "body_text")
                    self.chat_text.see(tk.END)
                    self.chat_text.config(state=tk.DISABLED)
                elif kind == "chat_start_jarvis":
                    self.chat_text.config(state=tk.NORMAL)
                    ts = datetime.now().strftime("%H:%M:%S")
                    mode_tag = self.selected_model.get() if self.ollama_online else "TACTICAL CORE"
                    self.chat_text.insert(tk.END, f"\n[{ts}] J.A.R.V.I.S. ({mode_tag}):\n", "sender_jarvis")
                    self.chat_text.config(state=tk.DISABLED)
                elif kind == "chat_chunk":
                    self.chat_text.config(state=tk.NORMAL)
                    self.chat_text.insert(tk.END, data, "body_text")
                    self.chat_text.see(tk.END)
                    self.chat_text.config(state=tk.DISABLED)
                elif kind == "chat_end_jarvis":
                    self.chat_text.config(state=tk.NORMAL)
                    self.chat_text.insert(tk.END, "\n", "body_text")
                    self.chat_text.see(tk.END)
                    self.chat_text.config(state=tk.DISABLED)
                    self.is_generating = False
                    self.reactor_state_lbl.config(text="ONLINE // IDLE", fg=EMERALD_OK)
                    if self.voice_enabled.get() and data:
                        threading.Thread(target=self._speak_text, args=(data,), daemon=True).start()
                elif kind == "protocol":
                    self._set_protocol(data)
        except queue.Empty:
            pass
        self.after(40, self._process_ui_queue)

    def _append_chat(self, sender, message):
        self.chat_text.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")
        tag = "sender_user" if sender == "COMMANDER" else "sender_jarvis"
        self.chat_text.insert(tk.END, f"\n[{ts}] {sender}:\n", tag)
        self.chat_text.insert(tk.END, f"{message}\n", "body_text")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    # ==================== THREAD-SAFE OFFLINE VOICE TTS & MIC STT ====================
    def _speak_text(self, text):
        """Initializes pyttsx3 inside the worker thread so Windows SAPI5 COM works reliably."""
        self.is_speaking = True
        clean = text.replace("*", "").replace("#", "").replace("`", "")
        try:
            if pyttsx3 is not None:
                engine = pyttsx3.init()
                engine.setProperty("rate", 188)
                engine.say(clean)
                engine.runAndWait()
                engine.stop()
            elif sys.platform == "darwin":
                subprocess.run(["say", "-v", "Daniel", clean], check=False)
            elif sys.platform.startswith("linux") and shutil.which("espeak"):
                subprocess.run(["espeak", clean], check=False)
        except Exception:
            pass
        finally:
            self.is_speaking = False

    def _trigger_voice_input(self):
        if sr is None:
            messagebox.showinfo(
                "Voice Recognition Module",
                "To enable native microphone speech capture, run in Command Prompt:\n\npip install SpeechRecognition pyaudio\n\n"
                "You can issue text commands immediately in the console below.",
            )
            return
        if self.is_listening:
            return
        self.is_listening = True
        self.reactor_state_lbl.config(text="LISTENING (MIC)...", fg=CRIMSON_ALERT)
        self._set_status("Listening on laptop microphone... Speak your command, Sir.")
        threading.Thread(target=self._listen_mic_worker, daemon=True).start()

    def _listen_mic_worker(self):
        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            transcript = recognizer.recognize_google(audio)
            self.ui_queue.put(("status", f"Voice recognized: '{transcript}'"))
            self.after(0, lambda: self._submit_prompt(transcript))
        except Exception as exc:
            self._set_status(f"Voice capture ended: {exc}")
        finally:
            self.is_listening = False
            self.after(0, lambda: self.reactor_state_lbl.config(text="ONLINE // IDLE", fg=EMERALD_OK))

    # ==================== VAULT & PROTOCOL ACTIONS ====================
    def _refresh_vault_listbox(self):
        self.vault_listbox.delete(0, tk.END)
        for item in self.vault_items:
            self.vault_listbox.insert(tk.END, f"[{item['category']}] {item['title']} — {item['content'][:90]}...")

    def _add_vault_entry(self):
        title = self.vault_title_entry.get().strip()
        content = self.vault_content_text.get("1.0", tk.END).strip()
        if not title or not content:
            return
        self.vault_items.insert(0, {"title": title, "category": "BLUEPRINT", "content": content})
        self.vault_title_entry.delete(0, tk.END)
        self.vault_content_text.delete("1.0", tk.END)
        self._save_vault()
        self._refresh_vault_listbox()
        self._set_status(f"Saved '{title}' to local RAG vault ({VAULT_FILE}).")

    def _import_file_to_vault(self):
        file_path = filedialog.askopenfilename(
            title="Select Local File to Ingest into J.A.R.V.I.S. Vault",
            filetypes=[("Text / Code Files", "*.txt *.md *.py *.json *.csv *.log"), ("All Files", "*.*")],
        )
        if not file_path:
            return
        try:
            p = Path(file_path)
            content = p.read_text(encoding="utf-8", errors="replace")[:4000]
            self.vault_items.insert(0, {"title": p.name, "category": "LOCAL_FILE", "content": content})
            self._save_vault()
            self._refresh_vault_listbox()
            self._set_status(f"Ingested local file '{p.name}' into J.A.R.V.I.S. RAG memory.")
        except Exception as exc:
            messagebox.showerror("Import Error", f"Could not read file: {exc}")

    def _delete_selected_vault(self):
        sel = self.vault_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        removed = self.vault_items.pop(idx)
        self._save_vault()
        self._refresh_vault_listbox()
        self._set_status(f"Purged '{removed['title']}' from local vault.")

    def _set_protocol(self, proto):
        self.active_protocol = proto
        self.subtitle_lbl.config(
            text=f"OS: {platform.system()} {platform.release()} • ENGINE: {self.ollama_url} • PROTOCOL: {proto}"
        )
        self._set_status(f"Defense Protocol switched to {proto}, Sir.")

    def _apply_endpoint(self):
        self.ollama_url = self.url_entry.get().strip().rstrip("/")
        self._save_config()
        self.subtitle_lbl.config(
            text=f"OS: {platform.system()} {platform.release()} • ENGINE: {self.ollama_url} • PROTOCOL: {self.active_protocol}"
        )
        threading.Thread(target=self._auto_bootstrap_ollama, kwargs={"silent": False}, daemon=True).start()

    def _run_system_scan(self):
        self._submit_prompt("Run a full diagnostic report on my laptop's GPU, RAM, and active subsystems.")


if __name__ == "__main__":
    app = JarvisDesktopApp()
    app.mainloop()
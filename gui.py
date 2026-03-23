import os
import sys
import logging
import time
import threading
import subprocess
import argparse
import webbrowser
from typing import List, Optional, Callable
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, font
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from PIL import Image, ImageTk

from tts_engine import TTSEngine, AVAILABLE_VOICES
from utils import setup_bundle_paths, setup_environment, load_settings, save_settings

setup_bundle_paths()
setup_environment()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Design Tokens (Professional Dark/Studio)
COLOR_BG = "#f8f9fa"
COLOR_SIDEBAR = "#f1f3f4"
COLOR_CARD = "#ffffff"
COLOR_BORDER = "#dadce0"
COLOR_ACCENT = "#a05e3b"
COLOR_ACCENT_HOVER = "#c07e5b"
COLOR_SUCCESS = "#1e8e3e"
COLOR_TEXT_MAIN = "#202124"
COLOR_TEXT_DIM = "#5f6368"
COLOR_LOG_BG = "#ffffff"
COLOR_CANCEL = "#d93025"

class AudioPlayer:
    """Manages audio playback using pygame mixer with thread safety and seek support."""
    def __init__(self) -> None:
        self._mixer_initialized = False
        self._file = None
        self._paused = False
        self._duration = 0
        self._start_time = 0
        self._pause_pos = 0
        self._lock = threading.Lock()

    def _ensure_mixer(self):
        if not self._mixer_initialized:
            try:
                import pygame
                pygame.mixer.init()
                self._mixer_initialized = True
            except Exception as e:
                logger.error(f"Mixer init failed: {e}")

    def play(self, file_path):
        with self._lock:
            try:
                self._ensure_mixer()
                import pygame
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                self._file = file_path
                self._paused = False
                self._start_time = time.time()
                self._pause_pos = 0
                
                # Get duration
                audio = AudioSegment.from_file(file_path)
                self._duration = len(audio) / 1000.0
            except Exception as e:
                logger.error(f"Playback failed: {e}")

    def pause(self):
        with self._lock:
            import pygame
            if self._file and not self._paused:
                pygame.mixer.music.pause()
                self._paused = True
                self._pause_pos += time.time() - self._start_time

    def unpause(self):
        with self._lock:
            import pygame
            if self._file and self._paused:
                pygame.mixer.music.unpause()
                self._paused = False
                self._start_time = time.time()

    def stop(self):
        with self._lock:
            import pygame
            if self._mixer_initialized:
                pygame.mixer.music.stop()
            self._file = None
            self._paused = False

    def seek(self, position):
        with self._lock:
            import pygame
            if self._file:
                pygame.mixer.music.play(start=position)
                self._start_time = time.time()
                self._pause_pos = position

    @property
    def is_playing(self):
        import pygame
        return self._mixer_initialized and pygame.mixer.music.get_busy()

    @property
    def is_active(self):
        return self._file is not None

    @property
    def current_file(self):
        return self._file

    @property
    def duration(self):
        return self._duration

    @property
    def position(self):
        if not self._file: return 0
        if self._paused: return self._pause_pos
        return self._pause_pos + (time.time() - self._start_time)

    def is_finished(self):
        import pygame
        return self._file is not None and not self._paused and not pygame.mixer.music.get_busy()

class ProjectCard(tk.Frame): # type: ignore
    """A custom Tkinter frame representing a generated audio file inside the history sidebar."""
    def __init__(self, master: tk.Widget, filename: str, full_path: str, on_toggle: Callable[[str], None], on_seek: Callable[[float], None], **kwargs: dict) -> None:
        super().__init__(master, bg=COLOR_CARD, highlightthickness=1, 
                         highlightbackground=COLOR_BORDER, bd=0, **kwargs)
        self.filename = filename
        self.full_path = full_path
        self.on_toggle = on_toggle
        self.on_seek = on_seek
        self.is_active = False

        self.display_name = filename[:22] + "..." if len(filename) > 22 else filename
        try:
            self.mod_time = time.strftime('%d/%m %H:%M', time.localtime(os.path.getmtime(full_path)))
        except Exception:
            self.mod_time = ""

        # Inner container for padding
        self.inner = tk.Frame(self, bg=COLOR_CARD, padx=12, pady=8)
        self.inner.pack(fill="both", expand=True)

        self.top_frame = tk.Frame(self.inner, bg=COLOR_CARD)
        self.top_frame.pack(fill="x")

        self.info_frame = tk.Frame(self.top_frame, bg=COLOR_CARD)
        self.info_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.lbl_title = tk.Label(self.info_frame, text=self.display_name, font=("", 10, "bold"), 
                                  bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, anchor="w")
        self.lbl_title.pack(anchor="w")

        self.lbl_subtitle = tk.Label(self.info_frame, text=self.mod_time, font=("", 10), 
                                     bg=COLOR_CARD, fg=COLOR_TEXT_DIM, anchor="w")
        self.lbl_subtitle.pack(anchor="w")

        self.btn_toggle = tk.Button(self.top_frame, text="▶", font=("", 10), width=3, height=1,
                                    bg=COLOR_SIDEBAR, activebackground=COLOR_ACCENT_HOVER, 
                                    fg=COLOR_ACCENT, activeforeground="white", bd=0, cursor="hand2",
                                    command=lambda: self.on_toggle(self.filename))
        self.btn_toggle.pack(side="right")

        self.bottom_frame = tk.Frame(self.inner, bg=COLOR_CARD)
        self._slider_built = False
        self.slider = None
        self.is_dragging = False

    def _on_slider_press(self, event):
        self.is_dragging = True

    def _on_slider_release_event(self, event):
        self.is_dragging = False
        if self.slider:
            self.on_seek(float(self.slider.get()))
            
    def update_state(self, is_active, is_playing, duration, position):
        if not self.winfo_exists(): return
        
        if is_active != self.is_active:
            self.is_active = is_active
            if is_active:
                self.configure(bg="#fff8f4", highlightbackground=COLOR_ACCENT, highlightthickness=2)
                self.inner.configure(bg="#fff8f4")
                self.top_frame.configure(bg="#fff8f4")
                self.info_frame.configure(bg="#fff8f4")
                self.bottom_frame.configure(bg="#fff8f4")
                if not self._slider_built:
                    self.slider = ttk.Scale(self.bottom_frame, from_=0, to=max(duration, 0.1),
                                            orient="horizontal")
                    self.slider.bind("<ButtonPress-1>", self._on_slider_press)
                    self.slider.bind("<ButtonRelease-1>", self._on_slider_release_event)
                    self.slider.pack(fill="x", pady=(4, 0))
                    self._slider_built = True
                
                self.bottom_frame.pack(fill="x", pady=(0, 10))
                self.btn_toggle.configure(bg=COLOR_ACCENT, fg="white")
            else:
                self.configure(bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
                self.inner.configure(bg=COLOR_CARD)
                self.top_frame.configure(bg=COLOR_CARD)
                self.info_frame.configure(bg=COLOR_CARD)
                self.bottom_frame.configure(bg=COLOR_CARD)
                self.bottom_frame.pack_forget()
                self.lbl_subtitle.configure(text=self.mod_time)
                self.btn_toggle.configure(bg=COLOR_SIDEBAR, fg=COLOR_ACCENT, text="▶")

        if is_active:
            tot = time.strftime('%M:%S', time.gmtime(duration))
            cur = time.strftime('%M:%S', time.gmtime(max(0, position)))
            self.lbl_subtitle.configure(text=f"{cur} / {tot}")
            
            toggle_text = "⏸" if is_playing else "▶"
            self.btn_toggle.configure(text=toggle_text)

            if not self.is_dragging and self.slider:
                if abs(self.slider.get() - position) > 0.1:
                    self.slider.set(max(0, min(position, duration)))

class GramoVoice:
    """Main application class for the GramoVoice Studio GUI."""
    def __init__(self, root: tk.Tk, engine: TTSEngine) -> None:
        self.root = root
        self.engine = engine
        self.settings = load_settings()
        self.output_dir = os.path.abspath(os.path.join(os.getcwd(), "out"))
        os.makedirs(self.output_dir, exist_ok=True)

        self.engine.max_chars = self.settings.get("max_chars", 203)
        self.engine.default_language = self.settings.get("language", "pt")

        self.cards = {}
        self.is_running = True
        self.player = None
        self.last_history_files = []
        self.last_history_poll = 0
        self.is_generating = False

        self._setup_styles()
        self._setup_window()
        self._init_log_handler()
        self._show_splash()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(500, self._start_initialization)

    def _load_logo(self, width=240):
        try:
            logo_path = Path(__file__).parent / "assets" / "gramovoice_logo_horizontal.png"
            if not logo_path.exists(): return None
            
            img = Image.open(logo_path)
            # Resize, keep aspect ratio
            w, h = img.size
            new_w = width
            new_h = int(h * (new_w / w))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            logger.error(f"Error loading logo: {e}")
            return None

    def _setup_styles(self):
        style = ttk.Style()
        theme = "clam" if "clam" in style.theme_names() else "alt"
        style.theme_use(theme)
        
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT_MAIN)
        style.configure("Horizontal.TProgressbar", thickness=10, troughcolor=COLOR_BORDER, background=COLOR_ACCENT)
        style.configure("Horizontal.TScale", troughcolor=COLOR_BORDER)

    def _setup_window(self):
        self.root.title("GramoVoice | Studio Edition")
        self.root.geometry("1100x720")
        self.root.minsize(1000, 600)
        self.root.configure(bg=COLOR_BG)
        
        # Set Window Icon
        try:
            icon_path = Path(__file__).parent / "assets" / "ico.png"
            if icon_path.exists():
                self.icon_img = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, self.icon_img)
        except Exception as e:
            logger.error(f"Error loading window icon: {e}")

    def _init_log_handler(self):
        class TkLogHandler(logging.Handler):
            def __init__(self, callback):
                super().__init__()
                self.callback = callback
                self.setLevel(logging.INFO)
            def emit(self, record):
                try:
                    msg = self.format(record)
                    # Terminal debug to confirm handler is working
                    print(f"[HANDLER] {msg}")
                    self.callback(msg)
                except Exception: pass

        handler = TkLogHandler(self._add_log_entry)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(handler)
        
        self._log_lines = ["--- STUDIO LOG READY ---"]
        logging.info("GramoVoice Studio UI Started.")

    def _add_log_entry(self, message):
        self._log_lines.append(message)
        if len(self._log_lines) > 500: self._log_lines = self._log_lines[-500:]
        if self.is_running:
            try: self.root.after(10, self._flush_log)
            except Exception: pass

    def _flush_log(self):
        if not hasattr(self, 'log_console') or not self.log_console.winfo_exists(): return
        try:
            self.log_console.configure(state="normal")
            self.log_console.delete("1.0", "end")
            # Ensure at least one line is shown
            display_lines = self._log_lines
            self.log_console.insert("end", "\n".join(display_lines[-80:]))
            self.log_console.see("end")
            self.log_console.configure(state="disabled")
        except Exception: pass

    def _show_splash(self):
        self.splash_frame = tk.Frame(self.root, bg=COLOR_BG)
        self.splash_frame.pack(fill="both", expand=True)
        container = tk.Frame(self.splash_frame, bg=COLOR_BG)
        container.place(relx=0.5, rely=0.45, anchor="center")
        
        # Logo or Title on Splash
        self.splash_logo = self._load_logo(width=500)
        if self.splash_logo:
            tk.Label(container, image=self.splash_logo, bg=COLOR_BG).pack(pady=(0, 20))
        else:
            tk.Label(container, text="GRAMOVOICE", font=("", 36, "bold"), bg=COLOR_BG, fg=COLOR_ACCENT).pack(pady=(0, 10))
        self.lbl_splash_status = tk.Label(container, text="INITIALIZING...", font=("", 12), bg=COLOR_BG, fg=COLOR_TEXT_DIM)
        self.lbl_splash_status.pack(pady=(0, 10))
        self.lbl_splash_perc = tk.Label(container, text="0%", font=("", 10), bg=COLOR_BG, fg=COLOR_TEXT_DIM)
        self.lbl_splash_perc.pack(pady=(0, 5))
        self.splash_progress = ttk.Progressbar(container, length=400, mode="determinate")
        self.splash_progress.pack()

    def _start_initialization(self):
        if not self.is_running: return
        try:
            self.player = AudioPlayer()
            threading.Thread(target=self._initialization_flow, daemon=True).start()
        except Exception as e:
            logger.error(f"Startup failed: {e}")

    def _initialization_flow(self):
        self.root.after(0, lambda: self.splash_progress.configure(mode="indeterminate"))
        self.root.after(0, self.splash_progress.start)
        success = self.engine.load_model(
            status_callback=lambda t, c=None: self.root.after(0, lambda: (
                self.lbl_splash_status.configure(text=t.upper()),
                self.lbl_splash_perc.configure(text=f"{int(c*100)}%" if isinstance(c, (int, float)) else self.lbl_splash_perc.cget("text"))
            )),
            progress_callback=lambda v: self.root.after(0, lambda: (
                self.splash_progress.configure(mode="determinate", value=v*100) if v >= 0 else None,
                self.lbl_splash_perc.configure(text=f"{int(v*100)}%" if isinstance(v, (int, float)) else self.lbl_splash_perc.cget("text"))
            ))
        )
        if success:
            self.root.after(500, self._transition_to_main)
        else:
            self.root.after(500, self._show_error)

    def _show_error(self):
        for w in self.splash_frame.winfo_children(): w.destroy()
        tk.Label(self.splash_frame, text="ERROR LOADING ENGINE", font=("", 20), bg=COLOR_BG, fg=COLOR_CANCEL).pack(expand=True)

    def _transition_to_main(self):
        self.splash_frame.destroy()
        self._build_ui()
        self.refresh_history(force=True)
        self._refresh_voices()
        threading.Thread(target=self._playback_monitor, daemon=True).start()

    def _build_ui(self):
        main = tk.Frame(self.root, bg=COLOR_BG)
        main.pack(fill="both", expand=True)
        
        # Sidebar
        sidebar = tk.Frame(main, width=320, bg=COLOR_SIDEBAR)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        inner_side = tk.Frame(sidebar, bg=COLOR_SIDEBAR, padx=20, pady=15)
        inner_side.pack(fill="both", expand=True)
        
        # Logo or Title
        self.logo_img = self._load_logo()
        if self.logo_img:
            tk.Label(inner_side, image=self.logo_img, bg=COLOR_SIDEBAR).pack(pady=(0, 10))
        else:
            tk.Label(inner_side, text="GramoVoice", font=("", 24, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_ACCENT).pack(anchor="w", pady=(0, 10))
        tk.Frame(inner_side, height=1, bg=COLOR_BORDER).pack(fill="x", pady=10)
        
        tk.Label(inner_side, text="VOICE MODEL", font=("", 10, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_ACCENT).pack(anchor="w")
        self.voice_var = tk.StringVar()
        self.drop_voices = ttk.Combobox(inner_side, textvariable=self.voice_var, state="readonly")
        self.drop_voices.pack(fill="x", pady=(4, 15))
        self.drop_voices.bind("<<ComboboxSelected>>", lambda e: self._save_voice_speed())

        speed_header = tk.Frame(inner_side, bg=COLOR_SIDEBAR)
        speed_header.pack(fill="x", pady=(4, 0))
        tk.Label(speed_header, text="SPEED", font=("", 10, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_ACCENT).pack(side="left")
        self.lbl_speed_val = tk.Label(speed_header, text="1.0x", font=("", 10, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_ACCENT)
        self.lbl_speed_val.pack(side="right")

        self.sld_speed = ttk.Scale(inner_side, from_=0.5, to=2.0, command=self._on_speed_change)
        self.sld_speed.pack(fill="x", pady=(4, 20))
        
        tk.Label(inner_side, text="PROJECT HISTORY", font=("", 9, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_DIM).pack(anchor="w")
        
        # History Scroll
        hist_cont = tk.Frame(inner_side, bg=COLOR_SIDEBAR)
        hist_cont.pack(fill="both", expand=True, pady=5)
        self.canvas = tk.Canvas(hist_cont, bg=COLOR_SIDEBAR, highlightthickness=0)
        self.scroll = ttk.Scrollbar(hist_cont, orient="vertical", command=self.canvas.yview)
        self.history_scroll = tk.Frame(self.canvas, bg=COLOR_SIDEBAR)
        
        self.history_scroll.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.history_scroll, anchor="nw", width=280)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        
        # Scroll Wheel Support (Linux - Contextual)
        hist_cont.bind("<Enter>", lambda e: (self.root.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units")), self.root.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))))
        hist_cont.bind("<Leave>", lambda e: (self.root.unbind_all("<Button-4>"), self.root.unbind_all("<Button-5>")))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        # Main Content
        content = tk.Frame(main, bg=COLOR_BG, padx=30, pady=25)
        content.pack(side="left", fill="both", expand=True)
        
        self.txt_project_name = ttk.Entry(content, font=("", 14))
        self.txt_project_name.insert(0, "Untitled Project")
        self.txt_project_name.pack(fill="x", pady=(0, 15))
        self.txt_project_name.bind("<Control-a>", lambda e: (e.widget.select_range(0, 'end'), e.widget.icursor('end'), "break")[2])
        self.txt_project_name.bind("<Control-A>", lambda e: (e.widget.select_range(0, 'end'), e.widget.icursor('end'), "break")[2])
        
        editor = tk.Frame(content, bg=COLOR_CARD, highlightthickness=1, highlightbackground=COLOR_BORDER)
        editor.pack(fill="both", expand=False, pady=(0, 10))
        
        self.txt_input = tk.Text(editor, font=("", 14), height=12, bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, bd=0, padx=10, pady=10, wrap="word", insertbackground=COLOR_ACCENT)
        self.txt_input.pack(fill="both", expand=True)
        self.txt_input.bind("<KeyRelease>", lambda e: self._update_char_counter())
        self.txt_input.bind("<Control-a>", lambda e: (e.widget.tag_add("sel", "1.0", "end"), "break")[1])
        self.txt_input.bind("<Control-A>", lambda e: (e.widget.tag_add("sel", "1.0", "end"), "break")[1])

        self.lbl_char_count = tk.Label(content, text="0 chars", font=("", 10), bg=COLOR_BG, fg=COLOR_TEXT_DIM)
        self.lbl_char_count.pack(anchor="e")

        prog_frame = tk.Frame(content, bg=COLOR_BG)
        prog_frame.pack(fill="x", pady=5)
        self.lbl_progress = tk.Label(prog_frame, text="0%", font=("", 9), bg=COLOR_BG, fg=COLOR_TEXT_DIM)
        self.lbl_progress.pack(side="top", anchor="e")
        self.pb_gen = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.pb_gen.pack(fill="x")

        btn_frame = tk.Frame(content, bg=COLOR_BG)
        btn_frame.pack(fill="x", pady=10)
        self.btn_gen = tk.Button(btn_frame, text="GENERATE AUDIO", font=("", 12, "bold"), bg=COLOR_ACCENT, fg="white", bd=0, height=2, cursor="hand2", command=self._handle_generate)
        self.btn_gen.pack(side="left", fill="x", expand=True)
        
        tk.Button(btn_frame, text="📂 FOLDER", font=("", 10, "bold"), bg=COLOR_CARD, fg=COLOR_ACCENT, bd=0, width=10, height=2, command=self._open_output_folder).pack(side="right", padx=5)

        tk.Label(content, text="ENGINE LOGS", font=("", 9, "bold"), bg=COLOR_BG, fg=COLOR_TEXT_DIM).pack(anchor="w", pady=(10, 5))
        log_frame = tk.Frame(content, bg=COLOR_LOG_BG, highlightthickness=1, highlightbackground=COLOR_BORDER)
        log_frame.pack(fill="x", side="top")
        self.log_console = tk.Text(log_frame, height=6, bg=COLOR_LOG_BG, fg="#1e8e3e", font=("Courier", 11), bd=0, padx=10, pady=10, state="disabled", wrap="word")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_console.yview)
        self.log_console.configure(yscrollcommand=log_scroll.set)
        self.log_console.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        
        # Footer
        footer_cont = tk.Frame(content, bg=COLOR_BG)
        footer_cont.pack(side="bottom", fill="x", pady=(15, 0))
        
        footer = tk.Frame(footer_cont, bg=COLOR_BG)
        footer.pack(expand=True)
        
        tk.Label(footer, text="made by ", font=("", 9), bg=COLOR_BG, fg=COLOR_TEXT_DIM).pack(side="left")
        
        lbl_user = tk.Label(footer, text="unusual_zeru", font=("", 9), bg=COLOR_BG, fg=COLOR_ACCENT, cursor="hand2")
        lbl_user.pack(side="left")
        lbl_user.bind("<Button-1>", lambda e: self._open_url("https://x.com/unusual_zeru"))
        lbl_user.bind("<Enter>", lambda e: lbl_user.configure(fg=COLOR_ACCENT_HOVER))
        lbl_user.bind("<Leave>", lambda e: lbl_user.configure(fg=COLOR_ACCENT))
        
        tk.Label(footer, text=", one of the ", font=("", 9), bg=COLOR_BG, fg=COLOR_TEXT_DIM).pack(side="left")
        
        lbl_aliens = tk.Label(footer, text="aliens 👽🖖", font=("", 9), bg=COLOR_BG, fg=COLOR_ACCENT, cursor="hand2")
        lbl_aliens.pack(side="left")
        lbl_aliens.bind("<Button-1>", lambda e: self._open_url("https://defiverso.com"))
        lbl_aliens.bind("<Enter>", lambda e: lbl_aliens.configure(fg=COLOR_ACCENT_HOVER))
        lbl_aliens.bind("<Leave>", lambda e: lbl_aliens.configure(fg=COLOR_ACCENT))
        
        tk.Label(footer, text=" | github: ", font=("", 9), bg=COLOR_BG, fg=COLOR_TEXT_DIM).pack(side="left")
        
        lbl_repo = tk.Label(footer, text="gramovoice", font=("", 9), bg=COLOR_BG, fg=COLOR_ACCENT, cursor="hand2")
        lbl_repo.pack(side="left")
        lbl_repo.bind("<Button-1>", lambda e: self._open_url("https://github.com/thiegocarvalho/gramovoice"))
        lbl_repo.bind("<Enter>", lambda e: lbl_repo.configure(fg=COLOR_ACCENT_HOVER))
        lbl_repo.bind("<Leave>", lambda e: lbl_repo.configure(fg=COLOR_ACCENT))

        # Initial flush to show logs captured during startup
        self.root.after(100, self._flush_log)

    def _on_speed_change(self, v):
        self.lbl_speed_val.configure(text=f"{float(v):.1f}x")
        self._save_voice_speed()

    def _update_char_counter(self):
        chars = len(self.txt_input.get("1.0", "end-1c"))
        self.lbl_char_count.configure(text=f"{chars} chars")

    def _refresh_voices(self):
        voices = [v for v in AVAILABLE_VOICES.keys()]
        self.drop_voices.configure(values=voices)
        saved = self.settings.get("model", "Dora (Feminino) - PT")
        if saved not in voices: saved = voices[0] if voices else ""
        self.drop_voices.set(saved)
        self.sld_speed.set(float(self.settings.get("speed", 1.0)))

    def _save_voice_speed(self):
        self.settings["model"] = self.drop_voices.get()
        self.settings["speed"] = str(self.sld_speed.get())
        save_settings(self.settings)

    def _on_close(self):
        self.is_running = False
        if self.player: self.player.stop()
        self.root.destroy()

    def _open_output_folder(self):
        try:
            if sys.platform == "win32": os.startfile(self.output_dir)
            else: subprocess.run(["xdg-open", self.output_dir])
        except Exception: pass

    def _open_url(self, url: str) -> None:
        """Opens the specified URL in the default web browser."""
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")

    def refresh_history(self, force=False):
        try:
            now = time.time()
            if force or (now - self.last_history_poll > 3):
                self.last_history_poll = now
                files = sorted([f for f in os.listdir(self.output_dir) if f.endswith(".mp3") or f.endswith(".wav")], 
                               key=lambda x: os.path.getmtime(os.path.join(self.output_dir, x)), reverse=True)[:30]
                if files != self.last_history_files:
                    self.last_history_files = files
                    for widget in self.history_scroll.winfo_children(): widget.destroy()
                    self.cards = {}
                    for f in files:
                        full = os.path.join(self.output_dir, f)
                        card = ProjectCard(self.history_scroll, f, full, self._toggle_play, self._seek_audio)
                        card.pack(fill="x", pady=4)
                        self.cards[full] = card
            
            active = self.player.current_file if self.player else None
            playing = self.player.is_playing if self.player else False
            for path, card in self.cards.items():
                card.update_state(path == active, playing if path == active else False, 
                                  self.player.duration, self.player.position)
        except Exception: pass

    def _toggle_play(self, filename):
        full = os.path.join(self.output_dir, filename)
        if self.player.current_file == full:
            if self.player.is_playing: self.player.pause()
            else: self.player.unpause()
        else: self.player.play(full)
        self.refresh_history(force=True)

    def _seek_audio(self, pos):
        if self.player: self.player.seek(pos)

    def _playback_monitor(self):
        while self.is_running:
            if self.player and (self.player.is_playing or self.player.is_finished()):
                if self.player.is_finished(): self.player.stop()
                self.root.after(0, self.refresh_history)
            time.sleep(0.1)

    def _handle_generate(self):
        if self.is_generating:
            self.engine.cancel()
            self.btn_gen.configure(text="STOPPING...", state="disabled")
            return

        text = self.txt_input.get("1.0", "end-1c").strip()
        name = self.txt_project_name.get().strip()
        if not text or not name:
            messagebox.showwarning("Warning", "Text and Project Name are required!")
            return
        
        if not name.endswith(".mp3") and not name.endswith(".wav"): name += ".mp3"
        out_path = os.path.join(self.output_dir, name)
        
        self.is_generating = True
        self.btn_gen.configure(text="STOP", bg=COLOR_CANCEL)
        self.pb_gen["value"] = 0
        self.lbl_progress.configure(text="0%")
        
        def run():
            try:
                success = self.engine.synthesize(
                    text=text, 
                    output_path=out_path,
                    speed=float(self.sld_speed.get()),
                    speaker_wav=self.drop_voices.get(),
                    progress_callback=lambda v: self.root.after(0, lambda: (
                        self.pb_gen.configure(value=v*100),
                        self.lbl_progress.configure(text=f"{int(v*100)}%")
                    ))
                )
                self.root.after(0, lambda: self.refresh_history(force=True))
                if success: 
                    messagebox.showinfo("Success", f"Audio generated: {name}")
                elif self.engine._cancel_requested:
                    logger.info("Synthesis canceled by user.")
                else: 
                    messagebox.showerror("Error", "Synthesis failed!")
            finally:
                self.is_generating = False
                self.root.after(0, lambda: self.btn_gen.configure(state="normal", text="GENERATE AUDIO", bg=COLOR_ACCENT))

        threading.Thread(target=run, daemon=True).start()

def main(skip_engine=False):
    # If run directly as gui.py, we might want to parse args
    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("--skip-engine", action="store_true")
        args = parser.parse_args()
        skip_engine = args.skip_engine

    root = tk.Tk()
    
    # Mock for testing if needed
    if skip_engine:
        class MockEngine:
            def __init__(self): self.max_chars = 203; self.default_language = "pt"
            def load_model(self, **kwargs): return True
            def synthesize(self, **kwargs): time.sleep(2); return True
        engine = MockEngine()
    else:
        engine = TTSEngine()
        
    GramoVoice(root, engine)
    root.mainloop()

if __name__ == "__main__":
    main()

import os
import sys
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# All user data in a writable location — avoids PermissionError when the app
# is installed in a read-only directory (e.g. Program Files on Windows).
APP_DIR = Path.home() / ".gramovoice"
SETTINGS_FILE = APP_DIR / "settings.json"


def _ensure_app_dir() -> None:
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create app config dir: {e}")


def setup_bundle_paths() -> None:
    pass


def setup_environment() -> None:
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    # Point pydub to the bundled FFmpeg binary early so every AudioSegment
    # call (including duration reading in the player) works without a system
    # FFmpeg installation on Windows.
    try:
        import imageio_ffmpeg
        from pydub import AudioSegment
        AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass


def load_settings() -> dict:
    _ensure_app_dir()
    default_settings = {
        "output_dir": str(Path.home() / "GramoVoice"),
        "max_chars": 203,
        "language": "pt",
        "model": "Dora (Feminino) - PT",
        "speed": 1.0,
        "output_quality": "balanced",   # compact | balanced | standard | high
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_settings.update(saved)
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    # Ensure speed is always a float regardless of how it was stored.
    try:
        default_settings["speed"] = float(default_settings["speed"])
    except (TypeError, ValueError):
        default_settings["speed"] = 1.0

    return default_settings


def save_settings(settings: dict) -> None:
    _ensure_app_dir()
    data = dict(settings)
    try:
        data["speed"] = float(data.get("speed", 1.0))
    except (TypeError, ValueError):
        data["speed"] = 1.0
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except PermissionError as e:
        logger.error(f"Permission denied saving settings to {SETTINGS_FILE}: {e}")
    except Exception as e:
        logger.error(f"Error saving settings: {e}")


def sanitize_filename(name: str) -> str:
    """Return a filename safe for both Windows and Linux."""
    # Characters forbidden on Windows
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "_")
    # Control characters 0-31
    name = "".join(c if ord(c) >= 32 else "_" for c in name)
    # Windows forbids trailing dots and spaces
    name = name.rstrip(". ")
    # Windows reserved device names (case-insensitive, with or without extension)
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    stem = Path(name).stem.upper()
    if stem in reserved:
        name = "_" + name
    return name.strip() or "untitled"

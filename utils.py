import os
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent.absolute()
SETTINGS_FILE = BASE_DIR / "settings.json"

def setup_bundle_paths():
    pass

def setup_environment():
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    # Suppress heavy library output
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

def load_settings():
    default_settings = {
        "output_dir": str(BASE_DIR / "out"),
        "max_chars": 203,
        "language": "pt",
        "model": "Dora (Feminino) - PT",
        "speed": "1.0"
    }
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                default_settings.update(saved)
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    return default_settings

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
        logger.info("Settings saved.")
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

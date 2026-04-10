import os
import logging
import threading
import re
from typing import Optional, Callable
from pathlib import Path
from utils import setup_environment

# MUST be called BEFORE any heavy AI libraries are imported
setup_environment()

# Silence benign word count mismatch warnings from the G2P engine
logging.getLogger("misaki").setLevel(logging.ERROR)

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import urllib.request  # noqa: E402

logger = logging.getLogger(__name__)

KOKORO_REPO_ID = "leonelhs/kokoro-thewh1teagle"
AVAILABLE_VOICES = {
    "Dora (Feminino) - PT": "pf_dora",
    "Alex (Masculino) - PT": "pm_alex",
    "Santa (Masculino) - PT": "pm_santa",
    "Bella (Feminino) - INT": "af_bella",
    "Nicole (Feminino) - INT": "af_nicole",
    "Sarah (Feminino) - INT": "af_sarah",
    "Sky (Feminino) - INT": "af_sky",
    "Alice (Feminino) - INT": "bf_alice",
    "Adam (Masculino) - INT": "am_adam",
    "Michael (Masculino) - INT": "am_michael",
    "Liam (Masculino) - INT": "am_liam",
    "George (Masculino) - INT": "bm_george",
}

# Pre-compiled regex to strip emojis before synthesis
_EMOJI_PATTERN = re.compile(
    r'[\U00010000-\U0010ffff]'  # High Unicode block (modern emojis)
    r'|[\u2600-\u27BF]',        # Dingbats and miscellaneous symbols
    flags=re.UNICODE
)

class TTSEngine:
    """Core Text-to-Speech Engine utilizing Kokoro ONNX."""
    
    def __init__(self, max_chars: int = 300, default_language: str = "pt-br") -> None:
        self.max_chars = max_chars
        self.default_language = default_language
        self.device = "cpu"
        self.kokoro = None
        self.g2p = None
        self._load_lock = threading.Lock()
        self._cancel_requested = False
        logger.info("Device: CPU")


    def cancel(self) -> None:
        """Flags the engine to cancel any ongoing synthesis task."""
        self._cancel_requested = True

    def load_model(self, status_callback: Optional[Callable[[str, str], None]] = None,
                    progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """
        Loads the Kokoro ONNX model and the G2P engine.
        Downloads necessary files if they aren't available locally.
        """
        with self._load_lock:
            if self.kokoro is not None:
                return True

            try:
                def download_with_progress(url, dest_path, label, base_prog, prog_span):
                    if os.path.exists(dest_path):
                        return dest_path

                    if status_callback:
                        status_callback(f"{label}...", "#B87333")

                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        total_size = int(response.info().get('Content-Length', 0))
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        
                        downloaded = 0
                        with open(dest_path, 'wb') as f:
                            while True:
                                chunk = response.read(8192 * 4)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                if total_size > 0 and progress_callback and status_callback:
                                    if downloaded % (1024 * 1024 * 2) < (8192 * 4): 
                                        frac = downloaded / total_size
                                        progress_callback(base_prog + frac * prog_span)
                                        mb_done = downloaded / (1024 * 1024)
                                        mb_total = total_size / (1024 * 1024)
                                        status_callback(
                                            f"{label} ({mb_done:.1f}/{mb_total:.1f} MB)",
                                            "#B87333"
                                        )

                cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub", "models--leonelhs--kokoro-thewh1teagle", "snapshots", "main")
                
                model_url = "https://huggingface.co/leonelhs/kokoro-thewh1teagle/resolve/main/kokoro-v1.0.onnx"
                model_path = os.path.join(cache_dir, "kokoro-v1.0.onnx")
                download_with_progress(model_url, model_path, "Downloading model", 0.05, 0.45)

                voices_url = "https://huggingface.co/leonelhs/kokoro-thewh1teagle/resolve/main/voices-v1.0.bin"
                voices_path = os.path.join(cache_dir, "voices-v1.0.bin")
                download_with_progress(voices_url, voices_path, "Downloading voices", 0.5, 0.2)

                if progress_callback:
                    progress_callback(0.7)
                if status_callback:
                    status_callback("Loading engine (CPU)...", "#B87333")

                from kokoro_onnx import Kokoro
                self.kokoro = Kokoro(model_path, voices_path)

                if progress_callback:
                    progress_callback(0.9)
                if status_callback:
                    status_callback("Initializing G2P (PT-BR)...", "#B87333")

                from misaki.espeak import EspeakG2P
                self.g2p = EspeakG2P(language="pt-br")

                if progress_callback:
                    progress_callback(1.0)
                if status_callback:
                    status_callback("SYSTEM READY", "green")
                return True

            except Exception as e:
                logger.error(f"Engine Load failed: {e}")
                if status_callback:
                    status_callback("Engine Error", "red")
                return False

    def _split_into_chunks(self, text: str) -> list[str]:
        """
        Intelligently splits a long string of text into smaller chunks
        that do not exceed the `max_chars` limit, trying to break on paragraphs,
        sentences, or words.
        """
        text = _EMOJI_PATTERN.sub('', text)
        
        max_chars = self.max_chars
        text = re.sub(r'[ \t\f\v]+', ' ', text).strip()
        if len(text) <= max_chars and "\n" not in text:
            return [text]
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        chunks = []
        for p in paragraphs:
            if len(p) <= max_chars:
                chunks.append(p)
                continue
            sentences = re.split(r'(?<=[.!?])\s+', p)
            current = ""
            for s in sentences:
                if len(current) + len(s) + 1 < max_chars:
                    current = (current + " " + s).strip()
                else:
                    if current:
                        chunks.append(current)
                    current = s
            if current:
                chunks.append(current)
        final = []
        for c in chunks:
            c = c.strip()
            if not c or not any(ch.isalnum() for ch in c):
                continue
            if len(c) > max_chars:
                words = c.split(' ')
                sub = ""
                for w in words:
                    if len(sub) + len(w) + 1 < max_chars:
                        sub = (sub + " " + w).strip()
                    else:
                        if sub:
                            final.append(sub)
                        sub = w
                if sub:
                    final.append(sub)
            else:
                final.append(c)
        return [c for c in final if c.strip()]

    def synthesize(self, text: str, output_path: str, speed: float = 1.0,
                   speaker_wav: Optional[str] = None, language: Optional[str] = None,
                   progress_callback: Optional[Callable[[float], None]] = None,
                   chunk_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Synthesizes speech from text and saves it to the specified output path.
        Returns True if successful, False if canceled or failed.
        """
        self._cancel_requested = False
        if not self.kokoro and not self.load_model():
            return False
        try:
            voice_name = speaker_wav or "Dora (Feminino)"
            voice_id = AVAILABLE_VOICES.get(voice_name, "pf_dora")
            chunks = self._split_into_chunks(text)
            total = len(chunks)
            if total == 0:
                return False
            all_samples = []
            sample_rate = 24000
            for i, chunk in enumerate(chunks):
                if self._cancel_requested:
                    return False
                if progress_callback:
                    progress_callback(i / total)
                if chunk_callback:
                    chunk_callback(f"Synthesizing {i+1}/{total}...")
                phonemes, _ = self.g2p(chunk)
                samples, sr = self.kokoro.create(
                    phonemes, voice=voice_id, speed=speed, is_phonemes=True
                )
                sample_rate = sr
                all_samples.append(samples)
                if total > 1:
                    silence = np.zeros(int(sample_rate * 0.25), dtype=np.float32)
                    all_samples.append(silence)
            if self._cancel_requested:
                return False
            if progress_callback:
                progress_callback(1.0)
            combined = np.concatenate(all_samples)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            if output_path.endswith(".mp3"):
                wav_path = output_path.replace(".mp3", ".wav")
                sf.write(wav_path, combined, sample_rate)
                try:
                    import imageio_ffmpeg
                    from pydub import AudioSegment
                    
                    # Point PyDub to the locally bundled FFmpeg executable
                    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()
                    
                    audio = AudioSegment.from_wav(wav_path)
                    # Use explicit tag-free export to avoid mpg123 compatibility issues on Linux
                    audio.export(output_path, format="mp3", bitrate="192k", tags={})
                    
                    # Ensure the file is fully written before cleanup
                    if os.path.exists(output_path):
                        os.remove(wav_path)
                    else:
                        logger.warning(f"MP3 export failed (file not created), keeping WAV at {wav_path}.")
                except Exception as e:
                    logger.warning(f"MP3 export failed: {e}. Keeping WAV at {wav_path}.")
            else:
                sf.write(output_path, combined, sample_rate)
            return True
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return False

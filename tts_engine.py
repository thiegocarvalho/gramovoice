import os
import sys
import queue
import logging
import re
import subprocess
import threading
import time
import urllib.request
from typing import Optional, Callable
from pathlib import Path
from utils import setup_environment

# Must run before importing heavy AI libraries
setup_environment()

logging.getLogger("misaki").setLevel(logging.ERROR)

import numpy as np      # noqa: E402
import soundfile as sf  # noqa: E402

logger = logging.getLogger(__name__)

KOKORO_REPO_ID    = "leonelhs/kokoro-thewh1teagle"
KOKORO_SAMPLE_RATE = 24000

AVAILABLE_VOICES = {
    "Dora (Feminino) - PT":    "pf_dora",
    "Alex (Masculino) - PT":   "pm_alex",
    "Santa (Masculino) - PT":  "pm_santa",
    "Bella (Feminino) - INT":  "af_bella",
    "Nicole (Feminino) - INT": "af_nicole",
    "Sarah (Feminino) - INT":  "af_sarah",
    "Sky (Feminino) - INT":    "af_sky",
    "Alice (Feminino) - INT":  "bf_alice",
    "Adam (Masculino) - INT":  "am_adam",
    "Michael (Masculino) - INT": "am_michael",
    "Liam (Masculino) - INT":  "am_liam",
    "George (Masculino) - INT": "bm_george",
}

_MIN_MODEL_BYTES = 1 * 1024 * 1024

_POPEN_FLAGS: dict = {}
if sys.platform == "win32":
    _POPEN_FLAGS["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

# ── pt-BR text preprocessing ──────────────────────────────────────────────────

_EMOJI_RE = re.compile(
    r"[\U00010000-\U0010ffff]|[☀-➿]",
    flags=re.UNICODE,
)

# Abbreviations that must NOT trigger a sentence split.
# Stored lowercase without the trailing dot.
_PT_BR_ABBREVS = frozenset({
    # Titles
    "sr", "sra", "dr", "dra", "prof", "profa", "eng", "engª",
    "adm", "rev", "pe", "cel", "cap", "sgt", "cb", "sd",
    # Address
    "av", "r", "al", "trav", "rod", "bl", "ap", "apto", "cj",
    # Common
    "etc", "obs", "ex", "vs", "op", "ed", "fig", "tab", "ref",
    "tel", "fax", "cel", "pag", "pág", "num", "nº", "vol",
    # Months (abbreviated)
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
    # Legal / business
    "ltda", "eireli", "s/a", "me", "epp",
    # Latin
    "p.ex", "p.s", "obs",
})

# Abbreviation expansion applied BEFORE G2P.
# Each entry: (compiled regex, replacement string)
_PT_BR_ABBREV_EXPANSIONS = [
    (re.compile(r"\bSr\.\s"),    "Senhor "),
    (re.compile(r"\bSra\.\s"),   "Senhora "),
    (re.compile(r"\bDr\.\s"),    "Doutor "),
    (re.compile(r"\bDra\.\s"),   "Doutora "),
    (re.compile(r"\bProf\.\s"),  "Professor "),
    (re.compile(r"\bProfa\.\s"), "Professora "),
    (re.compile(r"\bEng\.\s"),   "Engenheiro "),
    (re.compile(r"\bEngª\.\s"),  "Engenheira "),
    (re.compile(r"\betc\.",  re.IGNORECASE), "etcétera"),
    (re.compile(r"\bobs\.",  re.IGNORECASE), "observação"),
    (re.compile(r"\bp\.ex\.", re.IGNORECASE), "por exemplo"),
    (re.compile(r"\bvs\.",   re.IGNORECASE), "versus"),
    (re.compile(r"\bex\.\s", re.IGNORECASE), "por exemplo "),
    (re.compile(r"\bav\.\s", re.IGNORECASE), "avenida "),
]

_ORDINALS_MASC = [
    "primeiro", "segundo", "terceiro", "quarto", "quinto",
    "sexto", "sétimo", "oitavo", "nono", "décimo",
]
_ORDINALS_FEM = [
    "primeira", "segunda", "terceira", "quarta", "quinta",
    "sexta", "sétima", "oitava", "nona", "décima",
]


def _preprocess_pt_br(text: str) -> str:
    """
    Normalize pt-BR text before sending to G2P so that espeak-ng renders
    common patterns correctly: markdown, URLs, currency, percentages,
    ordinals, and abbreviated titles.
    """
    # 1. Markdown → plain text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)          # code blocks / inline
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)   # [label](url) → label

    # 2. URLs and emails → readable placeholders
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"www\.\S+", "link", text)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", "e-mail", text)

    # 3. Currency: R$ 1.234,56 → "1.234,56 reais"
    #    Pattern ends with \d to avoid capturing sentence-ending dots.
    text = re.sub(r"R\$\s*([\d.,]*\d)", r"\1 reais", text)
    text = re.sub(r"US\$\s*([\d.,]*\d)", r"\1 dólares", text)
    text = re.sub(r"€\s*([\d.,]*\d)", r"\1 euros", text)

    # 4. Percentage: 50% → "50 por cento"
    text = re.sub(r"([\d]+(?:[.,]\d+)?)\s*%", r"\1 por cento", text)

    # 5. Ordinals 1º–10º / 1ª–10ª → full words
    def _expand_ord_m(m: re.Match) -> str:
        n = int(m.group(1))
        return _ORDINALS_MASC[n - 1] if 1 <= n <= 10 else m.group(0)

    def _expand_ord_f(m: re.Match) -> str:
        n = int(m.group(1))
        return _ORDINALS_FEM[n - 1] if 1 <= n <= 10 else m.group(0)

    text = re.sub(r"\b([1-9]|10)º", _expand_ord_m, text)
    text = re.sub(r"\b([1-9]|10)ª", _expand_ord_f, text)

    # 6. Common abbreviated titles
    for pattern, replacement in _PT_BR_ABBREV_EXPANSIONS:
        text = pattern.sub(replacement, text)

    # 7. Acronyms written in all-caps (3+ letters, not at sentence start) → spaced letters
    #    e.g. "BNDES" → "B N D E S" so espeak spells them out clearly.
    #    Limit to 3-6 letter sequences to avoid false positives on all-caps sentences.
    def _space_acronym(m: re.Match) -> str:
        word = m.group(0)
        # Skip if it's a known word or Portuguese Roman numeral
        return " ".join(word)

    text = re.sub(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÜ]{3,6}\b", _space_acronym, text)

    return text


def _split_sentences_pt_br(paragraph: str) -> list[str]:
    """
    Split a paragraph into sentences for pt-BR, without breaking on
    common abbreviations like 'Dr.', 'Sr.', 'Sra.', etc.

    Strategy: temporarily replace dots in known abbreviations with a
    private-use Unicode character, then split on [.!?], then restore.
    """
    _DOT_PLACEHOLDER = ""  # Private Use Area — safe as placeholder

    # Protect dots inside known abbreviations
    def _protect(m: re.Match) -> str:
        word = m.group(1)
        if word.lower() in _PT_BR_ABBREVS:
            return word + _DOT_PLACEHOLDER
        return m.group(0)

    # Match word.dot patterns (e.g., "Dr.", "Jan.")
    protected = re.sub(r"\b([A-Za-zÀ-ÿ]+)\.", _protect, paragraph)

    # Also protect single uppercase initials ("J. Silva" → "J Silva")
    protected = re.sub(r"\b([A-ZÁÉÍÓÚ])\.", r"\1" + _DOT_PLACEHOLDER, protected)

    # Split on real sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?…])\s+(?=[A-ZÁÉÍÓÚ\"\'])", protected)

    # Restore placeholder dots
    return [s.replace(_DOT_PLACEHOLDER, ".").strip() for s in sentences if s.strip()]


# ── Engine ────────────────────────────────────────────────────────────────────

def _voice_language(voice_name: str) -> str:
    """Return 'pt-br' for PT voices, 'en-us' for INT voices."""
    if voice_name.endswith("- PT"):
        return "pt-br"
    if voice_name.endswith("- INT"):
        return "en-us"
    return "pt-br"


class TTSEngine:
    """Core Text-to-Speech Engine utilizing Kokoro ONNX."""

    def __init__(self, max_chars: int = 300, default_language: str = "pt-br") -> None:
        self.max_chars = max_chars
        self.default_language = default_language
        self.device = "cpu"
        self.kokoro = None
        self.g2p_ptbr = None   # pt-BR G2P (EspeakG2P)
        self.g2p_en   = None   # en-US G2P (EspeakG2P)
        self._load_lock = threading.Lock()
        self._cancel_requested = False
        logger.info("Device: CPU")

    def cancel(self) -> None:
        self._cancel_requested = True

    # ── Model loading ─────────────────────────────────────────────────────────

    def load_model(
        self,
        status_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> bool:
        with self._load_lock:
            if self.kokoro is not None:
                return True
            try:
                def _download(url, dest, label, base, span):
                    if os.path.exists(dest):
                        if os.path.getsize(dest) >= _MIN_MODEL_BYTES:
                            return
                        logger.warning(f"Removing incomplete download: {dest}")
                        try:
                            os.remove(dest)
                        except Exception:
                            pass
                    if status_callback:
                        status_callback(f"{label}...", "#B87333")
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    try:
                        with urllib.request.urlopen(req, timeout=60) as r:
                            total = int(r.info().get("Content-Length", 0))
                            done = 0
                            with open(dest, "wb") as f:
                                while True:
                                    chunk = r.read(8192 * 4)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                                    done += len(chunk)
                                    if total > 0 and done % (2 * 1024 * 1024) < (8192 * 4):
                                        if progress_callback:
                                            progress_callback(base + (done / total) * span)
                                        if status_callback:
                                            status_callback(
                                                f"{label} ({done/1e6:.1f}/{total/1e6:.1f} MB)",
                                                "#B87333",
                                            )
                    except Exception:
                        try:
                            os.remove(dest)
                        except Exception:
                            pass
                        raise

                cache = os.path.join(
                    os.path.expanduser("~"), ".cache", "huggingface", "hub",
                    "models--leonelhs--kokoro-thewh1teagle", "snapshots", "main",
                )
                base_url = "https://huggingface.co/leonelhs/kokoro-thewh1teagle/resolve/main"

                model_path  = os.path.join(cache, "kokoro-v1.0.onnx")
                voices_path = os.path.join(cache, "voices-v1.0.bin")
                _download(f"{base_url}/kokoro-v1.0.onnx",  model_path,  "Downloading model",  0.05, 0.45)
                _download(f"{base_url}/voices-v1.0.bin",   voices_path, "Downloading voices", 0.50, 0.20)

                if progress_callback:
                    progress_callback(0.70)
                if status_callback:
                    status_callback("Loading ONNX engine...", "#B87333")

                from kokoro_onnx import Kokoro
                self.kokoro = Kokoro(model_path, voices_path)

                if progress_callback:
                    progress_callback(0.85)
                if status_callback:
                    status_callback("Initializing G2P (PT-BR)...", "#B87333")

                from misaki.espeak import EspeakG2P
                self.g2p_ptbr = EspeakG2P(language="pt-br")

                if progress_callback:
                    progress_callback(0.95)
                if status_callback:
                    status_callback("Initializing G2P (EN-US)...", "#B87333")

                self.g2p_en = EspeakG2P(language="en-us")

                if progress_callback:
                    progress_callback(1.0)
                if status_callback:
                    status_callback("SYSTEM READY", "green")
                return True

            except Exception as e:
                logger.error(f"Engine Load failed: {e}")
                if status_callback:
                    status_callback(f"Engine Error: {e}", "red")
                return False

    # ── Text chunking ─────────────────────────────────────────────────────────

    def _split_into_chunks(self, text: str, language: str = "pt-br") -> list[str]:
        """
        Split text into synthesis-ready chunks.

        For pt-BR, applies text normalization and uses an abbreviation-aware
        sentence splitter so that 'Dr. Silva' is never broken into two chunks.
        """
        # Strip emojis
        text = _EMOJI_RE.sub("", text)

        # pt-BR specific preprocessing (normalizes markdown, URLs, currency, etc.)
        if language == "pt-br":
            text = _preprocess_pt_br(text)

        # Collapse whitespace
        text = re.sub(r"[ \t\f\v]+", " ", text).strip()

        max_c = self.max_chars

        if len(text) <= max_c and "\n" not in text:
            return [text]

        # Split into paragraphs (double newline = paragraph; single = line)
        paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]

        raw_chunks: list[str] = []
        for para in paragraphs:
            if len(para) <= max_c:
                raw_chunks.append(para)
                continue

            # Split into sentences using the appropriate splitter
            if language == "pt-br":
                sentences = _split_sentences_pt_br(para)
            else:
                sentences = re.split(r"(?<=[.!?…])\s+", para)

            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 <= max_c:
                    current = (current + " " + sent).strip()
                else:
                    if current:
                        raw_chunks.append(current)
                    current = sent
            if current:
                raw_chunks.append(current)

        # Final pass: split oversized chunks at word boundaries
        final: list[str] = []
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if not chunk or not any(c.isalnum() for c in chunk):
                continue
            if len(chunk) <= max_c:
                final.append(chunk)
            else:
                words = chunk.split()
                sub = ""
                for w in words:
                    if len(sub) + len(w) + 1 <= max_c:
                        sub = (sub + " " + w).strip()
                    else:
                        if sub:
                            final.append(sub)
                        sub = w
                if sub:
                    final.append(sub)

        return [c for c in final if c.strip()]

    # ── Synthesis ─────────────────────────────────────────────────────────────

    def synthesize(
        self,
        text: str,
        output_path: str,
        speed: float = 1.0,
        speaker_wav: Optional[str] = None,
        language: Optional[str] = None,
        mp3_quality: str = "balanced",
        progress_callback: Optional[Callable[[float], None]] = None,
        chunk_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Two-stage pipeline:
          1. Background thread — G2P phoneme conversion (prefetched, up to 4 chunks ahead)
          2. Main thread       — ONNX inference → stream audio directly to disk

        For MP3, raw PCM is piped into ffmpeg — no temp WAV file.
        For WAV, samples are written incrementally — no np.concatenate.

        Language is derived from the voice name suffix (- PT / - INT) so that
        pt-BR voices use Brazilian Portuguese G2P and INT voices use English G2P.
        """
        self._cancel_requested = False
        if not self.kokoro and not self.load_model():
            return False

        voice_name = speaker_wav or "Dora (Feminino) - PT"
        voice_id   = AVAILABLE_VOICES.get(voice_name, "pf_dora")
        lang       = language or _voice_language(voice_name)

        # Pick the correct G2P for this voice's language
        if lang == "pt-br":
            g2p = self.g2p_ptbr
        else:
            g2p = self.g2p_en

        if g2p is None:
            logger.error("G2P engine not initialised — call load_model() first.")
            return False

        try:
            chunks = self._split_into_chunks(text, language=lang)
            total  = len(chunks)
            if total == 0:
                return False

            logger.info(f"Synthesizing {total} chunk(s) | voice={voice_id} | lang={lang} | quality={mp3_quality}")

            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                logger.error(f"Cannot create output directory: {e}")
                return False

            # Silence inserted between chunks (250 ms within a paragraph)
            silence_between = np.zeros(int(KOKORO_SAMPLE_RATE * 0.25), dtype=np.float32)

            # ── Stage 1: G2P prefetch ─────────────────────────────────────────
            g2p_q: queue.Queue = queue.Queue(maxsize=4)
            _DONE = object()

            def _g2p_worker() -> None:
                for ch in chunks:
                    if self._cancel_requested:
                        g2p_q.put(_DONE)
                        return
                    try:
                        phonemes, _ = g2p(ch)
                        g2p_q.put(phonemes)
                    except Exception as exc:
                        logger.error(f"G2P error on chunk '{ch[:40]}': {exc}")
                        g2p_q.put(_DONE)
                        return
                g2p_q.put(_DONE)

            threading.Thread(target=_g2p_worker, daemon=True).start()

            # ── Stage 2: ONNX synthesis → disk ───────────────────────────────
            chunk_times: list[float] = []
            is_mp3 = output_path.endswith(".mp3")

            if is_mp3:
                return self._stream_to_mp3(
                    output_path, voice_id, speed, total, silence_between,
                    g2p_q, _DONE, chunk_times, mp3_quality,
                    progress_callback, chunk_callback,
                )
            else:
                return self._stream_to_wav(
                    output_path, voice_id, speed, total, silence_between,
                    g2p_q, _DONE, chunk_times,
                    progress_callback, chunk_callback,
                )

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return False

    # ── Streaming writers ─────────────────────────────────────────────────────

    def _eta(self, done: int, total: int, times: list[float]) -> str:
        if not times or done >= total:
            return ""
        avg  = sum(times) / len(times)
        secs = avg * (total - done)
        return (f"~{int(secs//60)}m{int(secs%60):02d}s" if secs >= 60 else f"~{int(secs)}s") + " restantes"

    def _stream_to_wav(
        self, output_path, voice_id, speed, total, silence,
        g2p_q, done_sentinel, times,
        on_progress, on_chunk,
    ) -> bool:
        wav: Optional[sf.SoundFile] = None
        try:
            for i in range(total):
                if self._cancel_requested:
                    return False
                phonemes = g2p_q.get()
                if phonemes is done_sentinel:
                    return False
                if on_progress:
                    on_progress(i / total)

                t0 = time.perf_counter()
                samples, sr = self.kokoro.create(phonemes, voice=voice_id, speed=speed, is_phonemes=True)
                times.append(time.perf_counter() - t0)

                if wav is None:
                    wav = sf.SoundFile(output_path, "w", samplerate=sr, channels=1,
                                       format="WAV", subtype="PCM_16")
                wav.write(samples)
                if total > 1:
                    wav.write(silence)

                if on_chunk:
                    on_chunk(f"[{i+1}/{total}] {self._eta(i+1, total, times)}")

            if on_progress:
                on_progress(1.0)
            return True
        except Exception as e:
            logger.error(f"WAV stream error: {e}")
            return False
        finally:
            if wav:
                wav.close()

    _MP3_QUALITY_FLAGS: dict[str, list[str]] = {
        "compact":  ["-q:a", "6"],    # VBR Q6 ≈ 60 kbps mono
        "balanced": ["-q:a", "4"],    # VBR Q4 ≈ 80 kbps mono  (default)
        "standard": ["-b:a", "128k"], # CBR 128 kbps
        "high":     ["-b:a", "192k"], # CBR 192 kbps
    }

    def _stream_to_mp3(
        self, output_path, voice_id, speed, total, silence,
        g2p_q, done_sentinel, times, mp3_quality,
        on_progress, on_chunk,
    ) -> bool:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as e:
            logger.error(f"imageio-ffmpeg unavailable: {e}")
            return False

        q_flags = self._MP3_QUALITY_FLAGS.get(mp3_quality, self._MP3_QUALITY_FLAGS["balanced"])
        logger.info(f"MP3 quality={mp3_quality} flags={q_flags}")

        proc: Optional[subprocess.Popen] = None
        try:
            proc = subprocess.Popen(
                [
                    ffmpeg,
                    "-f", "f32le", "-ar", str(KOKORO_SAMPLE_RATE), "-ac", "1",
                    "-i", "pipe:0",
                    "-codec:a", "libmp3lame", *q_flags,
                    "-id3v2_version", "3", "-write_id3v1", "1",
                    "-y", output_path,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                **_POPEN_FLAGS,
            )

            for i in range(total):
                if self._cancel_requested:
                    proc.stdin.close()
                    proc.wait()
                    _safe_remove(output_path)
                    return False

                phonemes = g2p_q.get()
                if phonemes is done_sentinel:
                    proc.stdin.close()
                    proc.wait()
                    _safe_remove(output_path)
                    return False

                if on_progress:
                    on_progress(i / total)

                t0 = time.perf_counter()
                samples, _ = self.kokoro.create(phonemes, voice=voice_id, speed=speed, is_phonemes=True)
                times.append(time.perf_counter() - t0)

                proc.stdin.write(samples.astype(np.float32).tobytes())
                if total > 1:
                    proc.stdin.write(silence.tobytes())

                if on_chunk:
                    on_chunk(f"[{i+1}/{total}] {self._eta(i+1, total, times)}")

            proc.stdin.close()
            _, stderr_data = proc.communicate()

            if proc.returncode != 0:
                logger.error(f"ffmpeg error (rc={proc.returncode}): {stderr_data.decode(errors='replace')}")
                _safe_remove(output_path)
                return False

            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error("ffmpeg produced no output.")
                return False

            if on_progress:
                on_progress(1.0)
            return True

        except Exception as e:
            logger.error(f"MP3 stream error: {e}")
            if proc:
                try:
                    proc.stdin.close()
                    proc.kill()
                    proc.wait()
                except Exception:
                    pass
            _safe_remove(output_path)
            return False


def _safe_remove(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

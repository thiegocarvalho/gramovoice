# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-04-28

### Added
- **MP3 Output Quality Selector:** New sidebar dropdown with four presets — Compacto VBR (~0.45 MB/min), Balanceado VBR (~0.60 MB/min, default), Padrão 128k (~0.96 MB/min), Alta 192k (~1.44 MB/min). VBR presets deliver equal or better voice quality at up to 3× smaller file sizes vs the previous 192k CBR default.
- **pt-BR Text Preprocessing Pipeline:** Automatic normalization before G2P conversion — Markdown formatting stripped, URLs replaced with "link", emails with "e-mail", `R$`/`US$`/`€` expanded to currency words, percentages to "por cento", ordinals 1º–10º to full words, common abbreviated titles (Dr., Sra., Prof., etc.) expanded.
- **Acronym Pronunciation:** All-caps sequences (3–6 letters, e.g. CNPJ, PIB) are automatically spaced letter-by-letter before G2P so espeak-ng spells them out correctly in pt-BR.
- **Cross-Platform Mouse Wheel Scrolling:** History panel now responds to `<MouseWheel>` on Windows and macOS in addition to the existing `<Button-4/5>` Linux bindings.
- **macOS Folder Open Support:** `_open_output_folder` now uses `open` on Darwin in addition to `os.startfile` (Windows) and `xdg-open` (Linux).

### Fixed
- **Critical — Wrong G2P for English Voices:** INT voices (Bella, Nicole, Sarah, Sky, Alice, Adam, Michael, Liam, George) were being processed by the pt-BR G2P engine, producing garbled/accented English audio. Two G2P instances are now loaded (`pt-br` and `en-us`) and selected automatically based on the voice name suffix (`- PT` / `- INT`).
- **pt-BR Sentence Splitter:** The sentence boundary detector no longer splits on abbreviation dots (`Dr.`, `Sra.`, `Prof.`, `Jan.`, etc.). A placeholder-based technique protects ~35 common pt-BR abbreviations before splitting, preventing nonsense fragments from reaching the ONNX model.
- **Windows PermissionError on Startup:** Settings and default output directory moved from the application directory to `~/.gramovoice/settings.json` and `~/GramoVoice/` respectively — eliminates write failures when the app is installed in a read-only location such as Program Files.
- **Windows File-Locking on WAV Deletion:** The old WAV→pydub→MP3 path has been replaced by a direct PCM→ffmpeg pipe, eliminating the intermediate WAV file and all associated `PermissionError [WinError 32]` issues.
- **Corrupted Partial Downloads:** Model download now validates file size (≥ 1 MB) and deletes corrupted partial files before re-downloading, preventing silent failures on next startup.
- **Download Hang:** Added a 60-second timeout to all model download requests.
- **Window Icon on Windows:** The app now uses `root.iconbitmap(.ico)` on Windows and `iconphoto(.png)` on Linux/macOS for correct rendering.
- **Debug Spam in Terminal:** Removed the `print(f"[HANDLER] {msg}")` line that printed every log entry to stdout during synthesis.
- **`sanitize_filename` on Windows:** Now strips trailing dots and spaces (forbidden by NTFS) and prefixes Windows reserved device names (`CON`, `NUL`, `COM1`…`LPT9`) with `_`.
- **Settings Type Consistency:** Speed is now stored and loaded as `float` in both settings.json and at runtime.

### Changed
- **Streaming Audio Output:** Synthesis no longer accumulates all samples in RAM before writing. WAV output uses `soundfile.SoundFile` in incremental write mode; MP3 output pipes raw PCM directly into `ffmpeg` — both eliminating the `np.concatenate` allocation that scaled linearly with file length.
- **G2P Prefetch Pipeline:** G2P phoneme conversion now runs in a dedicated background thread (queue depth 4), overlapping with ONNX inference and hiding most of espeak-ng's per-chunk latency.
- **ETA Display in Logs:** The engine log shows `[chunk/total] ~Xm00s restantes` during synthesis so progress on long documents is visible.
- **pydub FFmpeg Configured Globally:** `AudioSegment.converter` is now set to the bundled `imageio-ffmpeg` binary in `setup_environment()`, ensuring audio duration reading in the player works without a system FFmpeg on Windows.
- **Removed `customtkinter` from requirements:** Package was declared but unused; removed to slim down the dependency tree.
- **Cleaned up duplicate requirements:** Removed duplicate entries for `pygame`, `pydub`, `fastapi`, and `uvicorn`.

## [1.2.3] - 2026-03-23

### Fixed
- **Zero-Dependency MP3 Export:** Integrated `imageio-ffmpeg` to directly bundle a local, highly-optimized FFmpeg binary into the application. This restores `.mp3` format as the default universally, completely fixing `[WinError 2]` and eliminating the need for users to install external system libraries for audio encoding!


## [1.2.2] - 2026-03-23

### Fixed
- **Windows File System Error [WinError 2/183]:** Fixed a critical pathing bug where `pydub` would fail silently without `ffmpeg` on Windows and corrupt the audio files.
- **Universal Audio Standard:** Transitioned all applications (`GUI`, `API`, `MCP`) to output `.wav` format by default, creating a completely standalone environment without relying on external system libraries.


## [1.2.1] - 2026-03-23

### Added
- **UI Footer:** Added professional clickable footer tracking creator and community links (`made by unusual_zeru, one of the aliens 👽🖖`).
- **Application Icons:** Integrated custom windows `.ico` and linux `.png` icons dynamically setting app-level branding.

### Changed
- **Build Optimization:** Re-architected `build_app.sh` utilizing a clean venv injection to shrink binary distributions from 3.1 GB to under 100 MB.
- **Embedded ML Data:** Explicit bundling of `kokoro_onnx`, `misaki`, `language_tags`, and `phonemizer` language data directly into the standalone binary to prevent runtime environment mismatches.
- Refactored core modules to completely remove legacy references.

## [1.2.0] - 2026-03-21

### Added
- **Kokoro ONNX core:** Fully migrated to Kokoro ONNX Text-to-Speech Engine for optimal edge performance.
- **GramoVoice Studio UI:** Custom stylized Tkinter-based user interface with real-time waveform tracking.
- **Local MCP Server:** Native integration mode for API and Agentic environments.
- Open Source community documents (LICENSE, CONTRIBUTING.md, SECURITY.md).

### Changed
- Standardized entirely around Python type hints and docstrings.
- Extracted and decoupled the `AudioPlayer` thread management for high stability.
- Explicitly defined missing core dependencies (`pygame`) to ensure zero-crash initialization.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

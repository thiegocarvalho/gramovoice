# GramoVoice Studio Edition v1.3.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Text-to-Speech (TTS) studio powered by **Kokoro ONNX**, optimized for PT-BR narration with full Windows and Linux support.

---

## ✨ Features

- **12 voices** — 3 PT-BR (Dora, Alex, Santa) + 9 English (Bella, Nicole, Sarah, Sky, Alice, Adam, Michael, Liam, George)
- **pt-BR text preprocessing** — markdown, URLs, R$/currency, percentages, ordinals, abbreviations and acronyms normalized automatically before synthesis
- **MP3 quality selector** — Compact VBR / Balanced VBR (default) / Standard 128k / High 192k
- **Streaming pipeline** — audio written chunk-by-chunk directly to disk, no RAM spike for large files
- **Zero system dependencies** — bundled FFmpeg via `imageio-ffmpeg`, no external install required
- **FastAPI layer** — REST backend with webhook support
- **MCP tooling** — native Model Context Protocol support for AI assistants

---

## 📥 Download (Easy Way)

Download the pre-compiled standalone executable — zero configuration, zero programming knowledge required.

👉 **[Releases page](https://github.com/thiegocarvalho/gramovoice/releases/latest)** — grab the `.exe` (Windows) or `.AppImage` (Linux).

> **First run:** the app downloads the Kokoro model (~2 GB) automatically and caches it at `~/.cache/huggingface/`. Subsequent launches are instant.

---

## 🚀 Developer Quick Start

```bash
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Operational Modes

| Command | Mode |
|---|---|
| `python main.py` | GUI Studio (default) |
| `python main.py --api` | FastAPI server on `0.0.0.0:8000` |
| `python main.py --mcp` | MCP stdio server |
| `python main.py --skip-engine` | GUI without model (UI diagnostics) |

### Output files

Generated audio is saved to `~/GramoVoice/` by default. You can change this path in the app settings (`~/.gramovoice/settings.json`).

---

## 📦 Building Releases

GramoVoice uses **PyInstaller** to produce a fully portable 80–100 MB executable (vs. 3 GB+ standard ML distributions).

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
bash build_app.sh
```

Outputs:
- **Linux** → `GramoVoice-Studio-Linux-x86_64.AppImage`
- **Windows** → `dist/GramoVoice-Studio.exe`

---

## 🤖 MCP Integration

Add this to your AI assistant's MCP config:

```json
{
  "mcpServers": {
    "gramovoice": {
      "command": "/path/to/GramoVoice/venv/bin/python",
      "args": ["/path/to/GramoVoice/main.py", "--mcp"]
    }
  }
}
```

Available tool: `generate_audio` — synthesizes text to MP3/WAV using any of the 12 available voices.

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome.  
Check the [issues page](https://github.com/thiegocarvalho/gramovoice/issues) and read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

---

## 📝 License

[MIT](LICENSE) — © Thiego Carvalho

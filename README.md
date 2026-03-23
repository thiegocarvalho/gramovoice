# GramoVoice Studio Edition v1.2.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: PEP8](https://img.shields.io/badge/code%20style-pep8-green.svg)](https://www.python.org/dev/peps/pep-0008/)

A Text-to-Speech (TTS) studio powered by **Kokoro ONNX**, optimized for PT-BR narration.

## ✨ Features
- **MCP Tooling**: Native Model Context Protocol support for AI assistants.
- **FastAPI Layer**: Robust backend with webhook support.

## 📥 Download Executables (Easy Way)

The easiest way to use GramoVoice is to download the pre-compiled standalone executables! This requires zero configuration and zero programming knowledge.

👉 **[Click here to go to our Releases page](https://github.com/thiegocarvalho/gramovoice/releases/latest)** and download the `.exe` (Windows) or `.AppImage` (Linux) file.

---

## 🚀 Developer Quick Start

### Installation
1. Setup environment:
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start the Studio:
   ```bash
   python main.py
   ```

### Operational Modes
- **GUI (Studio)**: `python main.py`
- **Server (API)**: `python main.py --api`
- **Agent (MCP)**: `python main.py --mcp`

---

## 📦 Building Releases

GramoVoice uses **PyInstaller** to create highly optimized, standalone executables for both Windows and Linux, bundling all necessary Kokoro engine files.

### 🐧 Linux (AppImage) & 🪟 Windows (EXE)
We provide a unified build script that automatically creates an optimized `.exe` on Windows or an `.AppImage` on Linux.

1. Create a clean Python `venv` and install requirements:
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the build script (Make sure to run it from the project root):
   ```bash
   bash build_app.sh
   # On Windows, you can also run it directly in Git Bash or WSL.
   ```

The script will:
- Bundle all necessary hidden imports (`PIL._tkinter_finder`, `soundfile`, etc.)
- Bundle Kokoro ONNX and Misaki dictionary data directly into the executable.
- Create an 80-100MB fully portable executable (compared to standard 3GB+ ML distributions).
- Output the files to the `dist/` directory (or the project root for AppImages).

---

## 🤖 MCP Integration
Add this to your Claude desktop config:
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

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!
Feel free to check out the [issues page](https://github.com/thiegocarvalho/gramovoice/issues).
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

---

## 📝 License
This project is [MIT](LICENSE) licensed.

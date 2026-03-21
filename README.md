# GramoVoice Studio Edition v1.2.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: PEP8](https://img.shields.io/badge/code%20style-pep8-green.svg)](https://www.python.org/dev/peps/pep-0008/)

A high-performance, professional Text-to-Speech (TTS) studio powered by **Kokoro ONNX**. Engineered for absolute stability and premium brand identity, optimized for PT-BR and English narration.

## ✨ Features
- **MCP Tooling**: Native Model Context Protocol support for AI assistants.
- **FastAPI Layer**: Robust backend with webhook support.

## 🚀 Quick Start

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

### 🪟 Windows (Portable EXE)
Use PyInstaller to bundle everything into a single file:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "assets:assets" --name "GramoVoice-Studio" main.py
```

### 🐧 Linux (AppImage)
On Linux/Ubuntu, use `linuxdeploy` with the python plugin:
1. Ensure `python-appimage` is configured.
2. Run the provided `build_app.sh` script (requires `linuxdeploy`).

---

## 🤖 MCP Integration
Add this to your Claude desktop config:
```json
{
  "mcpServers": {
    "gramovoice": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/gramovoice/main.py", "--mcp"]
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

#!/bin/bash

# GramoVoice Studio Edition - Build Script
# Optimized for Kokoro ONNX & Standard Tkinter

echo "🚀 Starting GramoVoice packaging (Studio Edition)..."

OS_TYPE="linux"
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OS" == "Windows_NT" ]]; then
    OS_TYPE="windows"
fi

echo "📦 Target Platform: $OS_TYPE"

if [ -d "venv" ]; then
    if [ "$OS_TYPE" == "windows" ]; then
        source venv/Scripts/activate || source venv/bin/activate
    else
        source venv/bin/activate
    fi
fi

# Ensure build requirements
pip install pyinstaller

rm -rf build dist

EXE_NAME="GramoVoice-Studio"
DATA_SEP=":"
if [ "$OS_TYPE" == "windows" ]; then
    DATA_SEP=";"
fi

echo "🏗️ Building $EXE_NAME for $OS_TYPE..."

# Get the activated python's site-packages directory
SITE_PACKAGES=$(python -c "import sysconfig; print(sysconfig.get_path('purelib'))")

# Build Standalone Executable
pyinstaller --noconfirm --onefile --windowed \
    --name "$EXE_NAME" \
    --paths "$SITE_PACKAGES" \
    --add-data "assets${DATA_SEP}assets" \
    `# Explicitly include package data for Kokoro ONNX and its G2P dependencies` \
    --add-data "${SITE_PACKAGES}/kokoro_onnx${DATA_SEP}kokoro_onnx" \
    --add-data "${SITE_PACKAGES}/misaki${DATA_SEP}misaki" \
    --add-data "${SITE_PACKAGES}/language_tags${DATA_SEP}language_tags" \
    --add-data "${SITE_PACKAGES}/espeakng_loader${DATA_SEP}espeakng_loader" \
    --add-data "${SITE_PACKAGES}/phonemizer${DATA_SEP}phonemizer" \
    --add-data "${SITE_PACKAGES}/imageio_ffmpeg${DATA_SEP}imageio_ffmpeg" \
    `# Hidden imports for Audio generation & Fast API servers` \
    --hidden-import "pydub" \
    --hidden-import "imageio_ffmpeg" \
    --hidden-import "soundfile" \
    --hidden-import "onnxruntime" \
    --hidden-import "huggingface_hub" \
    --hidden-import "kokoro_onnx" \
    --hidden-import "misaki" \
    --hidden-import "fastapi" \
    --hidden-import "uvicorn" \
    --hidden-import "pydantic" \
    `# Custom Tkinter helper for PIL logo loading` \
    --hidden-import "PIL._tkinter_finder" \
    --exclude-module "torch" \
    --exclude-module "torchvision" \
    --exclude-module "torchaudio" \
    --exclude-module "TTS" \
    --exclude-module "matplotlib" \
    --exclude-module "sklearn" \
    --exclude-module "pandas" \
    --icon "assets/ico.ico" \
    main.py

echo "✅ Build complete! Output located in 'dist/'."

if [ "$OS_TYPE" == "linux" ]; then
    echo "🐧 Automating AppImage generation..."
    
    # Use AppImageTool directly since PyInstaller already packaged all dependencies.
    if [ ! -f "./appimagetool" ]; then
        echo "⬇️ Downloading appimagetool..."
        wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool
        chmod +x appimagetool
    fi

    cat > GramoVoice.desktop <<EOF
[Desktop Entry]
Name=GramoVoice
Exec=GramoVoice-Studio
Icon=ico
Type=Application
Categories=AudioVideo;
Terminal=false
EOF

    echo "📦 Packaging AppDir..."
    mkdir -p AppDir/usr/bin
    cp dist/GramoVoice-Studio AppDir/usr/bin/
    cp assets/ico.png AppDir/ico.png
    cp GramoVoice.desktop AppDir/
    
    # Create simple AppRun script required by AppImage
    cat > AppDir/AppRun <<EOF
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\${0}")")"
exec "\${HERE}/usr/bin/GramoVoice-Studio" "\$@"
EOF
    chmod +x AppDir/AppRun

    export ARCH=x86_64
    export OUTPUT="GramoVoice-Studio-Linux-x86_64.AppImage"
    
    echo "🌟 Generating AppImage..."
    ./appimagetool AppDir "$OUTPUT"

    rm -rf GramoVoice.desktop AppDir
    echo "📦 AppImage created: $OUTPUT"
fi

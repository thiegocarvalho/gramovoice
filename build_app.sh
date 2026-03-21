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

# Build Standalone Executable
pyinstaller --noconfirm --onefile --windowed \
    --name "$EXE_NAME" \
    --add-data "assets${DATA_SEP}assets" \
    --hidden-import "pydub" \
    --hidden-import "soundfile" \
    --hidden-import "onnxruntime" \
    main.py

echo "✅ Build complete! Output located in 'dist/'."

if [ "$OS_TYPE" == "linux" ]; then
    echo "🐧 Automating AppImage generation..."
    
    if [ ! -f "./linuxdeploy-x86_64.AppImage" ]; then
        echo "⬇️ Downloading linuxdeploy..."
        wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
        chmod +x linuxdeploy-x86_64.AppImage
    fi
    if [ ! -f "./linuxdeploy-plugin-appimage" ]; then
        echo "⬇️ Downloading linuxdeploy appimage plugin..."
        wget -q https://github.com/linuxdeploy/linuxdeploy-plugin-appimage/releases/download/continuous/linuxdeploy-plugin-appimage-x86_64.AppImage -O linuxdeploy-plugin-appimage
        chmod +x linuxdeploy-plugin-appimage
    fi

    # Ensure plugins in current directory are found
    export PATH="$PATH:$(pwd)"

    cat > GramoVoice.desktop <<EOF
[Desktop Entry]
Name=GramoVoice
Exec=GramoVoice-Studio
Icon=gramovoice_logo_horizontal
Type=Application
Categories=AudioVideo;
Terminal=false
EOF

    export OUTPUT="GramoVoice-Studio-Linux-x86_64.AppImage"
    mkdir -p AppDir
    
    # Use linuxdeploy to create AppImage from the PyInstaller executable
    ./linuxdeploy-x86_64.AppImage \
        --appdir AppDir \
        --executable dist/GramoVoice-Studio \
        --desktop-file GramoVoice.desktop \
        --icon-file assets/gramovoice_logo_horizontal.png \
        --output appimage

    rm -rf GramoVoice.desktop AppDir
    echo "📦 AppImage created: $LDAI_OUTPUT"
fi

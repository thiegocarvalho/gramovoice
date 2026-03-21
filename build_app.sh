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
Icon=gramovoice_logo_horizontal
Type=Application
Categories=AudioVideo;
Terminal=false
EOF

    echo "📦 Packaging AppDir..."
    mkdir -p AppDir/usr/bin
    cp dist/GramoVoice-Studio AppDir/usr/bin/
    cp assets/gramovoice_logo_horizontal.png AppDir/
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
    ./appimagetool AppDir "\$OUTPUT"

    rm -rf GramoVoice.desktop AppDir
    echo "📦 AppImage created: $LDAI_OUTPUT"
fi

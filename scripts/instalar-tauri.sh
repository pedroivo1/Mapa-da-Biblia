#!/bin/sh
# Compila o app (Tauri) e instala só para o usuário atual: binário em
# ~/.local/bin e atalho no menu. Requer rust, webkit2gtk-4.1 e cargo-tauri.
set -e
cd "$(dirname "$0")/.."
cargo tauri build --no-bundle
install -Dm755 src-tauri/target/release/mapa-da-biblia ~/.local/bin/mapa-da-biblia
install -Dm644 frontend/icones/icone-512.png ~/.local/share/icons/mapa-da-biblia.png
cat > ~/.local/share/applications/mapa-da-biblia.desktop <<D
[Desktop Entry]
Type=Application
Name=Mapa da Bíblia
Exec=$HOME/.local/bin/mapa-da-biblia
Icon=mapa-da-biblia
Categories=Education;
D
chmod +x ~/.local/share/applications/mapa-da-biblia.desktop
kbuildsycoca6 >/dev/null 2>&1 || true
echo "Instalado. Procure 'Mapa da Bíblia' no menu."

#!/bin/zsh
set -euo pipefail
ROOT="${0:A:h:h}"
cd "$ROOT"
PYTHON="$ROOT/.venv/bin/python"
if [[ "$(uname -m)" != "arm64" ]]; then
  print -u2 'This build targets Apple Silicon (arm64).'
  exit 1
fi
if [[ ! -x "$PYTHON" ]]; then
  print -u2 'Create .venv with Python 3.12 and install packaging/requirements-macos.txt first.'
  exit 1
fi
"$PYTHON" packaging/prepare_macos.py
"$PYTHON" packaging/macos_icon.py
/usr/bin/iconutil -c icns build/macos-icon/PointLabStudio.iconset -o build/macos-icon/PointLabStudio.icns
"$PYTHON" -m PyInstaller --noconfirm packaging/PointLabStudio-macOS.spec
/usr/bin/codesign --verify --deep --strict dist/PointLabStudio.app
print "Built: $ROOT/dist/PointLabStudio.app"

#!/usr/bin/env bash
# ag-init Unix Bootstrap Installer
# Installs uv (if missing) and ag-init globally without requiring pre-installed Python.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Ysn4Irix/ag-init/main/install.sh | sh

set -e

echo "=================================================="
echo "        ag-init Unix Bootstrap Installer          "
echo "=================================================="

# 1. Check or install uv
if ! command -v uv &> /dev/null; then
    echo "[*] uv is not installed. Bootstrapping standalone uv..."
    echo "    (Astral uv requires zero pre-installed Python or root privileges)"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v uv &> /dev/null; then
    echo "[!] uv command could not be located in PATH."
    echo "    Please add ~/.local/bin to your PATH and re-run."
    exit 1
fi

echo "[+] uv is available: $(uv --version)"

# 2. Install ag-init
TARGET_REPO="${AG_INIT_REPO:-git+https://github.com/Ysn4Irix/ag-init.git}"
echo "[*] Installing ag-init from $TARGET_REPO..."

uv tool install --force "$TARGET_REPO"

echo ""
echo "[+] ag-init installed successfully!"
echo "[+] You can now run: ag-init --help"
echo ""

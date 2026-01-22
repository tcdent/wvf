#!/bin/bash
# Setup script for wsl-agent
# This script clones and patches codey dependencies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="$SCRIPT_DIR/vendor"

echo "Setting up wsl-agent dependencies..."

# Clone codey if not present
if [ ! -d "$VENDOR_DIR/codey" ]; then
    echo "Cloning codey..."
    mkdir -p "$VENDOR_DIR"
    git clone --depth 1 https://github.com/tcdent/codey.git "$VENDOR_DIR/codey"
else
    echo "Codey already cloned, updating..."
    cd "$VENDOR_DIR/codey"
    git pull --ff-only || true
    cd "$SCRIPT_DIR"
fi

# Apply patches in codey
echo "Applying codey patches..."
cd "$VENDOR_DIR/codey"

# Run the genai patch
if [ ! -f "lib/genai/.patched" ]; then
    echo "Patching genai..."
    bash lib/patches/genai/apply.sh
fi

echo "Setup complete!"
echo ""
echo "You can now build with: cargo build"

#!/bin/bash
# Build script for Sniffixx release
# Creates clean distributable package

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building Sniffixx release..."

# Copy required files
cp "$SOURCE_DIR/sniffixx.sh" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/install.sh" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/auto_select.exp" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/opcapture.py" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/rs_autoscan.sh" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/target_capture.py" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/wpsbt.py" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/wpshift.py" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/wscan.py" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/VERSION" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/README.md" "$SCRIPT_DIR/"
cp "$SOURCE_DIR/LICENSE" "$SCRIPT_DIR/"

# Make scripts executable
chmod +x "$SCRIPT_DIR/sniffixx.sh"
chmod +x "$SCRIPT_DIR/install.sh"
chmod +x "$SCRIPT_DIR/rs_autoscan.sh"
chmod +x "$SCRIPT_DIR/auto_select.exp"

echo "Release built in live/"
echo "Files: $(ls -1 "$SCRIPT_DIR" | wc -l)"

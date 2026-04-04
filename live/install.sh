#!/bin/bash
set -euo pipefail

# Sniffixx Installer
# Usage: ./install.sh [--uninstall]

# Get script directory dynamically (must be first)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VERSION=$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "1.0.0")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default installation paths
INSTALL_TARGET="/usr/local/bin"
WORKDIR="/sniffixx"

# Parse arguments
UNINSTALL=false
if [[ "${1:-}" == "--uninstall" ]]; then
    UNINSTALL=true
fi

if [[ "$UNINSTALL" == "true" ]]; then
    echo -e "${YELLOW}Uninstalling Sniffixx...${NC}"
    rm -f "$INSTALL_TARGET/sniffixx"
    rm -rf "$WORKDIR"
    echo -e "${GREEN}Sniffixx uninstalled successfully.${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}Sniffixx - Network Auditing Toolkit for NetHunter${NC}"
echo "==========================================================="
echo "Version: $VERSION"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}ERROR: This installer must be run as root (use sudo).${NC}"
    exit 1
fi

# Dependency checking
echo -e "${YELLOW}Checking dependencies...${NC}"
missing_deps=()

check_dep() {
    local cmd="$1"
    local pkg="${2:-$cmd}"
    if ! command -v "$cmd" &>/dev/null; then
        missing_deps+=("$pkg")
        return 1
    fi
    echo -e "  ${GREEN}✓${NC} $cmd"
    return 0
}

# Core dependencies
check_dep "airodump-ng" "aircrack-ng"
check_dep "hcxdumptool"
check_dep "hcxpcapngtool" "hcxtools"
check_dep "reaver"
check_dep "hashcat"
check_dep "nmap"
check_dep "python3"

# Optional but recommended
check_dep "aireplay-ng" || true
check_dep "mdk4" || true
check_dep "tcpdump" || true
check_dep "tshark" || true
check_dep "macchanger" || true

if [[ ${#missing_deps[@]} -gt 0 ]]; then
    echo ""
    echo -e "${RED}Missing required dependencies:${NC}"
    for dep in "${missing_deps[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo -e "${YELLOW}Install them with: apt install <package>${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Creating directory structure...${NC}"

# Create workdir
mkdir -p "$WORKDIR"
mkdir -p "$WORKDIR/hs"
mkdir -p "$WORKDIR/wps"
mkdir -p "$WORKDIR/dump"
mkdir -p "$WORKDIR/dump/tcp"
mkdir -p "$WORKDIR/dump/pmkid"
mkdir -p "$WORKDIR/dump/tshark"
mkdir -p "$WORKDIR/dump/22000"
mkdir -p "$WORKDIR/logs"

echo -e "${YELLOW}Installing files...${NC}"

# Copy main script
cp "$SCRIPT_DIR/sniffixx.sh" "$INSTALL_TARGET/sniffixx"
chmod +x "$INSTALL_TARGET/sniffixx"
echo -e "  ${GREEN}✓${NC} Installed: $INSTALL_TARGET/sniffixx"

# Copy Python scripts
for script in wscan.py wpsbt.py opcapture.py target_capture.py wpshift.py; do
    if [[ -f "$SCRIPT_DIR/$script" ]]; then
        cp "$SCRIPT_DIR/$script" "$WORKDIR/"
        echo -e "  ${GREEN}✓${NC} Installed: $WORKDIR/$script"
    fi
done

# Copy bash scripts
if [[ -f "$SCRIPT_DIR/rs_autoscan.sh" ]]; then
    cp "$SCRIPT_DIR/rs_autoscan.sh" "$WORKDIR/"
    chmod +x "$WORKDIR/rs_autoscan.sh"
    echo -e "  ${GREEN}✓${NC} Installed: $WORKDIR/rs_autoscan.sh"
fi

# Copy expect script
if [[ -f "$SCRIPT_DIR/auto_select.exp" ]]; then
    cp "$SCRIPT_DIR/auto_select.exp" "$WORKDIR/"
    chmod +x "$WORKDIR/auto_select.exp"
    echo -e "  ${GREEN}✓${NC} Installed: $WORKDIR/auto_select.exp"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Run Sniffixx with: sniffixx"
echo ""
echo -e "${YELLOW}NOTE:${NC} oneshot.py is required for WPS attacks."
echo "Set the SNX_ONESHOT environment variable to its location:"
echo "  export SNX_ONESHOT=/path/to/oneshot.py"
echo "Or ensure it exists at /sdcard/nh_files/modules/oneshot.py"
echo ""
echo "Uninstall with: sudo $SCRIPT_DIR/install.sh --uninstall"
echo ""

exit 0

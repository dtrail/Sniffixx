#!/bin/bash

# Paths based on your setup
RSF_DIR="/root/routersploit"
VENV_DIR="$RSF_DIR/venv"
RSF="$RSF_DIR/rsf.py"

echo "Available interfaces:"
ip -o link show | awk -F': ' '{print $2}' | grep -v lo

read -p "Enter the interface to use for Nmap scan: " iface


# Prompt for subnet
read -p "Enter subnet to scan (e.g. 192.168.1.0/24): " SUBNET
SUBNET=${SUBNET:-192.168.1.0/24}

echo "[*] Scanning for live hosts on $SUBNET..."
LIVE_HOSTS=$(nmap -e "$iface" -sn "$SUBNET" -oG - | awk '/Up$/{print $2}')

if [ -z "$LIVE_HOSTS" ]; then
    echo "[!] No live hosts found. Exiting."
    exit 1
fi

# Convert to newline-separated list
TARGET_LIST=$(echo "$LIVE_HOSTS" | sort)

echo "[*] Found live hosts:"
echo "$TARGET_LIST"
echo "[*] Activating RouterSploit virtual environment..."

# Activate venv
source "$VENV_DIR/bin/activate"

# Display instructions for the user
echo
echo "===================================================================="
echo "🛠️  Paste the following commands into the RouterSploit shell line by line."
echo "* Keep in mind that you have to repeat the 'set target' step for every single IP you want to scan."
echo "  Replace X with one of the IPs listed below."
echo
echo "EXAMPLE:"
echo "  set target 192.168.2.1"
echo
echo "- COPY, PASTE, ENTER:"
echo "  use scanners/routers/router_scan"
echo
echo "- COPY, PASTE, ENTER:"
echo "  set target X"
echo
echo "- COPY, PASTE, ENTER:"
echo "  run"
echo
echo "IPs found (replace X with one of these):"
echo

# Print each IP on its own line
echo "$TARGET_LIST"
echo "===================================================================="
echo

# Launch RouterSploit shell
read -p "Press Enter to launch RouterSploit shell..." dummy
python3 "$RSF"

# Ask if user wants to stay in the shell again
read -p "Do you want to re-enter the RouterSploit shell? [y/N]: " stay
if [[ "$stay" =~ ^[Yy]$ ]]; then
    echo "[*] Re-entering interactive RouterSploit shell..."
    python3 "$RSF"
else
    echo "[*] Exiting. Deactivating virtual environment."
    deactivate
fi

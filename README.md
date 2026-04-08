# Sniffixx

**Network Auditing Toolkit for Kali NetHunter**

```
  ____        _  __ _  __ _       
 / ___| _ __ (_)/ _(_)/ _(_)_  __
 \___ \| '_ \| | |_| | |_| \ \/ /
  ___) | | | | |  _| |  _| |>  < 
 |____/|_| |_|_|_| |_|_| |_/_/\_\
        S N I F F I X X
```

A comprehensive WiFi auditing toolkit designed for Kali NetHunter. Scan, capture, crack, and analyze — all from a single terminal menu.

## Features

- **WiFi Adapter Management** — List, select, and manage WiFi adapters
- **Network Scanning** — Discover nearby networks with airodump-ng
- **Handshake Capture** — Capture WPA/WPA2 handshakes
- **PMKID Capture** — Extract PMKIDs with hcxdumptool
- **Hash Cracking** — Crack with hashcat or John the Ripper
- **WPS Attacks** — Pixie Dust, Brute Force, and more via oneshot.py
- **Packet Sniffing** — tcpdump and tshark integration
- **Captive Portal Bypass** — Connect and bypass captive portals
- **Router Exploitation** — RouterSploit integration
- **Credential Management** — Track and manage cracked credentials

## Requirements

### Hardware
- Kali NetHunter (Android with Termux)
- WiFi adapter supporting monitor mode
- Root access required

### Software Dependencies
```
airodump-ng (aircrack-ng)
hcxdumptool
hcxpcapngtool
reaver
hashcat
python3
```

### Optional
```
aireplay-ng (aircrack-ng)
mdk4
tcpdump
tshark
macchanger
nmap
```

## Installation

### Quick Install
```bash
git clone https://github.com/dtrail/sniffixx.git
cd sniffixx
chmod +x install.sh
sudo ./install.sh
```

### Manual Install
```bash
# Copy files
sudo cp sniffixx.sh /usr/local/bin/sniffixx
chmod +x /usr/local/bin/sniffixx

# Copy supporting files
mkdir -p /sniffixx
cp *.py /sniffixx/
cp *.sh /sniffixx/
cp *.exp /sniffixx/

# Create directories
mkdir -p /sniffixx/{hs,wps,dump,dump/{tcp,pmkid,tshark,22000},logs}
```

### Environment Variables
```bash
# For WPS attacks with oneshot.py
export SNX_ONESHOT=/path/to/oneshot.py
```

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/dtrail/sniffixx.git
   cd sniffixx
   ```

2. Install:
   ```bash
   chmod +x install.sh
   sudo ./install.sh
   ```

3. Run:
   ```bash
   sniffixx
   ```

4. Select your WiFi adapter from the menu
5. Choose your attack vector (scan, capture, crack, etc.)

## Usage

### Start Sniffixx
```bash
sniffixx
```

### Command Line Options
```bash
sniffixx --help     # Show help
sniffixx --version  # Show version
```

### Screenshots

*Screenshots coming soon*

Current terminal output includes:
- ASCII banner on startup
- Colored menu system
- Progress indicators during attacks
- Result summaries after operations

### Main Menu Options

| Option | Description |
|--------|-------------|
| 1 | List WiFi adapters |
| 2 | Select WiFi adapter |
| 3 | Sniff with tcpdump |
| 4 | Sniff with tshark |
| 5 | Capture PMKID |
| 6 | Convert pcapng to hashcat format |
| 7 | Crack PMKID |
| 8 | Scan WPS networks |
| 9 | WPS Special Brute Force |
| 10 | Monitor mode menu |
| 11 | Handshake grabber menu |
| 12 | Connect to cracked network |
| 13 | Manage credentials |
| 14 | Bypass captive portal |
| 15 | RouterSploit autoscan |
| W | WPS attack environment |
| D | Dump all networks |

## Workflow Example

1. **Select Adapter**: Choose your WiFi adapter
2. **Scan Networks**: Use option 1 or 11 to discover networks
3. **Capture Handshake/PMKID**: Use options 5 or 11
4. **Convert**: Convert captures to hashcat format (option 6)
5. **Crack**: Use hashcat or john to crack (option 7)

## Configuration

### Working Directory
Default: `/sniffixx`

### Log Directory
Default: `/sniffixx/logs`

Session logs and results are saved here.

## ⚠️ Disclaimer

**FOR AUTHORIZED PENETRATION TESTING ONLY**

This tool is designed exclusively for:
- Security researchers conducting authorized assessments
- Penetration testers with explicit client authorization
- Network administrators testing their own infrastructure
- Bug bounty researchers with in-scope targets

### Legal Requirements

**You MUST have explicit, written permission from the network owner before using this tool on any network.**

Unauthorized access to computer systems is illegal in most jurisdictions. This includes:
- Accessing WiFi networks without authorization
- Capturing network traffic without consent
- Attempting to crack passwords without permission

### Ethical Guidelines

- Only test networks you own or have written authorization to test
- Report all vulnerabilities to the appropriate parties
- Do not use this tool for malicious purposes
- Respect the privacy and security of others

### Liability

The authors and contributors of Sniffixx are not responsible for misuse of this tool.
By using Sniffixx, you accept full responsibility for your actions.

## License

MIT License — see [LICENSE](LICENSE) file for details.

## Credits

- **Author**: dtrail / d33ph@ntom / Godis
- **Inspired by**: Various NetHunter tools and pentesting frameworks

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Links

- [RouterSploit](https://github.com/reverse-shell/routersploit)
- [OneShot](https://github.com/deltaclock/oneshot)
- [aircrack-ng](https://www.aircrack-ng.org/)
- [hcxdumptool](https://github.com/ZerBea/hcxdumptool)

---

*For educational and authorized testing purposes only.*

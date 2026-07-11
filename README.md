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
### NOTE: This is a WIP! Some features are not entirely ready or implemented. Bugs are likely to happen.


A comprehensive WiFi auditing toolkit designed for Kali NetHunter, leveraging existing Kali tools for easier usage. Aimed at beginners and advanced users.
Scan, capture, crack, and analyze — all from a single terminal menu.

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
- **Automatic Wordlist Building** — Starting with a default rockyou.txt, with every cracked network your wordlist gets bigger
- **Network Mapping And Maintaining Access** — Diverse network scanning and maintenance after gaining access
- **Vulnerabilities Identification** — Find additional entry points to connected devices


## Requirements

### Hardware
- Kali NetHunter 2025.X (NOT rootless / Termux!)
- WiFi adapter supporting monitor mode & packet injection (requires kernel support and related firmware)
- Root access required!

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
sudo cp sniffixx-cli.sh /usr/local/bin/sniffixx-cli
chmod +x /usr/local/bin/sniffixx-cli

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
   sniffixx-cli
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
sniffixx-cli     # Show help
sniffixx-cli --help     # Show help
sniffixx-cli --version  # Show version
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


## Workflow Example WITHOUT monitor mode! 

1. **Select Adapter**: Choose your WiFi adapter (for now you need to type the given adapter name, not the number)
2. **Scan Networks**: Use option w to enter WPS Attack Environment and try first with Pixie Dust. 
3. **Crack WIFI**: d-link, Vodafone and TP-Link routers are often vulnerable. 
4. **Credentials** will be saved automatically to a set path (notified in terminal) 
5. **Connect**: Use option 12 to connect. It will mark any cracked AP in the list after scanning. 
6. **Subnet scan**: Sniffixx Automatically probes for IPs and devices. Select an appropriate option when shown. Copy the subnet Adress that is listed near your selected wifi adapter. For best results use option 3 for an aggressive stealth scan (careful, though! Could leave traces.)
7. **Router Exploitation**: use the then given option to router exploitation via Routersploit. Either Option 15 or elevated from option 12, executes an automated Nmap scan and provides you with usable IPs to work with in Routersploit, which will be opened for you.


## Configuration

### Working Directory
Default: `/sniffixx`

### Log Directory
Default: `/sniffixx/logs`

Session logs and results are saved here.



## To-Do

- ✅ Fix command arguments for Reaver and OneShot
- ✅ Fix bug in "WPS Special Bruteforce" and add an additional method for PIN attempts (leveraging Reaver/Bully in an uncommon way to test PINs on WPS enabled APs showed to be pretty reliable when used with a proper list. Implement grace periods for routers locking themselves during the process. This way proved to be more reliable, even faster than OneShot's online-bruteforce in some cases)
- ✅ Fix binary naming to fix naming conflict with the working dir
- ✅ Fix / Extend the Captive Portal Bypass process (currently working, but requires a bit of advanced knowledge. I'll make it easier to use)
- Implement modular extensions support (partially ready, though not yet implemented)
- Options for lateral movement beyond exploiting routers/devices and network mapping
- Add a self-extending viewable list for so-far unknown exploitable router models, and implement it to OneShot's vuln-list.*
- Implement custom WPS "cracking method" (more of a combination of known methods, but increase success rates by at least 20% for WPS enabled APs)

* I've cracked a pretty large number of APs that weren't/aren't known to any public list using Sniffixx only.



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

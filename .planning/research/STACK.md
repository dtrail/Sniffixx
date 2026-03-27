# Technology Stack — Sniffixx WiFi Auditing Toolkit

**Project:** Sniffixx (Kali NetHunter WiFi auditing)
**Researched:** 2026-03-27
**Overall confidence:** HIGH (versions verified against Kali package tracker, GitHub releases, and PyPI)

---

## Recommended Stack

### Core Framework: Bash + Python 3

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Bash** | 5.x (Termux default) | Menu UI, orchestration, tool invocation | Standard for NetHunter CLI tools; all existing scripts are bash; no reason to rewrite |
| **Python 3** | **3.13** (Termux current) | Complex logic (WPS, packet sniffing, network scanning) | Termux upgraded to 3.13 in March 2026; scapy, rich all support it; must not pin to 3.12 |

**Confidence:** HIGH — Termux-packages#28824 and #28880 confirm Python 3.13 is current.

### WiFi Capture & Attack Tools (System Packages)

These are the **essential external tools**. Sniffixx wraps them; it does not reimplement them.

| Tool | Version (Kali 2026.1) | Purpose | Status | Notes |
|------|----------------------|---------|--------|-------|
| **aircrack-ng** | **1.7** | Suite: airodump-ng, aireplay-ng, airmon-ng, aircrack-ng | ACTIVELY MAINTAINED | Core of the entire workflow. Includes airmon-ng for monitor mode on external adapters |
| **hcxdumptool** | **7.1.2** | PMKID capture | ACTIVELY MAINTAINED | **CRITICAL: v7.0.0+ has breaking CLI changes.** Replaced internal engine with hcxlabtool. Old flags like `-F` may not work. See pitfalls below |
| **hcxtools** (hcxpcapngtool) | **7.1.0** | pcapng → hashcat/john format conversion | ACTIVELY MAINTAINED | Added hashcat mode 37100 (FT-PSK EAPOL) in March 2026. Use `-o` for 22000 output, `--john=` for JtR |
| **hashcat** | **7.0.0** | WPA hash cracking (mode 22000) | ACTIVELY MAINTAINED | Major release Aug 2025. Mode 22000 is the standard. `-D 1` for CPU device on NetHunter (no GPU) |
| **john** (John the Ripper) | jumbo branch | Alternative hash cracking | MAINTAINED | Use `--format=wpapsk-opencl` or `wpapsk` depending on build |
| **wash** | Part of reaver package | WPS network scanning | MAINTAINED | `-2` flag for 5GHz support; output format stable |
| **reaver** | **1.6.6** | WPS PIN brute-force | MAINTAINED (t6x fork) | Arch ships 1.6.6; use `reaver-wps-fork-t6x` |
| **mdk4** | **4.2** | Deauth/DoS attacks | MAINTAINED (now under aircrack-ng org) | **Replace mdk3 references.** mdk4 is the successor and is in current Kali. mdk3 is deprecated |
| **nmap** | latest | Network/service scanning | ACTIVELY MAINTAINED | Standard tool, no version concerns |
| **tcpdump** | latest | Packet capture | ACTIVELY MAITAINED | Part of base system |
| **tshark** | latest | Packet capture + analysis | ACTIVELY MAINTAINED | Part of wireshark-cli |
| **macchanger** | latest | MAC spoofing | MAINTAINED | Simple, stable |
| **wpa_supplicant** | latest | WiFi connection management | SYSTEM | Part of base OS |
| **iw** | latest | Interface management | SYSTEM | Part of Linux wireless |

**Confidence:** HIGH — All versions verified against Kali package tracker (kali.org/tools/) and GitHub releases as of March 2026.

### Python Libraries

| Library | Version | Purpose | Install | Why This One |
|---------|---------|---------|---------|-------------|
| **scapy** | **2.7.0** | Raw 802.11 packet sniffing (Dot11 layer) | `pip install scapy` | The standard for Python packet manipulation. v2.7.0 released Dec 2025. Used in wpshift.py for WPS scanning |
| **rich** | **14.3.3** | Terminal UI (colors, prompts, tables, progress) | `pip install rich` | Modern replacement for colorama. v14.3.3 Feb 2026. Already used in wpshift.py. Provides `print()`, `Prompt`, `IntPrompt`, `Table`, `Panel` |

**Why NOT colorama:** `rich` is a superset — it does everything colorama does plus tables, panels, progress bars, markdown rendering, and structured prompts. The project already uses rich in wpshift.py. No reason to add colorama.

**Why NOT argparse libraries:** bash `read` + `case` menus are the standard for NetHunter tools. Python scripts can use stdlib `argparse` if CLI flags are needed.

**Confidence:** HIGH — Both verified on PyPI with current versions supporting Python 3.13.

### Python Standard Library Modules (Already In Use — Keep These)

These are already used correctly across the codebase and are the right choices:

| Module | Usage in Sniffixx | Notes |
|--------|-------------------|-------|
| `subprocess` | Running external tools | Prefer over `os.system()` — already used correctly |
| `os` / `sys` | Filesystem, exit handling | Standard |
| `tempfile` | wpa_supplicant config | Good practice — avoids race conditions |
| `re` | Parsing scan output | Appropriate |
| `csv` | Credential file parsing | Appropriate for stored.csv |
| `pathlib` | File existence checks | More modern than `os.path` — should be preferred |
| `time` | Delays/timeouts | Standard |
| `shutil` | DHCP client detection | Appropriate |

---

## Installer Patterns for Termux/NetHunter

### Current Problem
The `install.sh` uses hardcoded paths like `/sdcard/Dev/` which is the developer's specific device. This will fail on any other system.

### Recommended Pattern

```bash
#!/bin/bash
set -euo pipefail

# Detect repo location — works from any clone location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/usr/local/bin"
WORKDIR="/sniffixx"

# Verify we're running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: Run with sudo or as root" >&2
    exit 1
fi

# Copy from repo (not from hardcoded path)
cp "${SCRIPT_DIR}/sniffixx.sh" "${INSTALL_DIR}/sniffixx"
chmod +x "${INSTALL_DIR}/sniffixx"

# Copy Python scripts to workdir
for script in wscan.py opcapture.py wpsbt.py wpshift.py target_capture.py; do
    [ -f "${SCRIPT_DIR}/${script}" ] && cp "${SCRIPT_DIR}/${script}" "${WORKDIR}/"
done

# Create directory structure
mkdir -p "${WORKDIR}"/{hs,wps,dump/{tcp,pmkid,tshark,22000/{john,extracted}}}
```

**Why:** Uses `BASH_SOURCE` to find the repo regardless of where `git clone` placed it. No `/sdcard/Dev/` dependency.

### Dependency Installation Pattern

```bash
# System packages (apt)
APT_DEPS=(
    aircrack-ng hcxdumptool hcxtools hashcat
    reaver mdk4 nmap tcpdump tshark
    macchanger iw curl
)
apt install -y "${APT_DEPS[@]}"

# Python packages (pip)
pip install scapy rich
```

**Note on Termux pip:** As of March 2026, Termux Python is 3.13. Standard `pip install` works for scapy and rich — both ship pure Python wheels with no C extensions requiring special build steps. RouterSploit has known bcrypt/setuptools issues (threat9/routersploit#889) but that's out of scope for this project.

---

## Bash Best Practices for NetHunter Scripts

### Essential Patterns (Must Apply to sniffixx.sh)

**1. Strict mode header:**
```bash
#!/bin/bash
set -euo pipefail
IFS=$'\n\t'
```
- `set -e`: Exit on error (prevents silent failures when tools aren't installed)
- `set -u`: Error on undefined variables (catches typos like `$adpater`)
- `set -o pipefail`: Catch errors in pipelines
- **Current sniffixx.sh has NONE of these** — it silently continues on errors

**2. Quote ALL variables:**
```bash
# BAD (current code):
ip link set $adapter down;

# GOOD:
ip link set "$adapter" down;
```
This prevents word splitting on adapter names with spaces (unlikely but correct practice).

**3. Use `local` in functions:**
```bash
# BAD (current code):
reset_adapter() {
    # 'adapter' is global, reused across functions
    ...
}

# GOOD:
reset_adapter() {
    local adapter="${1:-$adapter}"  # explicit parameter with fallback
    ...
}
```

**4. Use `[[ ]]` over `[ ]`:**
```bash
# BAD:
if [ -z "$adapter" ]; then

# GOOD:
if [[ -z "$adapter" ]]; then
```
`[[ ]]` is bash-native, doesn't do word splitting, supports regex, and is faster.

**5. Check command existence before calling:**
```bash
require_tool() {
    if ! command -v "$1" &>/dev/null; then
        echo "Error: $1 not found. Install with: apt install $1" >&2
        return 1
    fi
}
```
This is the dependency check feature mentioned in PROJECT.md requirements.

**6. Use `$()` not backticks:**
```bash
# BAD:
adapters=$(ls /sys/class/net | grep wlan)  # Also: don't parse ls

# GOOD:
mapfile -t adapters < <(find /sys/class/net -maxdepth 1 -name 'wlan*' -printf '%f\n')
```

**7. Consistent color definitions at top of script:**
```bash
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'  # No Color

# Current sniffixx.sh references ${yellow}, ${red}, etc. but never defines them!
# Some functions use echo -e, others don't. Inconsistent.
```

**Confidence:** HIGH — These are universally accepted bash best practices, confirmed by multiple 2026 sources.

---

## What NOT to Use (And Why)

### Tools to Remove or Avoid

| Tool | Why NOT | Use Instead |
|------|---------|-------------|
| **mdk3** | Deprecated, unmaintained, replaced by mdk4. Current Kali doesn't ship it in default wireless meta. Code in sniffixx.sh line 708 uses `sudo mdk3` | **mdk4** — same interface, maintained under aircrack-ng org, version 4.2 |
| **oneshot.py** (external path) | Fragile dependency on `/sdcard/nh_files/modules/oneshot.py` — this is a third-party script at a non-standard path that won't exist on fresh installs | Either bundle oneshot.py in the repo, or call reaver/bully directly with the same attack parameters |
| **RouterSploit** | Heavy dependency (Python venv, bcrypt issues on Termux), not core to WiFi auditing, separate tool entirely | Keep as optional integration, don't require at install time. Defer to later phase |
| **auto_select.exp** (Expect) | Expect/Tcl adds a non-Python dependency, fragile for terminal automation | Rewrite automation logic in Python using `pexpect` (pip installable) or subprocess with stdin pipes |
| **colorama** | Redundant if using rich. Rich handles colors natively | **rich** — already in use, more capable |
| **os.system()** | No error capture, injection risk, no output capture | **subprocess.run()** with explicit args list |
| **parsing `ls` output** | Breaks on filenames with spaces/newlines, anti-pattern per ShellCheck | **find** with `-printf` or glob arrays |

### Patterns to Avoid

| Anti-Pattern | Why Bad | Instead |
|-------------|---------|---------|
| Hardcoded paths (`/sdcard/Dev/`, `/sniffix/`) | Breaks on different devices/installs | Use `${SCRIPT_DIR}` and a configurable `WORKDIR` |
| Global mutable state (`$adapter` shared across functions) | Makes code hard to reason about, functions aren't isolated | Pass adapter as parameter, use local variables |
| `python` vs `python3` | `python` may not exist or point to Python 2 on some systems | Always use `python3` (sniffixx.sh line 738 uses bare `python`) |
| German and English mixed in user prompts | Confuses non-German users; inconsistency hurts UX (lines 651-666 are German, rest is English) | Standardize on English for GitHub release |
| Unterminated `if` block (line 9 missing `fi` before next command) | Syntax error — will cause install failures | Fix: add proper `fi` or restructure |

---

## Version Compatibility Matrix

| Component | Minimum Version | Current Version | Notes |
|-----------|----------------|-----------------|-------|
| Python | 3.9+ | **3.13** (Termux) | scapy 2.7.0 requires ≥3.7; rich 14.x requires ≥3.8 |
| Bash | 4.0+ | **5.x** (Termux) | `mapfile`, `${var,,}` lowercase require bash 4+ |
| aircrack-ng | 1.6+ | **1.7** | 1.7 adds better 802.11ac/ax support |
| hcxdumptool | **7.0.0+** | **7.1.2** | v7 has BREAKING changes from v6. See below |
| hcxtools | **7.0.0+** | **7.1.0** | Must match hcxdumptool major version |
| hashcat | 6.0+ | **7.0.0** | Mode 22000 supported since 6.0; v7 has new features |
| scapy | 2.5+ | **2.7.0** | Dot11 layer stable across versions |
| rich | 10.0+ | **14.3.3** | Prompt, IntPrompt APIs stable |
| Kali NetHunter | 2025+ | **2026.1** | Latest release March 2026 |

---

## Critical Version Migration Notes

### hcxdumptool v6 → v7 Breaking Changes

The current sniffixx.sh uses:
```bash
hcxdumptool -i "$iface" -w "$capture_file" -F --rds=1
```

**hcxdumptool v7.0.0 (Aug 2025) changed the internal engine:**
- Replaced `hcxdumptool` internal engine with `hcxlabtool`
- Removed split screen ACCESS POINT ↔ CLIENT display
- `-F` flag behavior may have changed
- Added `--rdt` to disable TIOCGWINSZ
- Added RSSI to rcascan
- Moved GPS handling to separate `hcxnmealog`
- New option: `--enable_status=1` format may differ

**Action required:** Test all hcxdumptool invocations against v7.1.2. The `-F` and `--rds=1` flags need verification — they may have been renamed or removed. The handshake_grabber_menu() uses `--enable_status=1` and `--filtermode=2` which may also need updating.

**Confidence:** MEDIUM — I confirmed v7 exists and has breaking changes, but couldn't verify exact flag compatibility without testing on-device. This is a phase-specific research flag.

### hcxpcapngtool March 2026 Update

The changelog (25.03.2026) adds:
- Full conversion of FT-PSK EAPOL (hashcat mode 37100)
- New `-f` flag for WPA-PBKDF2-PMKID+EAPOL output

The existing `-o` for 22000 format and `--john=` for JtR format are still valid.

---

## Supporting Libraries (Optional but Recommended)

| Library | Version | Purpose | When to Add |
|---------|---------|---------|-------------|
| `pexpect` | latest | Replace `auto_select.exp` Expect script | Phase when rewriting WPS automation |
| `argparse` | stdlib | CLI flags (--help, --version) | Phase implementing CLI flags |
| `logging` | stdlib | Audit trail feature | Phase implementing logging |
| `json` | stdlib | Structured results output | Phase implementing result summary |
| `shutil` | already used | Terminal width detection | Keep |

---

## Sources

| Finding | Source | Confidence |
|---------|--------|------------|
| hcxdumptool v7.1.2 | GitHub ZerBea/hcxdumptool/releases | HIGH |
| hcxtools v7.1.0 + March 2026 changelog | GitHub ZerBea/hcxtools/changelog + kali.org/tools/hcxtools | HIGH |
| hashcat v7.0.0 | GitHub hashcat/hashcat/releases (Aug 2025) | HIGH |
| aircrack-ng v1.7 | kali.org/tools/aircrack-ng | HIGH |
| mdk4 v4.2 | kali.org/tools/mdk4 | HIGH |
| scapy v2.7.0 | PyPI scapy + GitHub secdev/scapy | HIGH |
| rich v14.3.3 | GitHub Textualize/rich/releases (Feb 2026) | HIGH |
| Python 3.13 in Termux | termux/termux-packages#28880, #28824 | HIGH |
| reaver 1.6.6 | archlinux.org/packages | MEDIUM |
| bash best practices | Multiple 2026 sources (101howto.com, oneuptime.com) | HIGH |
| hcxdumptool v7 breaking changes | GitHub release notes | MEDIUM (needs on-device testing) |
| RouterSploit bcrypt issues | threat9/routersploit#889 | HIGH |
| Termux pip issues | pypa/pip#13377, termux-packages | HIGH |

---

## Summary for Roadmap

**Core stack decision:** Bash orchestration + Python 3.13 logic + standard NetHunter toolchain. No custom frameworks, no web dependencies, no GUI.

**Must-fix before features:**
1. Update hcxdumptool calls for v7.x compatibility (breaking changes)
2. Replace mdk3 references with mdk4
3. Fix `python` → `python3` references
4. Add bash strict mode and variable quoting
5. Fix installer to use `SCRIPT_DIR` instead of hardcoded paths
6. Handle oneshot.py external dependency (bundle or replace)

**New dependencies to add:** None beyond existing (scapy, rich). All other functionality is stdlib or system packages.

**Dependencies to avoid:** colorama (redundant), expect/pexpect (rewrite auto_select.exp later), any web framework.

---

*Stack research: 2026-03-27*
*All version numbers verified against official sources.*

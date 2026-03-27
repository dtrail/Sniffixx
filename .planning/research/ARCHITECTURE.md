# Architecture Patterns: Sniffixx Refactoring

**Domain:** NetHunter WiFi pentesting CLI toolkit
**Researched:** 2026-03-27
**Overall confidence:** HIGH

## Current Architecture Assessment

### What Exists Now

Sniffixx is a **monolithic single-file bash orchestrator** pattern:

```
sniffixx.sh (910 lines)
├── Global state ($adapter, $workdir)
├── 16 inline bash functions (lines 23-802)
├── Main menu dispatch loop (lines 804-910)
├── Calls out to 5 Python scripts
├── Calls out to 1 shell script
└── References 1 expect script (commented out)
```

**Problems identified:**
1. **910-line monolith** — all business logic in one file, impossible to test or maintain in isolation
2. **Global mutable state** — `$adapter` shared across all functions with fragile `[ -z "$adapter" ]` guards
3. **Undefined variables** — color codes (`$yellow`, `$nc`), `$handshake_dir`, `$pmkid_dir`, `$bssid`, `$essid` referenced but never defined
4. **Hardcoded paths** — workdir `/sniffixx/`, PIN file `/sniffix/wps_pins.txt` (typo), installer source `/sdcard/Dev/`
5. **No separation of concerns** — UI rendering, business logic, external tool invocation, error handling all interleaved
6. **Duplicated WPS functionality** — `wpsbt.py` and `wpshift.py` have their own menus but are never called from main script; inline `wps_crack()` and `pixie_dust_menu()` do the same jobs differently
7. **Orphaned code** — `hs.sh` is never called; `auto_select.exp` is commented out
8. **No `local` keyword usage** — all variables leak to global scope

### Verdict vs Best Practices

| Dimension | Current State | Best Practice | Gap |
|-----------|--------------|---------------|-----|
| File organization | Single 910-line file | Modular files by domain | Critical |
| State management | Global variables | Passed parameters or config file | Critical |
| Function scope | No `local` usage | Always `local` for function vars | High |
| Naming convention | No prefix, collisions possible | Prefix pattern (e.g., `sn_`) | Medium |
| Error handling | Ad-hoc echo messages | Consistent logging, return codes | High |
| Configuration | Hardcoded paths | Config file or env vars | High |
| External tool interface | Inline calls mixed with logic | Wrapper functions with validation | Medium |

---

## Recommended Architecture

### Core Pattern: Thin Orchestrator + Domain Modules

Apply the **Strangler Fig pattern** adapted for bash: keep `sniffixx.sh` as a thin dispatcher, extract domain logic into sourced library files. This is the established pattern for modular bash (see: "Designing Modular Bash" by Kromg, 2025).

```
sniffixx.sh (thin orchestrator: ~120 lines)
├── source lib/core.sh         (shared utilities, config, logging)
├── source lib/adapters.sh     (adapter management)
├── source lib/monitor.sh      (monitor mode lifecycle)
├── source lib/pmkid.sh        (PMKID pipeline)
├── source lib/wps.sh          (WPS attacks)
├── source lib/handshake.sh    (handshake capture)
├── source lib/capture.sh      (sniffing: tcpdump, tshark)
├── Menu dispatch loop only
└── Calls to Python/external scripts via wrapper functions
```

**Why this pattern:**
- Bash has no module system — `source` is the mechanism
- Each `.sh` file is a "library" of functions with a namespace prefix
- The orchestrator file stays under 150 lines (menu + dispatch only)
- Each module can be tested independently
- Matches how fsociety (Python pentest framework) organizes by domain category

### Namespace Convention

Use `sn_` prefix for all public functions, `_sn_` for internal helpers:

```bash
# Public (called from menu)
sn_adapter_list()
sn_adapter_select()
sn_pmkid_capture()
sn_wps_scan()

# Private (internal to module)
_sn_check_root()
_sn_validate_adapter()
_sn_timestamp()
```

This prevents collisions with system commands and between modules. Source: modular bash library patterns (lost-in-it.com, 2025).

### State Management

Replace global `$adapter` with a **state file** pattern:

```bash
# lib/core.sh
SN_STATE_FILE="$SN_WORKDIR/.state"

sn_state_set() {
    local key="$1" value="$2"
    echo "${key}=${value}" >> "$SN_STATE_FILE"
}

sn_state_get() {
    local key="$1"
    grep "^${key}=" "$SN_STATE_FILE" 2>/dev/null | tail -1 | cut -d= -f2-
}

sn_adapter_get() {
    local adapter
    adapter=$(sn_state_get "adapter")
    if [[ -z "$adapter" ]]; then
        sn_log error "No adapter selected. Run adapter select first."
        return 1
    fi
    echo "$adapter"
}
```

**Why state file over global variable:**
- Survives across sourced file boundaries without namespace pollution
- Can be inspected for debugging (`cat /sniffixx/.state`)
- Adapter persists across sub-menu invocations reliably
- Each function declares exactly what it needs via `sn_state_get`

### Data Flow: Bash ↔ Python

Current pattern (broken):
```bash
# sniffixx.sh calls Python with no structured data passing
python $workdir/wscan.py    # no args, no env vars, Python reads its own config
```

Recommended pattern — **environment variable contract**:

```bash
# lib/captive.sh
sn_captive_bypass() {
    export SN_ADAPTER=$(sn_adapter_get) || return 1
    export SN_WORKDIR="$SN_WORKDIR"
    export SN_LOG_FILE="$SN_WORKDIR/logs/captive_$(sn_timestamp).log"
    
    python3 "$SN_LIB_DIR/python/opcapture.py"
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]]; then
        sn_log error "opcapture.py exited with code $exit_code"
    fi
    return $exit_code
}
```

```python
# opcapture.py — reads from environment
import os, sys

adapter = os.environ.get("SN_ADAPTER")
workdir = os.environ.get("SN_WORKDIR", "/sniffixx")
log_file = os.environ.get("SN_LOG_FILE")

if not adapter:
    print("ERROR: SN_ADAPTER not set", file=sys.stderr)
    sys.exit(1)
```

**Why environment variables over CLI args or stdin:**
- Works for both bash→python and python→python calls
- No argument parsing complexity in Python scripts
- Avoids shell quoting issues with special characters
- Established pattern in NetHunter module ecosystem (oneshot.py uses similar approach)
- Python scripts can run standalone for debugging (with manual env export)

### Inter-Script Communication for Results

When Python scripts need to return structured data to bash:

```python
# Python writes JSON to a known file
import json
result = {"bssid": "AA:BB:CC:DD:EE:FF", "essid": "TargetNet", "wps": True}
result_file = os.environ.get("SN_WORKDIR") + "/.result.json"
with open(result_file, "w") as f:
    json.dump(result, f)
```

```bash
# Bash reads the result
sn_wps_scan() {
    python3 "$SN_LIB_DIR/python/wps_scan.py"
    local result_file="$SN_WORKDIR/.result.json"
    if [[ -f "$result_file" ]]; then
        local bssid essid
        bssid=$(python3 -c "import json; print(json.load(open('$result_file'))['bssid'])")
        essid=$(python3 -c "import json; print(json.load(open('$result_file'))['essid'])")
        sn_state_set "target_bssid" "$bssid"
        sn_state_set "target_essid" "$essid"
        rm -f "$result_file"
    fi
}
```

---

## Recommended Project Directory Structure

```
Sniffixx/
├── sniffixx.sh                 # Entry point (~120 lines: source libs, menu loop)
├── install.sh                  # Installer (rewritten for new structure)
├── LICENSE                     # MIT/GPL for GitHub
├── README.md                   # Usage, install, screenshots
├── .gitignore                  # Exclude .planning/, .state, logs/, dumps/
│
├── lib/                        # Bash library modules (sourced, not executed)
│   ├── core.sh                 # Config, logging, colors, root check, version
│   ├── adapters.sh             # List, select, reset adapters
│   ├── monitor.sh              # Enable/disable monitor mode (wlan0 kernel, wlan2+ airmon-ng)
│   ├── capture.sh              # tcpdump, tshark sniffing wrappers
│   ├── pmkid.sh                # PMKID capture, convert, crack pipeline
│   ├── wps.sh                  # WPS scan, brute, pixie dust wrappers
│   ├── handshake.sh            # Handshake grabber, deauth attacks
│   ├── captive.sh              # Captive portal bypass, network connect
│   └── router.sh               # RouterSploit integration
│
├── python/                     # Python scripts (called via subprocess)
│   ├── wscan.py                # Network scanner + credential matcher + nmap
│   ├── opcapture.py            # Captive portal bypass
│   ├── target_capture.py       # Targeted client capture (called by opcapture.py)
│   ├── wpsbt.py                # WPS brute-force standalone
│   └── wpshift.py              # WPS shift/vendor PIN attack
│
├── scripts/                    # Non-Python external scripts
│   ├── rs_autoscan.sh          # RouterSploit + nmap launcher
│   └── auto_select.exp         # Expect script for oneshot automation
│
├── data/                       # Static data files
│   └── wps-pins-all-possible.txt  # WPS PIN dictionary (90MB)
│
├── config/                     # Configuration files
│   └── sniffixx.conf           # Default config (workdir path, colors, timeouts)
│
├── docs/                       # Documentation
│   ├── USAGE.md                # Detailed usage guide
│   └── ETHICS.md               # Legal/ethical use disclaimer
│
└── .planning/                  # GSD planning (git-ignored)
    └── ...
```

**Build order implications:**
1. `lib/core.sh` must be created first — everything depends on logging, config, state
2. `lib/adapters.sh` second — all operations depend on adapter selection
3. `lib/monitor.sh` third — scanning/capture depend on monitor mode
4. Domain modules (pmkid, wps, handshake) can be done in any order after core+adapters+monitor
5. `sniffixx.sh` is last — it's just the menu wiring

---

## Workdir Structure

The runtime workdir (`/sniffixx/`) should be reorganized:

```
/sniffixx/
├── .state                      # Runtime state (adapter, target_bssid, etc.)
├── logs/                       # Session logs (NEW)
│   └── session_YYYYMMDD_HHMMSS.log
├── dump/                       # Network dumps (existing)
│   ├── tcp/                    # tcpdump captures
│   ├── tshark/                 # tshark captures
│   ├── pmkid/                  # PMKID pcapng files
│   └── 22000/                  # Converted hashes
│       ├── john/               # John format hashes
│       └── extracted/          # Individual AP extractions
├── hs/                         # Handshake captures
├── wps/                        # WPS attack output
└── reports/                    # Session summaries (NEW)
    └── summary_YYYYMMDD.txt
```

**Key change:** Workdir should be configurable via `$SNIFFIXX_HOME` env var or `config/sniffixx.conf`, defaulting to `/sniffixx/`. This allows users to redirect output without code changes.

---

## Installer Architecture

### Current Problems
- Hardcoded source path `/sdcard/Dev/` — only works on developer's device
- Copies files to flat locations — no directory structure preserved
- No dependency checking
- No uninstall capability

### Recommended Installer Pattern

```bash
#!/bin/bash
# install.sh — Sniffixx installer for NetHunter/Termux

set -euo pipefail

SN_INSTALL_DIR="/usr/local/bin"
SN_WORKDIR_DEFAULT="/sniffixx"
SN_LIB_DIR="/usr/local/lib/sniffixx"

# 1. Detect source directory (where install.sh lives)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 2. Check root
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Run as root (su -c './install.sh')"
    exit 1
fi

# 3. Check dependencies
check_dependency() {
    if ! command -v "$1" &>/dev/null; then
        echo "MISSING: $1 — install with: apt install $2"
        return 1
    fi
}

echo "Checking dependencies..."
check_dependency hcxdumptool hcxdumptool
check_dependency hcxpcapngtool hcxpcapngtool
check_dependency hashcat hashcat
check_dependency john john
check_dependency aircrack-ng aircrack-ng
check_dependency reaver reaver
# ... etc

# 4. Install library modules
mkdir -p "$SN_LIB_DIR/lib" "$SN_LIB_DIR/python" "$SN_LIB_DIR/scripts" "$SN_LIB_DIR/data"
cp "$SCRIPT_DIR/lib/"*.sh "$SN_LIB_DIR/lib/"
cp "$SCRIPT_DIR/python/"*.py "$SN_LIB_DIR/python/"
cp "$SCRIPT_DIR/scripts/"* "$SN_LIB_DIR/scripts/"
cp "$SCRIPT_DIR/data/"* "$SN_LIB_DIR/data/" 2>/dev/null || true

# 5. Install entry point (with correct paths baked in)
sed "s|__SN_LIB_DIR__|$SN_LIB_DIR|g" "$SCRIPT_DIR/sniffixx.sh" > "$SN_INSTALL_DIR/sniffixx"
chmod +x "$SN_INSTALL_DIR/sniffixx"

# 6. Create workdir
mkdir -p "$SN_WORKDIR_DEFAULT"/{dump/{tcp,tshark,pmkid,22000/{john,extracted}},hs,wps,logs,reports}

echo "Installed. Run: sniffixx"
```

**Key design decisions:**
- **Auto-detect source dir** via `$(dirname "$0")` — works from any clone location
- **Dependency check before install** — fail early with actionable messages
- **Library separation** — `lib/`, `python/`, `scripts/` in `/usr/local/lib/sniffixx/`
- **Entry point uses `sed`** — replace `__SN_LIB_DIR__` placeholder with actual path
- **Workdir created at install** — all subdirectories ready before first run

---

## Monitor Mode: Architecture Fix

The current code hardcodes `wlan2` in enable/disable regardless of which adapter is passed. Recommended fix:

```bash
# lib/monitor.sh
sn_monitor_enable() {
    local adapter="$1"
    case "$adapter" in
        wlan0)
            # NetHunter internal adapter: kernel module approach
            echo 4 > /sys/module/wlan/parameters/con_mode
            ip link set wlan0 down
            ip link set wlan0 up
            sn_log info "Monitor mode enabled on wlan0 (kernel method)"
            ;;
        wlan*)
            # External USB adapters: airmon-ng (dynamic, not hardcoded)
            airmon-ng start "$adapter"
            sn_log info "Monitor mode enabled on $adapter (airmon-ng)"
            ;;
        *)
            sn_log error "Unknown adapter type: $adapter"
            return 1
            ;;
    esac
}
```

**Critical fix:** Pass `$adapter` (the actual argument) to `airmon-ng`, not hardcoded `wlan2`.

---

## Patterns to Follow

### Pattern 1: Guard-Then-Execute
Every adapter-dependent operation follows this template:

```bash
sn_pmkid_capture() {
    local adapter
    adapter=$(sn_adapter_get) || return 1
    
    sn_require_root || return 1
    sn_require_monitor_mode "$adapter" || return 1
    
    # ... actual capture logic using $adapter
}
```

### Pattern 2: Logging Over Echo
Replace all `echo` output with structured logging:

```bash
# lib/core.sh
sn_log() {
    local level="$1"; shift
    local color
    case "$level" in
        info)  color="\033[0;32m" ;;
        warn)  color="\033[0;33m" ;;
        error) color="\033[0;31m" ;;
        *)     color="\033[0m" ;;
    esac
    printf "${color}[%s] %s\033[0m\n" "$level" "$*" >&2
    printf "[%s] %s\n" "$(date +%F_%T)" "$*" >> "$SN_LOG_FILE"
}
```

### Pattern 3: Subprocess Wrapper
All external tool invocations go through a wrapper that handles logging and error capture:

```bash
_sn_run_tool() {
    local tool="$1"; shift
    if ! command -v "$tool" &>/dev/null; then
        sn_log error "$tool not found. Install with: apt install $tool"
        return 127
    fi
    sn_log info "Running: $tool $*"
    "$tool" "$@" 2>&1 | tee -a "$SN_LOG_FILE"
    local exit_code=${PIPESTATUS[0]}
    if [[ $exit_code -ne 0 ]]; then
        sn_log error "$tool exited with code $exit_code"
    fi
    return $exit_code
}
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Sourcing Scripts That Have `main()`
Python scripts like `wpsbt.py` and `wpshift.py` have their own `main()` and menu systems. Do NOT try to import/call their `main()` from bash. Instead:
- Either keep them truly standalone (user runs them directly)
- Or strip their `main()` and make them importable modules called from bash wrappers

### Anti-Pattern 2: Passing Data Via Temp Files Without Cleanup
If using temp files for bash↔python communication, always use `trap` cleanup:

```bash
local tmp_result=$(mktemp)
trap "rm -f '$tmp_result'" RETURN
python3 script.py --output "$tmp_result"
```

### Anti-Pattern 3: Silent Failures
Never do `2>/dev/null` on operations that might fail meaningfully. Capture stderr, log it, then decide:

```bash
# BAD: silent failure
hcxdumptool -i "$adapter" -w "$file" 2>/dev/null

# GOOD: logged failure
if ! hcxdumptool -i "$adapter" -w "$file" 2>&1 | tee -a "$SN_LOG_FILE"; then
    sn_log error "hcxdumptool failed — check adapter is in monitor mode"
    return 1
fi
```

---

## Scalability Considerations

| Concern | Current (1 user, 1 device) | Growth (GitHub release) |
|---------|---------------------------|------------------------|
| Path portability | Hardcoded `/sniffixx/` | Configurable via env/conf |
| Adapter types | wlan0, wlan2, wlan3 only | Dynamic detection via `iw dev` |
| External tools | Assume all installed | Check at startup, guide install |
| Python version | `python` vs `python3` ambiguity | Detect and use `python3` explicitly |
| PIN file size | 90MB in repo | Git LFS or download-on-install |

---

## Sources

- Modular bash patterns: "Designing Modular Bash: Functions, Namespaces, and Library Patterns" (lost-in-it.com, Oct 2025)
- CLI plugin architecture: "From Monolithic CLIs to Modular Plugins: Applying the Strangler Fig Pattern" (dev.to, Dec 2025)
- Pentest toolkit reference: fsociety-team/fsociety architecture (DeepWiki, Jun 2025)
- CLI tool creation: "How to Create a CLI Tool Using Bash: A Practical Guide" (coderlegion.com, Mar 2026)
- Sniffixx codebase analysis: `.planning/codebase/ARCHITECTURE.md` and `STRUCTURE.md` (2026-03-27)

---

*Architecture research: 2026-03-27*

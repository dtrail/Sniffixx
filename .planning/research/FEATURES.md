# Feature Landscape: Sniffixx WiFi Auditing Toolkit

**Domain:** WiFi penetration testing / network auditing (NetHunter)
**Researched:** 2026-03-27
**Competitive benchmark:** airgeddon (7.6k stars), wifite2 (1.4k stars), Fluxion, Bettercap, WiFiPumpkin3

## Table Stakes

Features every WiFi auditing tool must have. Missing = tool feels incomplete or unprofessional.

### Adapter Management

| Feature | Why Expected | Complexity | Sniffixx Status |
|---------|--------------|------------|-----------------|
| List available adapters | Users must know what hardware they have | Low | **Present** (list_adapters) — buggy: doesn't handle dynamic adapter names |
| Select working adapter | All operations need a target adapter | Low | **Present** — but hardcoded to wlan0/wlan2/wlan3 only |
| Enable/disable monitor mode | Required for all capture attacks | Medium | **Present** — but uses `/sys/module/wlan/parameters/con_mode` (Qualcomm-only) |
| Auto-detect adapter capabilities | Airgeddon detects chipset, band support, monitor mode capability | Medium | **Missing** |
| Adapter reset | Recover from stuck states | Low | **Present** (reset_adapter) |

**Dependency:** All other features depend on working adapter management.

### Network Scanning

| Feature | Why Expected | Complexity | Sniffixx Status |
|---------|--------------|------------|-----------------|
| Scan all nearby networks | Foundation for targeting | Low | **Present** (dump_networks) — bug: `--band bag` invalid flag |
| Display BSSID/ESSID/channel/signal | Minimum info for target selection | Low | **Present** in handshake_grabber_menu — but uses undefined $handshake_dir |
| Filter by band (2.4/5GHz) | Modern environments need 5GHz support | Low | **Present** (flag exists but broken: `bag` vs `abg`) |
| CSV export of scan results | Needed for offline analysis, reporting | Low | **Present** (airodump-ng --write) |
| WPS-enabled network scanning | Identify WPS-vulnerable targets | Low | **Present** (scan_wps_networks via wash) |

### Handshake Capture

| Feature | Why Expected | Complexity | Sniffixx Status |
|---------|--------------|------------|-----------------|
| WPA/WPA2 handshake capture | Core attack vector | Medium | **Present** (airodump-ng in handshake_grabber_menu) |
| Deauthentication attacks (force handshake) | Required to trigger re-authentication | Medium | **Present** — aireplay-ng, mdk3, mdk4 all supported |
| PMKID capture (no deauth needed) | Preferred modern method — no client required | Medium | **Present** (capture_pmkid via hcxdumptool) |
| PMKID/Handshake conversion to crackable formats | Must bridge capture → cracking | Low | **Present** (convert_selected_pmkid → .22000/.john) |
| Capture file management (list, select, extract) | Multiple captures need organization | Medium | **Present** (list_pmkid_entries, convert_selected_pmkid) |
| Dual-adapter deauth (scan on one, deauth on another) | More reliable than single-adapter deauth | Medium | **Present** (handshake_grabber_menu option 3) |
| Capture validation (verify handshake is usable) | Waste of time cracking invalid captures | Medium | **Missing** — hcxpcapngtool does basic validation but no explicit handshake verification |

### Hash Cracking

| Feature | Why Expected | Complexity | Sniffixx Status |
|---------|--------------|------------|-----------------|
| Hashcat integration (.22000 format) | Industry standard for GPU cracking | Low | **Present** (pmkid_crack_menu) |
| John the Ripper integration | Alternative CPU cracker | Low | **Present** (pmkid_crack_menu) |
| aircrack-ng integration | Lightweight fallback | Low | **Present** (pmkid_crack_menu) |
| Wordlist browsing/selection | Users need to find their wordlists | Low | **Present** (wordlists/seclists browsing) |
| Custom wordlist path input | Non-standard wordlist locations | Low | **Present** |
| Rule-based attacks | Massively improves crack rates | Medium | **Missing** — no hashcat `-r` flag support |
| Brute-force mode | Last resort for short PINs | Medium | **Missing** — no mask attack support |
| GPU device selection | Multi-GPU systems need this | Low | **Missing** — hardcoded `-D 1` (GPU device 1) |

### WPS Attacks

| Feature | Why Expected | Complexity | Sniffixx Status |
|---------|--------------|------------|-----------------|
| Pixie Dust (offline PIN recovery) | Most effective WPS attack | Medium | **Present** — via oneshot.py `-K` |
| Online brute force | Fallback when Pixie Dust fails | Medium | **Present** — via oneshot.py `-B` |
| Pixie Force | Variant attack | Medium | **Present** — via oneshot.py `-F` |
| Null PIN attack | Quick check for misconfigured APs | Low | **Present** |
| Custom PIN entry | Targeted testing with known PINs | Low | **Present** — but no PIN validation |
| Pre-computed PIN database lookup | Vendor-specific default PINs | Medium | **Present** — via oneshot.py `--vuln-list` |
| Loop mode (auto-attack multiple targets) | Efficiency for engagements | Medium | **Present** — via oneshot.py `-l` |
| WPS PIN generation algorithms | Airgeddon has ComputePIN, EasyBox, Arcadyan | High | **Missing** — no local PIN generation |
| Known PIN database with auto-update | Airgeddon maintains `known_pins.db` | Medium | **Missing** — relies entirely on external oneshot.py |

**Dependency:** WPS scanning (wash) → WPS attacks. All WPS attacks depend on adapter in monitor mode.

### Packet Sniffing

| Feature | Why Expected | Complexity | Sniffixx Status |
|---------|--------------|------------|-----------------|
| tcpdump capture | Lightweight, universal | Low | **Present** (sniff_tcpdump) |
| tshark capture | Protocol-aware, filterable | Low | **Present** (sniff_tshark) |
| Parallel tshark during PMKID capture | Capture full traffic alongside PMKID | Low | **Present** (capture_pmkid option) |

---

## Differentiators

Features that set Sniffixx apart from other tools. Not expected by default, but highly valued.

### NetHunter-Native Mobile Pentesting (PRIMARY DIFFERENTIATOR)

| Feature | Value Proposition | Complexity | Sniffixx Status |
|---------|-------------------|------------|-----------------|
| Internal adapter monitor mode (Qualcomm con_mode) | No external adapter needed on many NetHunter devices | Medium | **Present** — unique to NetHunter, other tools don't handle this |
| All-in-one terminal workflow | No GUI switching — scan, capture, crack in one session | Medium | **Present** — menu-driven single-terminal design |
| Works on Android via Termux | True mobile pentesting — no laptop needed | N/A | **Present** — designed for this |
| External + internal adapter support | Flexible hardware options | Medium | **Present** — but hardcoded names |

**Why this matters:** airgeddon, wifite2, Fluxion all target desktop Linux. Sniffixx is one of few tools designed specifically for NetHunter's constraints (single terminal, Android kernel quirks, internal adapter). This is the core value proposition.

### Captive Portal Bypass

| Feature | Value Proposition | Complexity | Sniffixx Status |
|---------|-------------------|------------|-----------------|
| MAC address spoofing | Bypass MAC-based captive portal auth | Medium | **Present** (opcapture.py via macchanger) |
| IP address spoofing | Bypass IP-based captive portal auth | Medium | **Present** (opcapture.py) |
| Open network scanning + connection | Identify and connect to open networks | Medium | **Present** (wscan.py, opcapture.py) |
| Stored credential lookup | Remember previously cracked networks | Low | **Present** (check_creds) |

**Why this matters:** Captive portal bypass is uncommon in WiFi auditing tools. airgeddon focuses on Evil Twin attacks (creating fake portals), not bypassing real ones. Sniffixx fills a different niche.

### RouterSploit Integration

| Feature | Value Proposition | Complexity | Sniffixx Status |
|---------|-------------------|------------|-----------------|
| Auto-scan connected network routers | Pivot from WiFi to router exploitation | Medium | **Present** (rs_autoscan.sh) |
| RouterSploit venv management | Handle Python dependency isolation | Low | **Present** |

**Why this matters:** Most WiFi tools stop at cracking the WiFi key. Sniffixx extends into router-level auditing — a natural next step after gaining network access.

### Credential Management

| Feature | Value Proposition | Complexity | Sniffixx Status |
|---------|-------------------|------------|-----------------|
| Auto-stored WPS credentials | Don't lose cracked PINs between sessions | Low | **Present** — reads from oneshot.py's stored.txt |
| Custom credential file | Track manually discovered credentials | Low | **Present** (wps_log.txt via nano) |

---

## Features Needed (Not Yet Built)

### Audit Trail & Logging (TABLE STAKES for Professional Use)

| Feature | Why Needed | Complexity | Priority |
|---------|------------|------------|----------|
| Session logging | Legal/ethical requirement — prove authorization scope | Medium | **Critical** |
| Operation timestamps | Audit trail for engagement reports | Low | **Critical** |
| Result summary after sessions | Quick overview of what was captured/cracked | Medium | **High** |
| Export results to text/JSON | Integration with reporting workflows | Medium | **High** |

**Why this matters:** Professional pentesters MUST document their work. Without logging, Sniffixx is a hobby tool, not a professional tool. airgeddon has no built-in logging either, so this would be a differentiator.

### Dependency & Environment Management (TABLE STAKES)

| Feature | Why Needed | Complexity | Priority |
|---------|------------|------------|----------|
| Dependency check on startup | Fail fast if tools missing (reaver, hcxdumptool, etc.) | Low | **Critical** |
| Adapter capability detection | Don't offer attacks the adapter can't do | Medium | **High** |
| Root check | Graceful failure instead of cryptic errors | Low | **High** |

### Input Validation (SECURITY)

| Feature | Why Needed | Complexity | Priority |
|---------|------------|------------|----------|
| BSSID format validation | Prevent command injection | Low | **Critical** |
| PIN format validation (8-digit numeric) | Prevent invalid PIN attempts | Low | **High** |
| Path sanitization | Prevent path traversal | Low | **High** |
| MAC/IP format validation (opcapture.py) | Prevent network stack errors | Low | **Medium** |

### CLI & Usability (PROFESSIONAL POLISH)

| Feature | Why Needed | Complexity | Priority |
|---------|------------|------------|----------|
| `--help` flag | Expected by all CLI tools | Low | **High** |
| `--version` flag | Already advertised in install.sh but not implemented | Low | **High** |
| Consistent language (all English) | German/English mix limits contributor base | Low | **Medium** |
| Color scheme consistency | Some menus have colors, some don't | Low | **Medium** |

### Expanded Cracking (DIFFERENTIATING)

| Feature | Why Needed | Complexity | Priority |
|---------|------------|------------|----------|
| Hashcat rule-based attacks | Dramatically improves crack rates | Medium | **Medium** |
| Hashcat mask/brute-force attacks | Short password coverage | Medium | **Medium** |
| Attack progress/status display | Users don't know if attack is working | Medium | **Medium** |
| Cracking session management (pause/resume) | Long-running attacks need control | High | **Low** |

---

## Anti-Features

Things to deliberately NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **GUI / Web interface** | Adds massive complexity, breaks NetHunter terminal workflow, requires X server or web deps. The whole point is terminal-only on a phone. | Keep menu-driven TUI. Improve menu clarity and keyboard navigation. |
| **Automated "hack everything" mode** | Legal liability — tools must require manual target selection for authorized testing. Automated attacks on all visible networks is illegal in most jurisdictions. | Always require user to select specific targets. Add "authorized scope" input. |
| **Windows/macOS support** | NetHunter is the platform. Cross-platform adds testing burden with zero value for the target audience. | Maintain Android/NetHunter focus. Document Linux desktop as "may work." |
| **WiFi 6E / WPA3 attack modules** | Current NetHunter hardware doesn't reliably support 6GHz. WPA3 attacks are still research-grade. Premature investment. | Track research. Note in README as future consideration. Add WPA3 downgrade attack when airgeddon plugin matures. |
| **Built-in wordlist generation** | Better handled by dedicated tools (crunch, maskprocessor, princeprocessor). Adds complexity without value. | Document recommended wordlists. Provide download links in installer. |
| **Custom cracking engine** | Hashcat, john, aircrack-ng exist and are well-optimized. Reinventing this wheel is years of work. | Continue wrapping existing tools. Focus on making the integration seamless. |
| **Evil Twin / Rogue AP attacks** | This is Fluxion/airgeddon's domain. Sniffixx's niche is capture + crack + bypass, not social engineering attacks. Massive complexity (hostapd, DHCP, DNS, web server, portal templates). | Keep captive portal *bypass* (Sniffixx's strength). Let Fluxion handle captive portal *creation*. |
| **Plugin system** | airgeddon's plugin system works because it has 7.6k stars and 37 contributors. Sniffixx isn't there yet. Premature abstraction. | Focus on clean, modular bash functions first. Plugins become viable after community adoption. |

---

## Feature Dependencies

```
Adapter Management
  └─→ Monitor Mode
        ├─→ Network Scanning
        │     ├─→ Handshake Capture → Hash Conversion → Cracking
        │     ├─→ PMKID Capture → Hash Conversion → Cracking
        │     └─→ WPS Scanning → WPS Attacks
        ├─→ Deauthentication (supports handshake capture)
        └─→ Packet Sniffing (standalone capture)

Network Connection (managed mode)
  ├─→ Open Network Scan → Connect → Captive Portal Bypass
  └─→ RouterSploit Auto-scan (after connected)

Logging System
  └─→ Wraps ALL operations above (audit trail)
```

## MVP Recommendation for GitHub Release

Prioritize for a "1.0" release that establishes credibility:

### Must Have (Blocking release)

1. **Fix all 13 bugs in CONCERNS.md** — broken features erode trust
2. **Input validation** — BSSID, PIN, path sanitization (security)
3. **Dependency check on startup** — fail gracefully, not cryptically
4. **`--help` and `--version` flags** — expected by every CLI tool
5. **Consistent paths** — no hardcoded `/sdcard/Dev/`, no `/sniffix/` vs `/sniffixx/`
6. **`.gitignore`** — exclude .pcap, .22000, .john, dump/, the 86MB PIN file
7. **README.md** — explain what it does, how to install, ethical use disclaimer

### Should Have (Strong 1.0)

8. **Session logging** — timestamped log of operations performed
9. **Result summary** — "Session captured 3 handshakes, 1 PMKID, cracked 1 key"
10. **Adapter auto-detection** — don't hardcode wlan0/wlan2/wlan3
11. **English-only UI** — remove German strings for international contributors

### Nice to Have (Post-1.0)

12. **Hashcat rule-based attacks** — improve crack rates
13. **Capture validation** — verify handshake before cracking attempt
14. **Brute-force/mask attacks** — cracking mode expansion

### Explicitly Deferred

- GUI, Evil Twin, plugin system, Windows/macOS, WPA3, automated attacks

---

## Competitive Position Summary

| Feature Category | airgeddon | wifite2 | Fluxion | Sniffixx |
|-----------------|-----------|---------|---------|----------|
| Adapter management | Excellent | Good | Good | Basic (buggy) |
| Scanning | Excellent | Excellent | Good | Present (buggy) |
| Handshake capture | Excellent | Excellent | Good | Present (buggy) |
| PMKID capture | Excellent | Good | No | Present |
| WPS attacks | Excellent | Good | No | Present (via oneshot) |
| Cracking | Excellent | Good | No | Present |
| Evil Twin | Excellent | No | Excellent | No (anti-feature) |
| Captive portal bypass | No | No | No | **Yes (unique)** |
| Router exploitation | No | No | No | **Yes (unique)** |
| Mobile/NetHunter | Partial | Partial | No | **Yes (core)** |
| Logging/Reporting | No | No | No | **Needed** |
| Input validation | Yes | Yes | Yes | **Missing** |
| Code quality | Excellent | Good | Good | Needs work |

**Sniffixx's defensible niche:** Mobile-first WiFi auditing on NetHunter with captive portal bypass and router exploitation — features no competitor offers in one tool.

---

## Sources

- airgeddon features wiki: https://github.com/v1s1t0r1sh3r3/airgeddon/wiki/Features (HIGH confidence — primary source, v11.61 Jan 2026)
- wifite2 repo: https://github.com/kimocoder/wifite2 (HIGH confidence — 1.4k stars, active)
- Fluxion repo: https://github.com/FluxionNetwork/fluxion (HIGH confidence)
- Sniffixx codebase analysis: `.planning/codebase/CONCERNS.md` (HIGH confidence — direct code audit)
- Sniffixx main script: `sniffixx.sh` (HIGH confidence — 910 lines analyzed)
- Hackzone 2026 WiFi tools roundup: https://hackzone.in/blog/wifi-hacking-tools-pentesters/ (MEDIUM confidence — blog, not primary source)
- NetHunter WiFi docs: https://kali.org/docs/nethunter/ (HIGH confidence — official Kali docs)

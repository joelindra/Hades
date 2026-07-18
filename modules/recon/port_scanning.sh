#!/bin/bash

# Colors
MAGENTA='\033[1;35m'
NC='\033[0m' # No Color
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'

# Banner function
display_banner() {
    clear
}

# Input target function
input_target() {
    clear
    echo -e "${BLUE}👽 Single Domain Auto Portscan${NC}"
    echo ""
    
    while true; do
        echo -e "${YELLOW}[?] Enter target host ${NC}(example: example.com or 192.168.1.1)"
        echo -e "${YELLOW}[?] Type 'quit' to exit${NC}"
        echo -ne "\n${GREEN}[+] Target host: ${NC}"
        read -r input
        
        # Validation logic
        if [[ -z "$input" ]]; then
            echo -e "\n${RED}[!] Error: host cannot be empty!${NC}"
            sleep 1
            continue
        elif [[ "$input" == "quit" ]]; then
            echo -e "\n${YELLOW}[!] Exiting program...${NC}"
            exit 0
        fi
        
        # If valid
        echo -e "\n${GREEN}[✓] Target host: $input${NC}"
        echo -e "${BLUE}[*] Starting port scan...${NC}\n"
        sleep 1
        target="$input"  # Set target variable
        
        # Create safe directory name (replace dots and slashes)
        safe_dirname=$(echo "$input" | sed 's/[\/\.]/_/g')
        workspace="scan_${safe_dirname}_$(date +%Y%m%d_%H%M%S)"
        break
    done
    return 0
}

# Create directory structure
setup_workspace() {
    echo -e "\n${BLUE}[+] Setting up workspace...${NC}"
    mkdir -p "$workspace"/{nmap,ports,services,vulnerabilities}
    echo -e "${GREEN}[✓] Directory structure created: $workspace${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Host discovery
check_host() {
    echo -e "\n${BLUE}[+] Checking if host is alive...${NC}"
    
    # Check if nmap is installed
    if ! command -v nmap &> /dev/null; then
        echo -e "${RED}[!] Error: nmap is not installed${NC}"
        echo -e "${YELLOW}[*] Please install nmap: sudo apt install nmap${NC}"
        exit 1
    fi
    
    # Host discovery with nmap
    echo -e "${MAGENTA}[*] Running host discovery...${NC}"
    
    # Try different discovery methods
    if sudo nmap -sn -PE -PP -PM -PO -PS21,22,23,25,80,443,3389 "$target" -oG - | grep -q "Status: Up"; then
        echo -e "${GREEN}[✓] Host is up${NC}"
        echo "Host is up" > "$workspace/host_status.txt"
        
        # Get IP address
        ip_address=$(sudo nmap -sn "$target" -oG - | grep "Host:" | awk '{print $2}' | grep -E '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$')
        if [[ -n "$ip_address" ]]; then
            echo -e "${GREEN}[✓] IP Address: $ip_address${NC}"
            echo "$ip_address" > "$workspace/ip_address.txt"
        fi
    else
        echo -e "${YELLOW}[!] Host appears to be down or blocking probes${NC}"
        echo -e "${YELLOW}[*] Continuing with scan anyway...${NC}"
        echo "Host status unknown" > "$workspace/host_status.txt"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Quick TCP port scan
quick_tcp_scan() {
    echo -e "\n${BLUE}[+] Running quick TCP port scan (top 1000 ports)...${NC}"
    
    echo -e "${MAGENTA}[*] Scanning common TCP ports...${NC}"
    
    # Quick TCP scan with service detection
    sudo nmap -sS -sV --top-ports 1000 -T4 "$target" -oA "$workspace/nmap/quick_tcp_scan" 2>/dev/null
    
    # Extract open ports
    if [[ -f "$workspace/nmap/quick_tcp_scan.gnmap" ]]; then
        grep -oE '[0-9]+/open/tcp' "$workspace/nmap/quick_tcp_scan.gnmap" | \
            cut -d'/' -f1 | sort -n -u > "$workspace/ports/tcp_open_ports.txt"
        
        tcp_count=$(wc -l < "$workspace/ports/tcp_open_ports.txt" 2>/dev/null || echo "0")
        echo -e "${GREEN}[✓] Found $tcp_count open TCP ports${NC}"
        
        if [[ $tcp_count -gt 0 ]]; then
            echo -e "${YELLOW}[*] Open TCP ports:${NC}"
            cat "$workspace/ports/tcp_open_ports.txt" | tr '\n' ' ' | sed 's/ $/\n/' | sed 's/^/    /'
        fi
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Full port scan
full_port_scan() {
    echo -e "\n${BLUE}[+] Running full port scan?${NC}"
    echo -ne "${YELLOW}[?] Scan all 65535 ports? (y/N): ${NC}"
    read -r answer
    
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo -e "${MAGENTA}[*] Running full TCP port scan (this may take a while)...${NC}"
        
        # Full TCP scan
        sudo nmap -sS -p- -T4 "$target" -oA "$workspace/nmap/full_tcp_scan" 2>/dev/null
        
        # Extract all open ports
        if [[ -f "$workspace/nmap/full_tcp_scan.gnmap" ]]; then
            grep -oE '[0-9]+/open/tcp' "$workspace/nmap/full_tcp_scan.gnmap" | \
                cut -d'/' -f1 | sort -n -u > "$workspace/ports/all_tcp_ports.txt"
            
            all_tcp_count=$(wc -l < "$workspace/ports/all_tcp_ports.txt" 2>/dev/null || echo "0")
            echo -e "${GREEN}[✓] Total open TCP ports found: $all_tcp_count${NC}"
        fi
    else
        echo -e "${YELLOW}[*] Skipping full port scan${NC}"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Service and version detection
service_detection() {
    echo -e "\n${BLUE}[+] Running detailed service detection...${NC}"
    
    # Get list of open ports
    if [[ -f "$workspace/ports/all_tcp_ports.txt" ]] && [[ -s "$workspace/ports/all_tcp_ports.txt" ]]; then
        ports_file="$workspace/ports/all_tcp_ports.txt"
    elif [[ -f "$workspace/ports/tcp_open_ports.txt" ]] && [[ -s "$workspace/ports/tcp_open_ports.txt" ]]; then
        ports_file="$workspace/ports/tcp_open_ports.txt"
    else
        echo -e "${YELLOW}[!] No open ports found to scan${NC}"
        return
    fi
    
    ports=$(cat "$ports_file" | tr '\n' ',' | sed 's/,$//')
    echo -e "${MAGENTA}[*] Scanning services on ports: $ports${NC}"
    
    # Detailed service scan
    sudo nmap -sV -sC -A -p"$ports" "$target" -T5 -oA "$workspace/nmap/service_scan" 2>/dev/null
    
    # Extract service information
    if [[ -f "$workspace/nmap/service_scan.nmap" ]]; then
        # Parse services
        grep -E "^[0-9]+/tcp" "$workspace/nmap/service_scan.nmap" > "$workspace/services/all_services.txt"
        
        # Categorize services
        grep -iE "http|https" "$workspace/services/all_services.txt" > "$workspace/services/web_services.txt" 2>/dev/null
        grep -iE "ssh" "$workspace/services/all_services.txt" > "$workspace/services/ssh_services.txt" 2>/dev/null
        grep -iE "ftp" "$workspace/services/all_services.txt" > "$workspace/services/ftp_services.txt" 2>/dev/null
        grep -iE "mysql|mssql|postgresql|oracle" "$workspace/services/all_services.txt" > "$workspace/services/database_services.txt" 2>/dev/null
        grep -iE "smb|netbios|samba" "$workspace/services/all_services.txt" > "$workspace/services/smb_services.txt" 2>/dev/null
        
        echo -e "${GREEN}[✓] Service detection completed${NC}"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Vulnerability scanning
vulnerability_scan() {
    echo -e "\n${BLUE}[+] Running vulnerability scans...${NC}"
    
    # Check if we have open ports
    if [[ -f "$workspace/ports/tcp_open_ports.txt" ]] && [[ -s "$workspace/ports/tcp_open_ports.txt" ]]; then
        ports=$(cat "$workspace/ports/tcp_open_ports.txt" | tr '\n' ',' | sed 's/,$//')
        
        echo -e "${MAGENTA}[*] Running Nmap vulnerability scripts...${NC}"
        
        # General vulnerability scan
        sudo nmap --script vuln -p"$ports" "$target" -oA "$workspace/vulnerabilities/vuln_scan" 2>/dev/null
        
        # Check for specific services and run targeted scans
        if grep -q "80\|443\|8080\|8443" "$workspace/ports/tcp_open_ports.txt" 2>/dev/null; then
            echo -e "${MAGENTA}[*] Running HTTP vulnerability checks...${NC}"
            http_ports=$(grep -E "^(80|443|8080|8443)$" "$workspace/ports/tcp_open_ports.txt" | tr '\n' ',' | sed 's/,$//')
            sudo nmap --script "http-*" -p"$http_ports" "$target" -oA "$workspace/vulnerabilities/http_vuln" 2>/dev/null
        fi
        
        if grep -q "445\|139" "$workspace/ports/tcp_open_ports.txt" 2>/dev/null; then
            echo -e "${MAGENTA}[*] Running SMB vulnerability checks...${NC}"
            sudo nmap --script "smb-vuln-*" -p445,139 "$target" -oA "$workspace/vulnerabilities/smb_vuln" 2>/dev/null
        fi
        
        if grep -q "22" "$workspace/ports/tcp_open_ports.txt" 2>/dev/null; then
            echo -e "${MAGENTA}[*] Running SSH checks...${NC}"
            sudo nmap --script "ssh-*" -p22 "$target" -oA "$workspace/vulnerabilities/ssh_check" 2>/dev/null
        fi
        
        echo -e "${GREEN}[✓] Vulnerability scanning completed${NC}"
    else
        echo -e "${YELLOW}[!] No open ports found for vulnerability scanning${NC}"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Generate report
generate_report() {
    echo -e "\n${BLUE}[+] Generating scan report...${NC}"
    
    report_file="$workspace/scan_report.txt"
    
    {
        echo "NMAP PORT SCAN REPORT"
        echo "===================="
        echo "Date: $(date)"
        echo "Target: $target"
        
        if [[ -f "$workspace/ip_address.txt" ]]; then
            echo "IP Address: $(cat "$workspace/ip_address.txt")"
        fi
        
        echo "Host Status: $(cat "$workspace/host_status.txt" 2>/dev/null || echo "Unknown")"
        echo ""
        
        echo "OPEN PORTS:"
        echo "-----------"
        if [[ -f "$workspace/ports/tcp_open_ports.txt" ]] && [[ -s "$workspace/ports/tcp_open_ports.txt" ]]; then
            echo "TCP Ports: $(cat "$workspace/ports/tcp_open_ports.txt" | tr '\n' ' ')"
            echo "Total: $(wc -l < "$workspace/ports/tcp_open_ports.txt") ports"
        else
            echo "No open ports found"
        fi
        echo ""
        
        echo "SERVICES DETECTED:"
        echo "-----------------"
        if [[ -f "$workspace/services/all_services.txt" ]] && [[ -s "$workspace/services/all_services.txt" ]]; then
            cat "$workspace/services/all_services.txt"
        else
            echo "No services detected"
        fi
        echo ""
        
        echo "SERVICE SUMMARY:"
        echo "---------------"
        echo "Web Services: $(wc -l < "$workspace/services/web_services.txt" 2>/dev/null || echo "0")"
        echo "SSH Services: $(wc -l < "$workspace/services/ssh_services.txt" 2>/dev/null || echo "0")"
        echo "Database Services: $(wc -l < "$workspace/services/database_services.txt" 2>/dev/null || echo "0")"
        echo "SMB Services: $(wc -l < "$workspace/services/smb_services.txt" 2>/dev/null || echo "0")"
        echo "FTP Services: $(wc -l < "$workspace/services/ftp_services.txt" 2>/dev/null || echo "0")"
        echo ""
        
        echo "POTENTIAL VULNERABILITIES:"
        echo "-------------------------"
        if [[ -f "$workspace/vulnerabilities/vuln_scan.nmap" ]]; then
            grep -iE "VULNERABLE|CVE-" "$workspace/vulnerabilities/vuln_scan.nmap" | head -20 || echo "No vulnerabilities detected"
        else
            echo "Vulnerability scan not performed"
        fi
        
    } > "$report_file"
    
    echo -e "${GREEN}[✓] Report saved to: $report_file${NC}"
    
    # Display summary
    echo -e "\n${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}           SCAN SUMMARY                 ${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "Target: ${GREEN}$target${NC}"
    echo -e "Open Ports: ${GREEN}$(wc -l < "$workspace/ports/tcp_open_ports.txt" 2>/dev/null || echo "0")${NC}"
    echo -e "Report Location: ${GREEN}$workspace/${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Send to Telegram (optional)
send_to_telegram() {
    echo -e "\n${BLUE}[+] Preparing to send results to Telegram...${NC}"
    if ! command -v curl &> /dev/null || ! command -v zip &> /dev/null; then
        echo -e "${RED}[!] 'curl' and 'zip' are required but not installed.${NC}"
        return 1
    fi

    if [[ ! -f "telegram_token.txt" || ! -f "telegram_chat_id.txt" ]]; then
        echo -e "${RED}[!] Telegram credentials (telegram_token.txt, telegram_chat_id.txt) not found.${NC}"
        return 1
    fi

    local token=$(<"telegram_token.txt")
    local chat_id=$(<"telegram_chat_id.txt")
    local result_dir="$workspace/result"

    local message
    message=$(printf "🔍 *PORT Scan Completed for:* \`%s\`\n\n" "$workspace"
    printf "📊 *Summary:*\n"
    printf "📤 Detailed results are attached in the zip file."
    )

    # Send summary message
    echo -e "${BLUE}[*] Sending summary message...${NC}"
    curl -s -X POST "https://api.telegram.org/bot$token/sendMessage" \
        -d chat_id="$chat_id" \
        -d text="$message" \
        -d parse_mode="Markdown" > /dev/null

    # 3. Archive Results and Send
    if [ -d "$result_dir" ] && [ "$(ls -A "$result_dir")" ]; then
        local archive_name="results-$(basename "$workspace")-$(date +%F).zip"
        
        echo -e "${BLUE}[*] Creating results archive: ${archive_name}${NC}"
        # Option -j (junk paths) keeps files out of subfolders in zip
        zip -r -j "$archive_name" "$result_dir" > /dev/null

        echo -e "${BLUE}[*] Uploading archive...${NC}"
        curl -s -X POST "https://api.telegram.org/bot$token/sendDocument" \
            -F chat_id="$chat_id" \
            -F document=@"$archive_name" \
            -F caption="All scan results for $workspace" > /dev/null
        
        rm "$archive_name" # Remove zip file after sending
    else
        echo -e "${YELLOW}[!] No result files found to archive in '$result_dir'.${NC}"
    fi
    
    echo -e "${GREEN}[✓] Process completed. Results sent to Telegram.${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}
# Main execution
main() {
    display_banner
    input_target
    setup_workspace
    check_host
    quick_tcp_scan
    full_port_scan
    service_detection
    vulnerability_scan
    generate_report
    send_to_telegram
    
    echo -e "\n${GREEN}[✓] Port scan completed!${NC}"
    echo -e "${YELLOW}[*] Results saved in: ${workspace}/${NC}\n"
}

# Check for root/sudo
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[!] This script requires root privileges${NC}"
   echo -e "${YELLOW}[*] Please run with sudo: sudo $0${NC}"
   exit 1
fi

# Run the script
main
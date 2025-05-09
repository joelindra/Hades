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
    echo -e "${BLUE}"
    figlet -w 100 -f small "Dirsearch For Patrol"
    echo -e "${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Input target function
input_target() {
    clear
    echo -e "\n${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          Dirsearch For Patrol        ${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"
    
    while true; do
        echo -e "${YELLOW}[?] Masukkan domain target ${NC}(contoh: example.com)"
        echo -e "${YELLOW}[?] Ketik 'quit' untuk keluar${NC}"
        echo -ne "\n${GREEN}[+] Target Domain: ${NC}"
        read -r input
        
        # Validasi input
        if [[ -z "$input" ]]; then
            echo -e "\n${RED}[!] Error: Domain tidak boleh kosong!${NC}"
            sleep 1
            continue
        elif [[ "$input" == "quit" ]]; then
            echo -e "\n${YELLOW}[!] Keluar dari program...${NC}"
            exit 0
        elif ! [[ "$input" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
            echo -e "\n${RED}[!] Error: Format domain tidak valid!${NC}"
            sleep 1
            continue
        fi
        
        # Jika validasi berhasil
        echo -e "\n${GREEN}[✓] Domain target valid: $input${NC}"
        echo -e "${BLUE}[*] Memulai pemindaian...${NC}\n"
        sleep 1
        break
    done
    
    # Simpan domain ke variable global
    TARGET_DOMAIN="$input"
    return 0
}

# WAF detection
check_waf() {
    echo -e "\n${BLUE}[+] Checking Web Application Firewall...${NC}"
    echo -e "${MAGENTA}[*] Running WAF detection...${NC}"
    wafw00f "$TARGET_DOMAIN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Domain enumeration
enumerate_domain() {
    echo -e "\n${BLUE}[+] Starting Domain Enumeration...${NC}"
    
    # Create directory structure
    mkdir -p "$TARGET_DOMAIN"/{sources,result/{takeover,httpx},reports}
    
    echo -e "${MAGENTA}[*] Running Subfinder...${NC}"
    subfinder -d "$TARGET_DOMAIN" -o "$TARGET_DOMAIN/sources/subfinder.txt"
    subfinder_count=$(wc -l < "$TARGET_DOMAIN/sources/subfinder.txt")
    echo -e "${GREEN}[✓] Subfinder found ${subfinder_count} subdomains${NC}"
    
    echo -e "${MAGENTA}[*] Running Assetfinder...${NC}"
    assetfinder -subs-only "$TARGET_DOMAIN" | tee "$TARGET_DOMAIN/sources/assetfinder.txt"
    assetfinder_count=$(wc -l < "$TARGET_DOMAIN/sources/assetfinder.txt")
    echo -e "${GREEN}[✓] Assetfinder found ${assetfinder_count} subdomains${NC}"
    
    echo -e "${MAGENTA}[*] Combining results...${NC}"
    cat "$TARGET_DOMAIN/sources/"*.txt > "$TARGET_DOMAIN/sources/all.txt"
    total_domains=$(wc -l < "$TARGET_DOMAIN/sources/all.txt")
    echo -e "${GREEN}[✓] Total unique subdomains: ${total_domains}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

probe_http() {
    echo -e "\n${BLUE}[+] Probing for live hosts...${NC}"
    cat "$TARGET_DOMAIN/sources/all.txt" | httprobe | tee "$TARGET_DOMAIN/result/httpx/httpx.txt"
    
    total_live=$(wc -l < "$TARGET_DOMAIN/result/httpx/httpx.txt")
    echo -e "${GREEN}[✓] Found ${total_live} live hosts${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Run Dirsearch on targets
run_dirsearch_patrol() {
    echo -e "\n${BLUE}[+] Starting Dirsearch Patrol...${NC}"
    
    total_targets=$(wc -l < "$TARGET_DOMAIN/result/httpx/httpx.txt")
    current=0
    found_dirs=0
    
    while IFS= read -r target; do
        ((current++))
        echo -e "\n${YELLOW}[*] Scanning target ($current/$total_targets): $target${NC}"
        
        output_file="$TARGET_DOMAIN/reports/${target//\//_}_dirsearch_report.txt"
        
        dirsearch -u "$target" \
                 -t 150 \
                 -x 403,404,401,500,429 \
                 -i 200,302,301 \
                 --random-agent \
                 -o "$output_file"
        
        # Count found directories
        if [[ -f "$output_file" ]]; then
            dirs_found=$(grep -c "200\|301\|302" "$output_file")
            ((found_dirs+=dirs_found))
            echo -e "${GREEN}[✓] Found $dirs_found directories for $target${NC}"
        fi
    done < "$TARGET_DOMAIN/result/httpx/httpx.txt"
    
    echo -e "\n${GREEN}[✓] Dirsearch completed! Total directories found: $found_dirs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Send results to Telegram
send_to_telegram() {
    echo -e "\n${BLUE}[+] Sending results to Telegram...${NC}"
    
    if [[ -f telegram_token.txt && -f telegram_chat_id.txt ]]; then
        token=$(cat telegram_token.txt)
        chat_id=$(cat telegram_chat_id.txt)
        
        # Count total directories found
        total_dirs=$(find "$TARGET_DOMAIN/reports" -type f -exec grep -c "200\|301\|302" {} \; | awk '{sum+=$1} END{print sum}')
        
        # Send summary message
        message="🔍 Dirsearch Patrol completed for: $TARGET_DOMAIN

📊 Summary:
• Subdomains scanned: $(wc -l < "$TARGET_DOMAIN/sources/all.txt")
• Total directories found: $total_dirs
• Report files generated: $(find "$TARGET_DOMAIN/reports" -type f | wc -l)

📤 Sending detailed results..."

        curl -s -X POST "https://api.telegram.org/bot$token/sendMessage" \
             -d chat_id="$chat_id" \
             -d text="$message" > /dev/null 2>&1

        # Send files with progress
        total_files=$(find "$TARGET_DOMAIN" -type f | wc -l)
        current=0
        
        find "$TARGET_DOMAIN" -type f | while read -r file; do
            ((current++))
            echo -e "${MAGENTA}[*] Sending file ($current/$total_files): $(basename "$file")${NC}"
            curl -s -F chat_id="$chat_id" \
                 -F document=@"$file" \
                 "https://api.telegram.org/bot$token/sendDocument" > /dev/null 2>&1
        done

        echo -e "${GREEN}[✓] Results sent to Telegram${NC}"
    else
        echo -e "${RED}[!] Telegram credentials not found${NC}"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    display_banner
    input_target
    check_waf
    enumerate_domain
    probe_http
    run_dirsearch_patrol
    send_to_telegram
    echo -e "\n${GREEN}[✓] Dirsearch patrol completed successfully!${NC}\n"
}

# Run the script
main
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
    echo -e "${BLUE}👽 Single Domain Directory Patrol${NC}"
    echo ""
    
    while true; do
        echo -e "${YELLOW}[?] Enter target domain ${NC}(example: example.com)"
        echo -e "${YELLOW}[?] Type 'quit' to exit${NC}"
        echo -ne "\n${GREEN}[+] Target domain: ${NC}"
        read -r input
        
        # Validation logic
        if [[ -z "$input" ]]; then
            echo -e "\n${RED}[!] Error: workspace cannot be empty!${NC}"
            sleep 1
            continue
        elif [[ "$input" == "quit" ]]; then
            echo -e "\n${YELLOW}[!] Exiting program...${NC}"
            exit 0
        elif ! [[ "$input" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
            echo -e "\n${RED}[!] Error: Invalid workspace format!${NC}"
            sleep 1
            continue
        fi
        
        # If valid
        echo -e "\n${GREEN}[✓] Target workspace valid: $input${NC}"
        echo -e "${BLUE}[*] Starting scan...${NC}\n"
        sleep 1
        break
    done
    
    # Save workspace to global variable
    TARGET_workspace="$input"
    return 0
}

# WAF detection
check_waf() {
    echo -e "\n${BLUE}[+] Checking Web Application Firewall...${NC}"
    echo -e "${MAGENTA}[*] Running WAF detection...${NC}"
    wafw00f "$TARGET_workspace"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# workspace enumeration
enumerate_workspace() {
    echo -e "\n${BLUE}[+] Starting workspace Enumeration...${NC}"
    
    # Create directory structure
    mkdir -p "$TARGET_workspace"/{sources,result/{takeover,httpx},reports}
    
    echo -e "${MAGENTA}[*] Running Subfinder...${NC}"
    subfinder -d "$TARGET_workspace" -o "$TARGET_workspace/sources/subfinder.txt"
    subfinder_count=$(wc -l < "$TARGET_workspace/sources/subfinder.txt")
    echo -e "${GREEN}[✓] Subfinder found ${subfinder_count} subworkspaces${NC}"
    
    echo -e "${MAGENTA}[*] Running Assetfinder...${NC}"
    assetfinder -subs-only "$TARGET_workspace" | tee "$TARGET_workspace/sources/assetfinder.txt"
    assetfinder_count=$(wc -l < "$TARGET_workspace/sources/assetfinder.txt")
    echo -e "${GREEN}[✓] Assetfinder found ${assetfinder_count} subworkspaces${NC}"
    
    echo -e "${MAGENTA}[*] Combining results...${NC}"
    cat "$TARGET_workspace/sources/"*.txt > "$TARGET_workspace/sources/all.txt"
    total_workspaces=$(wc -l < "$TARGET_workspace/sources/all.txt")
    echo -e "${GREEN}[✓] Total unique subworkspaces: ${total_workspaces}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

probe_http() {
    echo -e "\n${BLUE}[+] Probing for live hosts...${NC}"
    
    # Probe hosts and save temp results
    temp_file=$(mktemp)
    cat "$TARGET_workspace/sources/all.txt" | httprobe | tee "$temp_file"
    
    # Deduplication: prioritize HTTPS over HTTP
    echo -e "${YELLOW}[+] Removing duplicates (prioritizing HTTPS)...${NC}"
    
    # Extract unique workspace and determine best protocol
    awk -F'://' '{
        workspace = $2
        protocol = $1
        
        # If workspace does not exist yet or current protocol is https
        if (!(workspace in workspaces) || protocol == "https") {
            workspaces[workspace] = protocol "://" workspace
        }
    }
    END {
        for (d in workspaces) {
            print workspaces[d]
        }
    }' "$temp_file" | sort > "$TARGET_workspace/result/httpx/httpx.txt"
    
    # Delete temporary file
    rm -f "$temp_file"
    
    total_live=$(cat "$TARGET_workspace/result/httpx/httpx.txt" 2>/dev/null | wc -l)
    echo -e "${GREEN}[✓] Found ${total_live} live hosts (after deduplication)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Run Dirsearch on targets
run_dirsearch_patrol() {
    echo -e "\n${BLUE}[+] Starting Dirsearch Patrol...${NC}"
    
    total_targets=$(wc -l < "$TARGET_workspace/result/httpx/httpx.txt")
    current=0
    found_dirs=0
    
    while IFS= read -r target; do
        ((current++))
        echo -e "\n${YELLOW}[*] Scanning target ($current/$total_targets): $target${NC}"
        
        output_file="$TARGET_workspace/reports/${target//\//_}_dirsearch_report.txt"
        
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
    done < "$TARGET_workspace/result/httpx/httpx.txt"
    
    echo -e "\n${GREEN}[✓] Dirsearch completed! Total directories found: $found_dirs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Send results to Telegram
send_to_telegram() {
    echo -e "\n${BLUE}[+] Preparing to send results to Telegram...${NC}"
    if ! command -v curl &> /dev/null || ! command -v zip &> /dev/null; then
        echo -e "${RED}[!] 'curl' and 'zip' are required but not installed.${NC}"
        return 1
    fi

    # Check both root and config/ directory
    if [[ -f "config/telegram_token.txt" && -f "config/telegram_chat_id.txt" ]]; then
        local token=$(<"config/telegram_token.txt")
        local chat_id=$(<"config/telegram_chat_id.txt")
    elif [[ -f "telegram_token.txt" && -f "telegram_chat_id.txt" ]]; then
        local token=$(<"telegram_token.txt")
        local chat_id=$(<"telegram_chat_id.txt")
    else
        echo -e "${RED}[!] Telegram credentials not found in config/ or root.${NC}"
        return 1
    fi
    local result_dir="$workspace/result"

    local message
    message=$(printf "🔍 *Dirpatrol Scan Completed for:* \`%s\`\n\n" "$workspace"
    printf "📊 *Summary:*\n"
    printf " • Total URLs: \`%s\`\n" "$(wc -l < "$result_dir/wayback/wayback.txt" 2>/dev/null || echo 0)"
    printf " • Valid URLs: \`%s\`\n" "$(wc -l < "$result_dir/wayback/valid.txt" 2>/dev/null || echo 0)"
    printf " • Potential Directory: \`%s\`\n\n" "$(wc -l < "$TARGET_workspace/reports/${target//\//_}_dirsearch_report.txt" 2>/dev/null || echo 0)"
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
    check_waf
    enumerate_workspace
    probe_http
    run_dirsearch_patrol
    send_to_telegram
    echo -e "\n${GREEN}[✓] Dirsearch patrol completed successfully!${NC}\n"
}

# Run the script
main
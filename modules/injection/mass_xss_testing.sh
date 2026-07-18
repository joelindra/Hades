#!/bin/bash

# Colors
MAGENTA='\033[1;35m'
NC='\033[0m' # No Color
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'

# Global variable for current workspace
workspace=""

# Banner function
display_banner() {
    clear
    echo -e "${BLUE}👽 Mass Server Domain XSS${NC}"
    echo ""
}

# Input target function
input_target() {
    local choice
    while true; do
        display_banner
        echo -e "${YELLOW}[?] Select input method:${NC}"
        echo -e "${YELLOW}    1. Enter a single domain${NC}"
        echo -e "${YELLOW}    2. Enter file path containing domain list${NC}"
        echo -e "${YELLOW}    Type 'quit' to exit${NC}"
        echo -ne "\n${GREEN}[+] Your Choice: ${NC}"
        read -r choice

        case "$choice" in
            1)
                read_single_domain
                return 0
                ;;
            2)
                read_domains_from_file
                return 0
                ;;
            quit)
                echo -e "\n${YELLOW}[!] Exiting program...${NC}"
                exit 0
                ;;
            *)
                echo -e "\n${RED}[!] Invalid choice. Please try again.${NC}"
                sleep 1
                ;;
        esac
    done
}

# Read single domain
read_single_domain() {
    while true; do
        display_banner
        echo -e "${YELLOW}[?] Enter target domain ${NC}(example: example.com)"
        echo -e "${YELLOW}[?] Type 'quit' to exit${NC}"
        echo -ne "\n${GREEN}[+] Target domain: ${NC}"
        read -r input

        # Validation logic
        if [[ -z "$input" ]]; then
            echo -e "\n${RED}[!] Error: Domain cannot be empty!${NC}"
            sleep 1
            continue
        elif [[ "$input" == "quit" ]]; then
            echo -e "\n${YELLOW}[!] Exiting program...${NC}"
            exit 0
        elif ! [[ "$input" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
            echo -e "\n${RED}[!] Error: Invalid domain format!${NC}"
            sleep 1
            continue
        fi

        # If valid
        echo -e "\n${GREEN}[✓] Valid target domain: $input${NC}"
        echo -e "${BLUE}[*] Starting scan for $input...${NC}\n"
        sleep 1
        domains_to_scan=("$input") # Set as an array for consistency
        break
    done
    return 0
}

# Read domains from file
read_domains_from_file() {
    local file_path
    while true; do
        display_banner
        echo -e "${YELLOW}[?] Enter file path containing domain list ${NC}(ex: domain.txt)"
        echo -e "${YELLOW}[?] Type 'quit' to exit${NC}"
        echo -ne "\n${GREEN}[+] File path: ${NC}"
        read -r file_path

        if [[ "$file_path" == "quit" ]]; then
            echo -e "\n${YELLOW}[!] Exiting program...${NC}"
            exit 0
        elif [[ ! -f "$file_path" ]]; then
            echo -e "\n${RED}[!] Error: File not found or not a regular file!${NC}"
            sleep 1
            continue
        elif [[ ! -r "$file_path" ]]; then
            echo -e "\n${RED}[!] Error: File is not readable!${NC}"
            sleep 1
            continue
        fi

        # Read domains into an array, skipping empty lines and trimming whitespace
        mapfile -t domains_to_scan < <(grep -vE '^\s*$' "$file_path" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        if [ ${#domains_to_scan[@]} -eq 0 ]; then
            echo -e "\n${RED}[!] Error: File is empty or does not contain valid domains!${NC}"
            sleep 1
            continue
        fi

        echo -e "\n${GREEN}[✓] Successfully read ${#domains_to_scan[@]} domains from '$file_path'${NC}"
        echo -e "${BLUE}[*] Starting scan for these domains...${NC}\n"
        sleep 1
        break
    done
    return 0
}


# WAF detection
check_waf() {
    echo -e "\n${BLUE}[+] Checking Web Application Firewall for $workspace...${NC}"
    if command -v wafw00f &> /dev/null; then
        wafw00f "$workspace"
    else
        echo -e "${YELLOW}[!] wafw00f not found - performing basic WAF check${NC}"
        curl -sI "https://$workspace" | grep -i "WAF" || true
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Domain enumeration
enumerate_domain() {
    echo -e "\n${BLUE}[+] Starting Domain Enumeration for $workspace...${NC}"
    
    # Create directory structure
    mkdir -p "$workspace"/{sources,result/{xss,wayback,gf,httpx}}
    
    echo -e "${MAGENTA}[*] Running Subfinder...${NC}"
    subfinder -d "$workspace" -o "$workspace/sources/subfinder.txt" 2>/dev/null || true
    subfinder_count=$(wc -l < "$workspace/sources/subfinder.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Subfinder found ${subfinder_count} subdomains${NC}"
    
    echo -e "${MAGENTA}[*] Running Assetfinder...${NC}"
    assetfinder -subs-only "$workspace" 2>/dev/null | tee "$workspace/sources/assetfinder.txt" || true
    assetfinder_count=$(wc -l < "$workspace/sources/assetfinder.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Assetfinder found ${assetfinder_count} subdomains${NC}"
    
    echo -e "${MAGENTA}[*] Combining results...${NC}"
    cat "$workspace/sources/"*.txt 2>/dev/null | sort -u > "$workspace/sources/all.txt"
    total_domains=$(wc -l < "$workspace/sources/all.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Total unique subdomains: ${total_domains}${NC}"
    
    echo -e "${GREEN}[✓] Domain enumeration completed${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# HTTP probe
probe_http() {
    echo -e "\n${BLUE}[+] Probing for live hosts for $workspace...${NC}"
    
    # Probe hosts and save temp results
    temp_file=$(mktemp)
    cat "$workspace/sources/all.txt" | httprobe -c 50 -t 5000 | tee "$temp_file" || true
    
    # Deduplication: prioritize HTTPS over HTTP
    echo -e "${YELLOW}[+] Removing duplicates (prioritizing HTTPS)...${NC}"
    
    # Extract unique domains and determine best protocol
    awk -F'://' '{
        domain = $2
        protocol = $1
        
        # If domain does not exist yet or current protocol is https
        if (!(domain in domains) || protocol == "https") {
            domains[domain] = protocol "://" domain
        }
    }
    END {
        for (d in domains) {
            print domains[d]
        }
    }' "$temp_file" | sort > "$workspace/result/httpx/httpx.txt"
    
    # Delete temporary file
    rm -f "$temp_file"
    
    total_live=$(wc -l < "$workspace/result/httpx/httpx.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Found ${total_live} live hosts (after deduplication)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Wayback data collection
collect_wayback() {
    echo -e "\n${BLUE}[+] Collecting URLs from Wayback Machine for $workspace...${NC}"
    
    cat "$workspace/result/httpx/httpx.txt" | waybackurls | anew "$workspace/result/wayback/wayback-tmp.txt" || true
    
    echo -e "${MAGENTA}[*] Filtering relevant URLs...${NC}"
    cat "$workspace/result/wayback/wayback-tmp.txt" 2>/dev/null | \
        egrep -v "\.woff|\.ttf|\.svg|\.eot|\.png|\.jpeg|\.jpg|\.png|\.css|\.ico" | \
        sed 's/:80//g;s/:443//g' | sort -u > "$workspace/result/wayback/wayback.txt"
    
    rm -f "$workspace/result/wayback/wayback-tmp.txt"
    total_urls=$(wc -l < "$workspace/result/wayback/wayback.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Found ${total_urls} unique URLs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# URL validation
validate_urls() {
    echo -e "\n${BLUE}[+] Validating discovered URLs for $workspace...${NC}"
    if [ ! -s "$workspace/result/wayback/wayback.txt" ]; then
        echo -e "${YELLOW}[!] No URLs found in wayback.txt for validation. Skipping URL validation.${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 0
    fi

    cat "$workspace/result/wayback/wayback.txt" | \
        ffuf -c -u "FUZZ" -w - -of csv -o "$workspace/result/wayback/valid-tmp.txt" -t 100 -rate 1000 || true
    
    cat "$workspace/result/wayback/valid-tmp.txt" 2>/dev/null | grep http | awk -F "," '{print $1}' >> "$workspace/result/wayback/valid.txt"
    rm -f "$workspace/result/wayback/valid-tmp.txt"
    
    valid_urls=$(wc -l < "$workspace/result/wayback/valid.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Found ${valid_urls} valid URLs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# GF pattern matching
run_gf_patterns() {
    echo -e "\n${BLUE}[+] Running pattern matching for $workspace...${NC}"
    
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
    )
    
    total_patterns=${#patterns[@]}
    current=0
    
    for pattern in "${!patterns[@]}"; do
        ((current++))
        echo -e "${MAGENTA}[*] ($current/$total_patterns) Checking for ${patterns[$pattern]}...${NC}"
        gf "$pattern" "$workspace/result/wayback/valid.txt" 2>/dev/null | tee "$workspace/result/gf/${pattern}.txt" || true
        count=$(wc -l < "$workspace/result/gf/${pattern}.txt" 2>/dev/null || echo "0")
        echo -e "${GREEN}[✓] Found ${count} potential ${patterns[$pattern]} endpoints${NC}"
    done
    
    echo -e "${GREEN}[✓] Pattern matching completed${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# XSS testing
test_xss() {
    echo -e "\n${BLUE}[+] Testing for XSS vulnerabilities for $workspace...${NC}"
    
    # Create results directory
    mkdir -p "$workspace/result/xss"
    
    echo -e "${MAGENTA}[*] Processing potential XSS endpoints...${NC}"
    if [ ! -s "$workspace/result/gf/xss.txt" ]; then
        echo -e "${YELLOW}[!] No potential XSS URLs found by GF. Skipping Dalfox scan.${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 0
    fi

    cat "$workspace/result/gf/xss.txt" 2>/dev/null | \
        grep -E '\bhttps?://[^[:space:]]+[?&][^[:space:]]+=[[^[:space:]]+' | \
        sort -u > "$workspace/result/xss/potential_xss.txt"
    
    sed 's/=.*/=/' "$workspace/result/xss/potential_xss.txt" > "$workspace/result/xss/urls_xss.txt"
    
    potential_count=$(wc -l < "$workspace/result/xss/potential_xss.txt" 2>/dev/null || echo "0")
    echo -e "${GREEN}[✓] Found ${potential_count} potential XSS endpoints${NC}"
    
    if [ "$potential_count" -gt 0 ]; then
        echo -e "${MAGENTA}[*] Running Dalfox XSS Scanner...${NC}"
        
        dalfox file "$workspace/result/xss/urls_xss.txt" \
            --skip-mining-all \
            --skip-grepping \
            --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
            --timeout 3 \
            --mass-worker 25 \
            --silence \
            --output "$workspace/result/xss/dalfox_results.txt" || true
        
        # Process Dalfox results and extract confirmed vulnerabilities
        if [ -f "$workspace/result/xss/dalfox_results.txt" ]; then
            echo -e "\n${GREEN}[✓] Dalfox scan completed${NC}"
            
            # Extract and format vulnerable URLs
            grep "POC" "$workspace/result/xss/dalfox_results.txt" | sort -u > "$workspace/result/xss/vulnerable.txt"
            
            vulnerable_count=$(wc -l < "$workspace/result/xss/vulnerable.txt" 2>/dev/null || echo "0")
            if [ "$vulnerable_count" -gt 0 ]; then
                echo -e "\n${RED}[!] Found $vulnerable_count confirmed XSS vulnerabilities for $workspace:${NC}"
                while IFS= read -r vuln; do
                    echo -e "${RED}[+] $vuln${NC}"
                done < "$workspace/result/xss/vulnerable.txt"
            else
                echo -e "${GREEN}[✓] No confirmed XSS vulnerabilities found for $workspace.${NC}"
            fi
        else
            echo -e "${YELLOW}[!] Dalfox results file not found or scan failed for $workspace.${NC}"
        fi
    else
        echo -e "${YELLOW}[!] No potential XSS endpoints to test for $workspace.${NC}"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Send results to Telegram
send_to_telegram() {
    echo -e "\n${BLUE}[+] Preparing to send results to Telegram for $workspace...${NC}"
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
    local total_urls_count=$(cat "$result_dir/wayback/wayback.txt" 2>/dev/null | wc -l)
    local valid_urls_count=$(cat "$result_dir/wayback/valid.txt" 2>/dev/null | wc -l)
    local potential_xss_count=$(cat "$workspace/result/xss/potential_xss.txt" 2>/dev/null | wc -l)
    local confirmed_xss_count=$(cat "$workspace/result/xss/vulnerable.txt" 2>/dev/null | wc -l)

    local message
    message=$(printf "🔍 *XSS Scan Completed for:* \`%s\`\n\n" "$workspace"
    printf "📊 *Summary:*\n"
    printf " • Total URLs Found: \`%s\`\n" "$total_urls_count"
    printf " • Valid URLs: \`%s\`\n" "$valid_urls_count"
    printf " • Potential XSS Endpoints: \`%s\`\n" "$potential_xss_count"
    printf " • *Confirmed XSS Vulnerabilities:* \`%s\`\n\n" "$confirmed_xss_count"
    printf "📤 Detailed results are attached in the zip file."
    )

    # Send summary message
    echo -e "${BLUE}[*] Sending summary message...${NC}"
    curl -s -X POST "https://api.telegram.org/bot$token/sendMessage" \
        -d chat_id="$chat_id" \
        -d text="$message" \
        -d parse_mode="Markdown" > /dev/null

    # Archive Results and Send
    if [ -d "$result_dir" ] && [ "$(ls -A "$result_dir")" ]; then
        local archive_name="results-$(basename "$workspace")-$(date +%F_%H-%M-%S).zip"
        
        echo -e "${BLUE}[*] Creating results archive: ${archive_name}${NC}"
        zip -r -j "$archive_name" "$result_dir" > /dev/null

        echo -e "${BLUE}[*] Uploading archive...${NC}"
        curl -s -X POST "https://api.telegram.org/bot$token/sendDocument" \
            -F chat_id="$chat_id" \
            -F document=@"$archive_name" \
            -F caption="All scan results for $workspace" > /dev/null
        
        rm "$archive_name"
    else
        echo -e "${YELLOW}[!] No result files found to archive in '$result_dir' for $workspace.${NC}"
    fi
    
    echo -e "${GREEN}[✓] Process completed. Results sent to Telegram for $workspace.${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    display_banner
    input_target # This will populate the domains_to_scan array

    if [ ${#domains_to_scan[@]} -eq 0 ]; then
        echo -e "${RED}[!] No domains found to scan. Exiting.${NC}"
        exit 1
    fi

    for domain in "${domains_to_scan[@]}"; do
        workspace="$domain" # Set global workspace variable for the current domain

        # Check if the directory already exists from a previous run, and if so, clean it up
        if [ -d "$workspace" ]; then
            echo -e "${YELLOW}[*] Deleting previous scan results for $workspace...${NC}"
            rm -rf "$workspace"
            sleep 1
        fi

        check_waf
        enumerate_domain
        probe_http
        collect_wayback
        validate_urls
        run_gf_patterns
        test_xss
        send_to_telegram
        echo -e "\n${GREEN}[✓] XSS scan completed for $workspace!${NC}\n"
    done

    echo -e "\n${GREEN}[✓] All requested XSS scans completed successfully!${NC}\n"
}

# Run the script
main

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
    figlet -w 100 -f small "Mass Auto CORS Detection"
    echo -e "${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Input target function
input_target() {
    clear
    echo -e "\n${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          Mass Auto CORS Detection          ${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"
    
    while true; do
        echo -e "${YELLOW}[?] Masukkan workspace target ${NC}(contoh: example.com)"
        echo -e "${YELLOW}[?] Ketik 'quit' untuk keluar${NC}"
        echo -ne "\n${GREEN}[+] Target workspace: ${NC}"
        read -r input
        
        # Validasi input
        if [[ -z "$input" ]]; then
            echo -e "\n${RED}[!] Error: workspace tidak boleh kosong!${NC}"
            sleep 1
            continue
        elif [[ "$input" == "quit" ]]; then
            echo -e "\n${YELLOW}[!] Keluar dari program...${NC}"
            exit 0
        elif ! [[ "$input" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
            echo -e "\n${RED}[!] Error: Format workspace tidak valid!${NC}"
            sleep 1
            continue
        fi
        
        # Jika validasi berhasil
        echo -e "\n${GREEN}[✓] workspace target valid: $input${NC}"
        echo -e "${BLUE}[*] Memulai pemindaian...${NC}\n"
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
    mkdir -p "$workspace"/{sources,result/{nuclei,httpx,sqli,wayback,gf}}
    
    echo -e "${MAGENTA}[*] Running Subfinder...${NC}"
    subfinder -d "$workspace" -o "$workspace/sources/subfinder.txt"
    
    echo -e "${MAGENTA}[*] Running Assetfinder...${NC}"
    assetfinder -subs-only "$workspace" | tee "$workspace/sources/assetfinder.txt"
    
    echo -e "${MAGENTA}[*] Combining results...${NC}"
    cat "$workspace/sources/"*.txt > "$workspace/sources/all.txt"
    
    total_workspaces=$(wc -l < "$workspace/sources/all.txt")
    echo -e "${GREEN}[✓] Found ${total_workspaces} subworkspaces${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# HTTP probe
probe_http() {
    echo -e "\n${BLUE}[+] Probing for live hosts...${NC}"
    
    # Probe hosts dan simpan hasil sementara
    temp_file=$(mktemp)
    cat "$workspace/sources/all.txt" | httprobe | tee "$temp_file"
    
    # Deduplikasi: prioritaskan HTTPS daripada HTTP
    echo -e "${YELLOW}[+] Removing duplicates (prioritizing HTTPS)...${NC}"
    
    # Ekstrak workspace unik dan tentukan protokol terbaik
    awk -F'://' '{
        workspace = $2
        protocol = $1
        
        # Jika workspace belum ada atau protokol saat ini adalah https
        if (!(workspace in workspaces) || protocol == "https") {
            workspaces[workspace] = protocol "://" workspace
        }
    }
    END {
        for (d in workspaces) {
            print workspaces[d]
        }
    }' "$temp_file" | sort > "$workspace/result/httpx/httpx.txt"
    
    # Hapus file temporary
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
    cat "$workspace/result/wayback/wayback.txt" | \
        ffuf -c -u "FUZZ" -w - -of csv -o "$workspace/result/wayback/valid-tmp.txt" -t 100 -rate 1000
    
    cat "$workspace/result/wayback/valid-tmp.txt" | grep http | awk -F "," '{print $1}' >> "$workspace/result/wayback/valid.txt"
    rm "$workspace/result/wayback/valid-tmp.txt"
    
    total_valid=$(wc -l < "$workspace/result/wayback/valid.txt")
    echo -e "${GREEN}[✓] Found ${total_valid} valid URLs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# GF pattern matching
run_gf_patterns() {
    echo -e "\n${BLUE}[+] Running pattern matching...${NC}"
    
    declare -A patterns=(
        ["sqli"]="SQL Injection"
        ["xss"]="Cross-Site Scripting"
        ["ssrf"]="Server-Side Request Forgery"
        ["rce"]="Remote Code Execution"
        ["idor"]="Insecure Direct Object Reference"
        ["lfi"]="Local File Inclusion"
        ["ssti"]="Server-Side Template Injection"
        ["debug_logic"]="Debug Logic"
        ["php-errors"]="PHP Errors"
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

test_cors() {
    echo -e "\n${BLUE}[+] Testing for CORS Misconfiguration vulnerabilities...${NC}"
    
    # Create results directory
    mkdir -p "$workspace/result/cors"
    
    # Create or check for URLs file
    if [[ ! -d "$workspace/result/gf" ]]; then
        mkdir -p "$workspace/result/gf"
    fi
    
    # If we don't have a specific CORS pattern file, we can use all discovered URLs
    if [[ ! -f "$workspace/result/gf/urls.txt" ]]; then
        echo -e "${YELLOW}[!] URL list not found! Using all discovered URLs.${NC}"
        find "$workspace" -name "*.txt" -type f -exec grep -l "http" {} \; | xargs cat | sort -u > "$workspace/result/gf/urls.txt"
    fi
    
    total_urls=$(wc -l < "$workspace/result/gf/urls.txt")
    current=0
    vulnerable=0
    
    # Origin values to test
    declare -a origins=(
        "https://evil.com"
        "https://attacker.com"
        "null"
        "https://subworkspace.${workspace#*//}"
        "https://${workspace#*//}.evil.com"
        "http://${workspace#*//}"
    )
    
    echo -e "${GREEN}[*] Testing $total_urls URLs for CORS misconfigurations${NC}"
    
    while IFS= read -r url; do
        ((current++))
        echo -e "\n${YELLOW}[*] Testing URL ($current/$total_urls): $url${NC}"
        
        for origin in "${origins[@]}"; do
            echo -e "${BLUE}[+] Testing with Origin: $origin${NC}"
            
            # Test CORS headers with modified Origin header
            response_headers=$(curl -s -I -H "Origin: $origin" -H "User-Agent: Mozilla/5.0" -L --max-time 10 "$url")
            
            # Check for Access-Control-Allow-Origin header
            acao=$(echo "$response_headers" | grep -i "Access-Control-Allow-Origin" | head -1)
            
            # Check for Access-Control-Allow-Credentials header
            acac=$(echo "$response_headers" | grep -i "Access-Control-Allow-Credentials" | head -1)
            
            # If ACAO header exists
            if [[ -n "$acao" ]]; then
                echo -e "${YELLOW}[*] Found CORS header: $acao${NC}"
                
                # Case 1: ACAO reflects our origin (most dangerous if credentials are allowed)
                if echo "$acao" | grep -q "$origin"; then
                    if [[ -n "$acac" ]] && echo "$acac" | grep -qi "true"; then
                        echo -e "${RED}[!] Critical CORS Misconfiguration: Origin reflection with credentials!${NC}"
                        echo -e "${RED}[!] Vulnerable URL: $url${NC}"
                        echo -e "${RED}[!] Allows Origin: $origin${NC}"
                        echo -e "${RED}[!] Allows Credentials: true${NC}"
                        echo "$url [Origin: $origin, Credentials: true]" >> "$workspace/result/cors/critical.txt"
                        ((vulnerable++))
                    else
                        echo -e "${ORANGE}[!] Moderate CORS Misconfiguration: Origin reflection!${NC}"
                        echo -e "${ORANGE}[!] Vulnerable URL: $url${NC}"
                        echo -e "${ORANGE}[!] Allows Origin: $origin${NC}"
                        echo "$url [Origin: $origin]" >> "$workspace/result/cors/moderate.txt"
                        ((vulnerable++))
                    fi
                # Case 2: ACAO is wildcard *
                elif echo "$acao" | grep -q "\*"; then
                    if [[ -n "$acac" ]] && echo "$acac" | grep -qi "true"; then
                        echo -e "${RED}[!] Warning: Wildcard origin with credentials (should not be possible)${NC}"
                        echo -e "${RED}[!] Unusual URL: $url${NC}"
                        echo "$url [Wildcard with credentials]" >> "$workspace/result/cors/unusual.txt"
                    else
                        echo -e "${YELLOW}[!] Low CORS Misconfiguration: Wildcard origin${NC}"
                        echo "$url [Wildcard]" >> "$workspace/result/cors/low.txt"
                    fi
                # Case 3: ACAO allows null origin
                elif echo "$acao" | grep -qi "null" && [[ "$origin" == "null" ]]; then
                    if [[ -n "$acac" ]] && echo "$acac" | grep -qi "true"; then
                        echo -e "${RED}[!] Critical CORS Misconfiguration: Null origin with credentials!${NC}"
                        echo -e "${RED}[!] Vulnerable URL: $url${NC}"
                        echo "$url [Null origin with credentials]" >> "$workspace/result/cors/critical.txt"
                        ((vulnerable++))
                    else
                        echo -e "${ORANGE}[!] Moderate CORS Misconfiguration: Null origin allowed!${NC}"
                        echo -e "${ORANGE}[!] Vulnerable URL: $url${NC}"
                        echo "$url [Null origin]" >> "$workspace/result/cors/moderate.txt"
                        ((vulnerable++))
                    fi
                # Case 4: Check if ACAO trusts all subworkspaces (weak configuration)
                elif [[ "$origin" == *"${workspace#*//}"* ]] && echo "$acao" | grep -q "$origin"; then
                    echo -e "${YELLOW}[!] Weak CORS Configuration: Trusts subworkspaces${NC}"
                    echo -e "${YELLOW}[!] URL: $url${NC}"
                    echo "$url [Trusts subworkspaces: $origin]" >> "$workspace/result/cors/weak.txt"
                    ((vulnerable++))
                fi
                
                # Check for additional dangerous CORS headers
                acam=$(echo "$response_headers" | grep -i "Access-Control-Allow-Methods" | head -1)
                acah=$(echo "$response_headers" | grep -i "Access-Control-Allow-Headers" | head -1)
                
                if [[ -n "$acam" ]] && echo "$acam" | grep -qi -E "PUT|DELETE|PATCH"; then
                    echo -e "${YELLOW}[!] Potentially risky methods allowed: $acam${NC}"
                    echo "$url [Risky methods: $acam]" >> "$workspace/result/cors/methods.txt"
                fi
                
                if [[ -n "$acah" ]] && echo "$acah" | grep -qi -E "Authorization|Cookie|X-CSRF-Token"; then
                    echo -e "${YELLOW}[!] Sensitive headers allowed: $acah${NC}"
                    echo "$url [Sensitive headers: $acah]" >> "$workspace/result/cors/headers.txt"
                fi
            fi
        done
    done < "$workspace/result/gf/urls.txt"
    
    # Compile summary report
    echo -e "\n${BLUE}[*] CORS Vulnerability Summary:${NC}"
    
    if [ -f "$workspace/result/cors/critical.txt" ] && [ -s "$workspace/result/cors/critical.txt" ]; then
        echo -e "\n${RED}[!] Critical CORS Vulnerabilities:${NC}"
        cat "$workspace/result/cors/critical.txt"
    fi
    
    if [ -f "$workspace/result/cors/moderate.txt" ] && [ -s "$workspace/result/cors/moderate.txt" ]; then
        echo -e "\n${ORANGE}[!] Moderate CORS Vulnerabilities:${NC}"
        cat "$workspace/result/cors/moderate.txt"
    fi
    
    if [ -f "$workspace/result/cors/weak.txt" ] && [ -s "$workspace/result/cors/weak.txt" ]; then
        echo -e "\n${YELLOW}[!] Weak CORS Configurations:${NC}"
        cat "$workspace/result/cors/weak.txt"
    fi
    
    if [ -f "$workspace/result/cors/low.txt" ] && [ -s "$workspace/result/cors/low.txt" ]; then
        echo -e "\n${YELLOW}[!] Low Risk CORS Issues:${NC}"
        cat "$workspace/result/cors/low.txt"
    fi
    
    if [ -f "$workspace/result/cors/methods.txt" ] && [ -s "$workspace/result/cors/methods.txt" ]; then
        echo -e "\n${YELLOW}[!] Risky HTTP Methods Allowed:${NC}"
        cat "$workspace/result/cors/methods.txt"
    fi
    
    if [ -f "$workspace/result/cors/headers.txt" ] && [ -s "$workspace/result/cors/headers.txt" ]; then
        echo -e "\n${YELLOW}[!] Sensitive Headers Allowed:${NC}"
        cat "$workspace/result/cors/headers.txt"
    fi
    
    echo -e "\n${GREEN}[✓] Total potential CORS vulnerabilities: $vulnerable${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Send results to Telegram
send_to_telegram() {
    echo -e "\n${BLUE}[+] Sending results to Telegram...${NC}"
    
    if [[ -f telegram_token.txt && -f telegram_chat_id.txt ]]; then
        token=$(cat telegram_token.txt)
        chat_id=$(cat telegram_chat_id.txt)
        
        # Send initial message with summary
        message="🔍 Reconnaissance completed for: $workspace
📊 Summary:
• Subworkspaces found: $(wc -l < "$workspace/sources/all.txt")
• Live hosts: $(wc -l < "$workspace/result/httpx/httpx.txt")
• Unique URLs: $(wc -l < "$workspace/result/wayback/wayback.txt")
• Valid URLs: $(wc -l < "$workspace/result/wayback/valid.txt")
📤 Sending detailed results..."

        curl -s -X POST "https://api.telegram.org/bot$token/sendMessage" \
             -d chat_id="$chat_id" \
             -d text="$message" > /dev/null 2>&1

        # Send files
        total_files=$(find "$workspace" -type f | wc -l)
        current=0
        
        find "$workspace" -type f | while read -r file; do
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
    enumerate_workspace
    probe_http
    collect_wayback
    validate_urls
    run_gf_patterns
    test_cors
    send_to_telegram
    echo -e "\n${GREEN}[✓] Mass CORS scan completed successfully!${NC}\n"
}

# Run the script
main
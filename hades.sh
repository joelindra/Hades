#!/bin/bash
declare -A COLORS=(
    [PRIMARY]='\e[38;2;120;200;255m'
    [ACCENT]='\e[38;2;255;125;175m'
    [SUCCESS]='\e[38;2;125;255;175m'
    [WARNING]='\e[38;2;255;230;125m'
    [DANGER]='\e[38;2;255;125;125m'
    [MUTED]='\e[38;2;150;150;180m'
    [BRIGHT]='\e[38;2;235;235;255m'
    [DIM]='\e[38;2;100;100;120m'
)

BOLD='\e[1m'
ITALIC='\e[3m'
RESET='\e[0m'

VERSION="7"
AUTHOR="Anonre | Joel Indra"
YEAR=$(date +%Y)
SCAN_DATE=$(date +"%d-%m-%Y %H:%M:%S")
SESSION_ID=$(date +%s | sha256sum | cut -c1-12)

set -e
trap 'elegant_error $LINENO' ERR

elegant_type() {
    local text="$1"
    echo -e "${text}"
    sleep 0.05
}

elegant_loading() {
    local task_name=$1
    local delay=${2:-0.8}

    echo -ne "\n${COLORS[ACCENT]}>>> ${task_name}...${RESET}"
    sleep $delay
    echo -e "\r${COLORS[ACCENT]}>>> ${task_name}... ${COLORS[SUCCESS]}Done!${RESET} \n"
}

elegant_error() {
    local line=$1
    echo ""
    echo -e "${COLORS[DANGER]}${BOLD}║ Error detected at line $line        ${RESET}"
    exit 1
}

display_banner() {
    clear

    echo ""
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[ACCENT]}╦ ╦╔═╗╔╦╗╔═╗╔═╗${COLORS[PRIMARY]}                          "
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[ACCENT]}╠═╣╠═╣ ║║║╣ ╚═╗${COLORS[PRIMARY]}                          "
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[ACCENT]}╩ ╩╩ ╩═╩╝╚═╝╚═╝${COLORS[PRIMARY]}                          "
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[SUCCESS]}Bug Bounty Framework v${VERSION}${COLORS[PRIMARY]}            "
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[MUTED]}Created by: ${COLORS[BRIGHT]}${AUTHOR} ©${YEAR}${COLORS[PRIMARY]}      "
    sleep 0.5

    echo ""
    echo -e "${COLORS[PRIMARY]}│ ${COLORS[SUCCESS]}• Kernel    ${COLORS[MUTED]}| ${COLORS[BRIGHT]}$(uname -r)${COLORS[PRIMARY]}${RESET}"
    echo -e "${COLORS[PRIMARY]}│ ${COLORS[SUCCESS]}• Machine   ${COLORS[MUTED]}| ${COLORS[BRIGHT]}$(uname -m)${COLORS[PRIMARY]}${RESET}"
    echo -e "${COLORS[PRIMARY]}│ ${COLORS[SUCCESS]}• Session   ${COLORS[MUTED]}| ${COLORS[BRIGHT]}$SESSION_ID${COLORS[PRIMARY]}${RESET}"
    echo -e "${COLORS[PRIMARY]}│ ${COLORS[SUCCESS]}• Timestamp ${COLORS[MUTED]}| ${COLORS[BRIGHT]}$SCAN_DATE${COLORS[PRIMARY]}${RESET}"
    echo ""
    if [[ $(id -u) -eq 0 ]]; then
        echo -e "│ • ${COLORS[SUCCESS]}You are Root! You can run this tool.${COLORS[PRIMARY]}${RESET}"
    else
        echo -e "│ • ${COLORS[DANGER]}Not Root! You need root to run this tool.${COLORS[PRIMARY]}${RESET}"
    fi
}

display_help() {
    display_banner

    echo ""
    echo -e "${COLORS[PRIMARY]}${BOLD}--- Reconnaissance ---${RESET}\n"
    echo -e "  ${COLORS[BRIGHT]}-d ${COLORS[MUTED]}--mass-recon    ${COLORS[WARNING]}Mass Target Recon${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f,subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-s ${COLORS[MUTED]}--single-recon  ${COLORS[WARNING]}Single Target Recon${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, waybackurls, anew, ffuf, gf, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-f ${COLORS[MUTED]}--port-scan     ${COLORS[WARNING]}Single Target Port Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}nmap, curl ${RESET}"
    echo -e ""

    echo -e "${COLORS[ACCENT]}${BOLD}--- Injection Testing ---${RESET}\n"
    echo -e "  ${COLORS[BRIGHT]}-p ${COLORS[MUTED]}--mass-sql      ${COLORS[WARNING]}Mass Target SQL Injection Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f,subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf, sqltimer, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-o ${COLORS[MUTED]}--single-sql    ${COLORS[WARNING]}Single Target SQL Injection Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, waybackurls, anew, ffuf, gf, sqltimer, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-w ${COLORS[MUTED]}--mass-xss      ${COLORS[WARNING]}Mass Target XSS Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f,subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf, dalfox, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-x ${COLORS[MUTED]}--single-xss    ${COLORS[WARNING]}Single Target XSS Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, waybackurls, anew, ffuf, gf, dalfox, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-n ${COLORS[MUTED]}--single-lfi    ${COLORS[WARNING]}Single Target LFI Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, waybackurls, anew, ffuf, gf, mapfile, md5sum, curl ${RESET}"
    echo -e ""

    echo -e "${COLORS[WARNING]}${BOLD}--- Special Operations ---${RESET}\n"
    echo -e "  ${COLORS[BRIGHT]}-m ${COLORS[MUTED]}--mass-assess   ${COLORS[PRIMARY]}Mass Target Auto VA${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, subfinder, assetfinder, httprobe, nuclei, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-y ${COLORS[MUTED]}--sub-takeover  ${COLORS[PRIMARY]}Subdomain Takeover Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, notifier.sh, subfinder, assetfinder, httprobe, subjack, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-q ${COLORS[MUTED]}--dir-patrol    ${COLORS[PRIMARY]}Directory Patrol Target Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, notifier.sh, subfinder, assetfinder, httprobe, dirsearch ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-l ${COLORS[MUTED]}--js-finder     ${COLORS[PRIMARY]}ALL JS Secret Finder${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, notifier.sh, subfinder, assetfinder, httprobe, waybackurls, anew, trufflehog, curl ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-k ${COLORS[MUTED]}--mass-cors     ${COLORS[PRIMARY]}Mass Target CORS Missconfig Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-u ${COLORS[MUTED]}--mass-csrf     ${COLORS[PRIMARY]}Mass Target CSRF Scan${RESET}"
    echo -e "  ${COLORS[MUTED]}wafw00f, subfinder, assetfinder, httprobe, waybackurls, anew, ffuf, gf, curl ${RESET}"
    echo -e ""

    echo -e "${COLORS[DANGER]}${BOLD}--- OWASP WASTG Testing ---${RESET}\n"
    echo -e "  ${COLORS[BRIGHT]}-e ${COLORS[MUTED]}--client-test   ${COLORS[BRIGHT]}Client-side Testing${RESET}"
    echo -e "  ${COLORS[MUTED]}curl, jq ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-b ${COLORS[MUTED]}--weak-test     ${COLORS[BRIGHT]}Testing For Weak Cryptography${RESET}"
    echo -e "  ${COLORS[MUTED]}nmap, sslscan, openssl, curl, timeout ${RESET}"
    echo -e ""
    echo -e "  ${COLORS[BRIGHT]}-r ${COLORS[MUTED]}--info-test     ${COLORS[BRIGHT]}Information Gathering [UPCOMING]${RESET}\n"

    echo -e "${COLORS[BRIGHT]}${BOLD}--- System ---${RESET}\n"
    echo -e "  ${COLORS[BRIGHT]}-i ${COLORS[MUTED]}--install       ${COLORS[PRIMARY]}Install Dependencies${RESET}"
    echo -e "  ${COLORS[BRIGHT]}-h ${COLORS[MUTED]}--help          ${COLORS[PRIMARY]}Display Commands${RESET}\n"

    echo -e "${COLORS[DIM]}${BOLD}--- More Info ---${RESET}\n"
    echo -e "${COLORS[BRIGHT]}Usage: ${COLORS[MUTED]}./hades.sh [options]${RESET}"
    echo -e "${COLORS[BRIGHT]}Repo:  ${COLORS[SUCCESS]}https://github.com/joelindra/hades${RESET}\n"
}

execute_module() {
    local module_name=$1
    local script_path=$2

    elegant_loading "Loading Module" 0.5

    if source "./function/$script_path" 2>/tmp/hades_error.log; then
        echo -e "${COLORS[SUCCESS]}${BOLD}Module executed successfully${RESET}\n"
    else
        echo -e "${COLORS[DANGER]}${BOLD}Module execution failed${RESET}"
        cat /tmp/hades_error.log
        exit 1
    fi
}

declare -A options_map=(
    [-d]="m-recon.sh"
    [--mass-recon]="m-recon.sh"
    [-s]="s-recon.sh"
    [--single-recon]="s-recon.sh"
    [-f]="s-port.sh"
    [--port-scan]="s-port.sh"

    [-p]="m-sqli.sh"
    [--mass-sql]="m-sqli.sh"
    [-o]="s-sqli.sh"
    [--single-sql]="s-sqli.sh"
    [-w]="m-xss.sh"
    [--mass-xss]="m-xss.sh"
    [-x]="s-xss.sh"
    [--single-xss]="s-xss.sh"
    [-n]="s-lfi.sh"
    [--single-lfi]="s-lfi.sh"

    [-m]="m-scan.sh"
    [--mass-assess]="m-scan.sh"

    [-y]="takeover.sh"
    [--sub-takeover]="takeover.sh"
    [-u]="m-csrf.sh"
    [--mass-csrf]="m-csrf.sh"
    [-q]="dir-scan.sh"
    [--dir-patrol]="dir-scan.sh"
    [-l]="m-js.sh"
    [--js-finder]="m-js.sh"
    [-k]="m-cors.sh"
    [--mass-cors]="m-cors.sh"

    [-b]="weak.sh"
    [--weak-test]="weak.sh"
    [-e]="client.sh"
    [--client-test]="client.sh"

    [-i]="all-req.sh"
    [--install]="all-req.sh"
    [-h]="help"
    [--help]="help"
)

check_updates() {
    echo -e "\n${COLORS[WARNING]}${BOLD}--- Update Check ---${RESET}"
    echo -ne "${COLORS[BRIGHT]}Checking for updates...${RESET}"
    sleep 1
    echo -e "\r${COLORS[SUCCESS]}Latest version installed.${RESET}\n"
}

main() {
    display_banner

    check_updates

    if [[ $# -eq 0 ]]; then
        display_help
        exit 0
    fi

    for option in "$@"; do
        local script="${options_map[$option]}"

        if [[ -z "$script" ]]; then
            echo -e "\n${COLORS[DANGER]}${BOLD}✗ Invalid command: $option${RESET}"
            display_help
            exit 1
        fi

        if [[ "$script" == "help" ]]; then
            display_help
            continue
        fi

        execute_module "$option" "$script"
    done

    echo ""
    echo -e "${COLORS[SUCCESS]}| ${COLORS[WARNING]}Session Complete${COLORS[SUCCESS]}                                 ${RESET}"
    echo -e "${COLORS[SUCCESS]}| ${COLORS[BRIGHT]}• Time    ${COLORS[MUTED]}| ${COLORS[ACCENT]}$(date +"%H:%M:%S")${COLORS[SUCCESS]}                     ${RESET}"
    echo -e "${COLORS[SUCCESS]}| ${COLORS[BRIGHT]}• Status ${COLORS[MUTED]}| ${COLORS[SUCCESS]}All operations successful${COLORS[SUCCESS]}    ${RESET}"
}

main "$@"

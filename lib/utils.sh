#!/bin/bash

# HADES Utility Library
# Common utility functions

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Source dependencies
source "${SCRIPT_DIR}/lib/colors.sh"
source "${SCRIPT_DIR}/lib/logger.sh"

# Check if running as root
check_root() {
    if [[ $(id -u) -ne 0 ]]; then
        log_error "This script requires root privileges"
        return 1
    fi
    return 0
}

# Check internet connection
check_internet() {
    log_info "Checking internet connection..."
    
    if ping -c 1 -W 2 8.8.8.8 &> /dev/null || ping -c 1 -W 2 google.com &> /dev/null; then
        log_info "Internet connection: ONLINE"
        return 0
    else
        log_error "Internet connection: OFFLINE"
        return 1
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check required commands
check_required_commands() {
    local missing=()
    local commands=("$@")
    
    for cmd in "${commands[@]}"; do
        if ! command_exists "$cmd"; then
            missing+=("$cmd")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing[*]}"
        log_info "Run './hades.sh --install' to install dependencies"
        return 1
    fi
    
    return 0
}

# Create directory structure for target
create_target_structure() {
    local target="$1"
    local base_dir=$(get_output_dir "$target")
    
    mkdir -p "${base_dir}/sources"
    mkdir -p "${base_dir}/results/nuclei"
    mkdir -p "${base_dir}/results/wayback"
    mkdir -p "${base_dir}/results/httpx"
    mkdir -p "${base_dir}/results/exploit"
    mkdir -p "${base_dir}/results/js"
    mkdir -p "${base_dir}/results/gf"
    mkdir -p "${base_dir}/results/logs"
    
    echo "$base_dir"
}

# Count lines in file (safe)
count_lines() {
    local file="$1"
    if [[ -f "$file" ]] && [[ -s "$file" ]]; then
        wc -l < "$file" | tr -d ' '
    else
        echo "0"
    fi
}

# Remove duplicates from file (prioritize HTTPS)
deduplicate_urls() {
    local input_file="$1"
    local output_file="$2"
    
    awk -F'://' '{
        domain = $2
        protocol = $1
        
        if (!(domain in domains) || protocol == "https") {
            domains[domain] = protocol "://" domain
        }
    }
    END {
        for (d in domains) {
            print domains[d]
        }
    }' "$input_file" | sort > "$output_file"
}

# Send message to Telegram
send_telegram_message() {
    local message="$1"
    local token=$(get_config "TELEGRAM_TOKEN")
    local chat_id=$(get_config "TELEGRAM_CHAT_ID")
    local user_agent=$(get_config "USER_AGENT")
    
    if [[ -z "$token" ]] || [[ -z "$chat_id" ]]; then
        log_warning "Telegram not configured, skipping notification"
        return 1
    fi
    
    curl -s -X POST "https://api.telegram.org/bot${token}/sendMessage" \
        -H "User-Agent: ${user_agent}" \
        -d chat_id="$chat_id" \
        -d text="$message" \
        -d parse_mode="Markdown" > /dev/null 2>&1
    
    if [[ $? -eq 0 ]]; then
        log_info "Telegram message sent"
        return 0
    else
        log_error "Failed to send Telegram message"
        return 1
    fi
}

# Send file to Telegram
send_telegram_file() {
    local file_path="$1"
    local caption="$2"
    local token=$(get_config "TELEGRAM_TOKEN")
    local chat_id=$(get_config "TELEGRAM_CHAT_ID")
    local user_agent=$(get_config "USER_AGENT")
    
    if [[ -z "$token" ]] || [[ -z "$chat_id" ]]; then
        log_warning "Telegram not configured, skipping file upload"
        return 1
    fi
    
    if [[ ! -f "$file_path" ]]; then
        log_error "File not found: $file_path"
        return 1
    fi
    
    curl -s -X POST "https://api.telegram.org/bot${token}/sendDocument" \
        -H "User-Agent: ${user_agent}" \
        -F chat_id="$chat_id" \
        -F document=@"$file_path" \
        -F caption="$caption" > /dev/null 2>&1
    
    if [[ $? -eq 0 ]]; then
        log_info "Telegram file sent: $(basename "$file_path")"
        return 0
    else
        log_error "Failed to send Telegram file"
        return 1
    fi
}

# Send message to Discord
send_discord_message() {
    local message="$1"
    local webhook=$(get_config "DISCORD_WEBHOOK")
    local user_agent=$(get_config "USER_AGENT")
    
    if [[ -z "$webhook" ]]; then
        log_warning "Discord not configured, skipping notification"
        return 1
    fi
    
    # Format message as Discord embed
    local json_payload=$(cat <<EOF
{
  "content": "🔔 **HADES Security Scan Notification**",
  "embeds": [{
    "title": "Scan Update",
    "description": "$(echo "$message" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')",
    "color": 5814783,
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }]
}
EOF
)
    
    curl -s -X POST "$webhook" \
        -H "User-Agent: ${user_agent}" \
        -H "Content-Type: application/json" \
        -d "$json_payload" > /dev/null 2>&1
    
    if [[ $? -eq 0 ]]; then
        log_info "Discord message sent"
        return 0
    else
        log_error "Failed to send Discord message"
        return 1
    fi
}

# Send file to Discord (via webhook with file upload)
send_discord_file() {
    local file_path="$1"
    local caption="$2"
    local webhook=$(get_config "DISCORD_WEBHOOK")
    local user_agent=$(get_config "USER_AGENT")
    
    if [[ -z "$webhook" ]]; then
        log_warning "Discord not configured, skipping file upload"
        return 1
    fi
    
    if [[ ! -f "$file_path" ]]; then
        log_error "File not found: $file_path"
        return 1
    fi
    
    # Discord webhooks don't support file uploads directly
    # We'll send a message with file info instead
    local file_size=$(du -h "$file_path" | cut -f1)
    local json_payload=$(cat <<EOF
{
  "content": "📎 **File: $(basename "$file_path")**",
  "embeds": [{
    "title": "$(echo "$caption" | sed 's/"/\\"/g')",
    "description": "File: \`$(basename "$file_path")\`\\nSize: $file_size\\n\\n*Note: Discord webhooks don't support file uploads. Please download from the scan directory.*",
    "color": 5814783,
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }]
}
EOF
)
    
    curl -s -X POST "$webhook" \
        -H "User-Agent: ${user_agent}" \
        -H "Content-Type: application/json" \
        -d "$json_payload" > /dev/null 2>&1
    
    if [[ $? -eq 0 ]]; then
        log_info "Discord file notification sent: $(basename "$file_path")"
        return 0
    else
        log_error "Failed to send Discord file notification"
        return 1
    fi
}

# Send notification (Telegram or Discord based on config)
send_notification() {
    local message="$1"
    local file_path="${2:-}"
    local caption="${3:-}"
    
    # Check Telegram
    local telegram_enabled=$(get_config "TELEGRAM_ENABLED")
    if [[ "$telegram_enabled" == "true" ]] || [[ -n "$(get_config "TELEGRAM_TOKEN")" ]]; then
        if [[ -n "$file_path" ]]; then
            send_telegram_file "$file_path" "$caption"
        else
            send_telegram_message "$message"
        fi
    fi
    
    # Check Discord
    local discord_enabled=$(get_config "DISCORD_ENABLED")
    if [[ "$discord_enabled" == "true" ]] || [[ -n "$(get_config "DISCORD_WEBHOOK")" ]]; then
        if [[ -n "$file_path" ]]; then
            send_discord_file "$file_path" "$caption"
        else
            send_discord_message "$message"
        fi
    fi
}

# Create archive and send to Telegram/Discord
archive_and_send() {
    local source_dir="$1"
    local target_name="$2"
    local archive_name="hades-${target_name}-$(date +%Y%m%d-%H%M%S).zip"
    
    if [[ ! -d "$source_dir" ]] || [[ -z "$(ls -A "$source_dir" 2>/dev/null)" ]]; then
        log_warning "No files to archive in: $source_dir"
        return 1
    fi
    
    log_info "Creating archive: $archive_name"
    zip -r -q "$archive_name" "$source_dir" > /dev/null 2>&1
    
    if [[ $? -eq 0 ]] && [[ -f "$archive_name" ]]; then
        send_notification "" "$archive_name" "Scan results for $target_name"
        rm -f "$archive_name"
        log_info "Archive sent and removed"
        return 0
    else
        log_error "Failed to create archive"
        return 1
    fi
}

# Display banner
display_banner() {
    clear
    echo ""
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[ACCENT]}╦ ╦╔═╗╔╦╗╔═╗╔═╗${COLORS[PRIMARY]}                          "
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[ACCENT]}╠═╣╠═╣ ║║║╣ ╚═╗${COLORS[PRIMARY]}                          "
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[ACCENT]}╩ ╩╩ ╩═╩╝╚═╝╚═╝${COLORS[PRIMARY]}                          "
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[SUCCESS]}Bug Bounty Framework v7${COLORS[PRIMARY]}            "
    echo -e "${COLORS[PRIMARY]}│  ${COLORS[MUTED]}Created by: ${COLORS[BRIGHT]}Anonre | Joel Indra ©$(date +%Y)${COLORS[PRIMARY]}      "
    echo ""
}

# Show progress
show_progress() {
    local current=$1
    local total=$2
    local task="$3"
    
    local percent=$((current * 100 / total))
    local bar_length=30
    local filled=$((percent * bar_length / 100))
    local empty=$((bar_length - filled))
    
    local bar=$(printf "%${filled}s" | tr ' ' '█')
    local empty_bar=$(printf "%${empty}s" | tr ' ' '░')
    
    echo -ne "\r${COLORS[INFO]}[$current/$total]${RESET} $task ${COLORS[ACCENT]}[$bar$empty_bar]${RESET} ${percent}%"
    
    if [[ $current -eq $total ]]; then
        echo ""
    fi
}


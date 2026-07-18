#!/bin/bash

# HADES Configuration Library
# Centralized configuration management with YAML support

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/config"
DATA_DIR="${SCRIPT_DIR}/data"
OUTPUT_DIR="${SCRIPT_DIR}/output"
CONFIG_YAML="${CONFIG_DIR}/config.yaml"

# Source dependencies
source "${SCRIPT_DIR}/lib/colors.sh"
source "${SCRIPT_DIR}/lib/logger.sh"
source "${SCRIPT_DIR}/lib/validation.sh"
source "${SCRIPT_DIR}/lib/yaml_parser.sh"

# YAML configuration storage
declare -A YAML_CONFIG

# Default configuration values (fallback if YAML not available)
declare -A CONFIG=(
    [TELEGRAM_TOKEN]=""
    [TELEGRAM_CHAT_ID]=""
    [TELEGRAM_ENABLED]="false"
    [DISCORD_WEBHOOK]=""
    [DISCORD_ENABLED]="false"
    [OUTPUT_DIR]="$OUTPUT_DIR"
    [LOG_LEVEL]="INFO"
    [MAX_CONCURRENT_SCANS]="5"
    [RATE_LIMIT]="100"
    [TIMEOUT]="30"
    [USER_AGENT]="HADES-Security-Scanner/7.0"
    [VERSION]="7.0"
    [FRAMEWORK_NAME]="HADES"
    [AUTHOR]="Anonre | Joel Indra"
)

# Load YAML configuration
load_yaml_config() {
    if [[ -f "$CONFIG_YAML" ]]; then
        log_debug "Loading YAML configuration from $CONFIG_YAML"
        yaml_load_config "$CONFIG_YAML" "YAML_CONFIG"
        
        # Map YAML values to CONFIG array
        # Framework info
        CONFIG[VERSION]=$(yaml_get "$CONFIG_YAML" "framework.version" 2>/dev/null | tr -d '\n\r' || echo "7.0")
        CONFIG[FRAMEWORK_NAME]=$(yaml_get "$CONFIG_YAML" "framework.name" 2>/dev/null | tr -d '\n\r' || echo "HADES")
        CONFIG[EDITION]=$(yaml_get "$CONFIG_YAML" "framework.edition" 2>/dev/null | tr -d '\n\r' || echo "")
        CONFIG[AUTHOR]=$(yaml_get "$CONFIG_YAML" "framework.author" 2>/dev/null | tr -d '\n\r' || echo "Anonre | Joel Indra")
        
        # Application settings
        CONFIG[USER_AGENT]=$(yaml_get "$CONFIG_YAML" "application.user_agent" 2>/dev/null | tr -d '\n\r' || echo "HADES-Security-Scanner/7.0")
        
        # Logging
        CONFIG[LOG_LEVEL]=$(yaml_get "$CONFIG_YAML" "logging.level" 2>/dev/null | tr -d '\n\r' || echo "INFO")
        CONFIG[LOG_DIRECTORY]=$(yaml_get "$CONFIG_YAML" "logging.directory" 2>/dev/null | tr -d '\n\r' || echo "./logs")
        
        # Output
        CONFIG[OUTPUT_DIR]=$(yaml_get "$CONFIG_YAML" "output.directory" 2>/dev/null | tr -d '\n\r' || echo "$OUTPUT_DIR")
        
        # Scanning
        CONFIG[MAX_CONCURRENT_SCANS]=$(yaml_get "$CONFIG_YAML" "scanning.max_concurrent_scans" 2>/dev/null | tr -d '\n\r' || echo "5")
        CONFIG[RATE_LIMIT]=$(yaml_get "$CONFIG_YAML" "scanning.rate_limit" 2>/dev/null | tr -d '\n\r' || echo "100")
        CONFIG[TIMEOUT]=$(yaml_get "$CONFIG_YAML" "scanning.timeout" 2>/dev/null | tr -d '\n\r' || echo "30")
        
        # Telegram (still load from txt files for security)
        CONFIG[TELEGRAM_ENABLED]=$(yaml_get "$CONFIG_YAML" "notifications.telegram.enabled" 2>/dev/null | tr -d '\n\r' || echo "false")
        if [[ -f "${CONFIG_DIR}/telegram_token.txt" ]]; then
            CONFIG[TELEGRAM_TOKEN]=$(cat "${CONFIG_DIR}/telegram_token.txt" | tr -d '\n\r ')
        fi
        if [[ -f "${CONFIG_DIR}/telegram_chat_id.txt" ]]; then
            CONFIG[TELEGRAM_CHAT_ID]=$(cat "${CONFIG_DIR}/telegram_chat_id.txt" | tr -d '\n\r ')
        fi
        
        # Discord (still load from txt files for security)
        CONFIG[DISCORD_ENABLED]=$(yaml_get "$CONFIG_YAML" "notifications.discord.enabled" 2>/dev/null | tr -d '\n\r' || echo "false")
        if [[ -f "${CONFIG_DIR}/discord_webhook.txt" ]]; then
            CONFIG[DISCORD_WEBHOOK]=$(cat "${CONFIG_DIR}/discord_webhook.txt" | tr -d '\n\r ')
        fi
        
        log_info "YAML configuration loaded successfully"
        return 0
    else
        log_warning "YAML config file not found: $CONFIG_YAML"
        return 1
    fi
}

# Load configuration from files
load_config() {
    # Load YAML config first
    load_yaml_config
    
    # Load Telegram credentials from text files (for security)
    if [[ -f "${CONFIG_DIR}/telegram_token.txt" ]]; then
        CONFIG[TELEGRAM_TOKEN]=$(cat "${CONFIG_DIR}/telegram_token.txt" | tr -d '\n\r ')
    fi
    
    if [[ -f "${CONFIG_DIR}/telegram_chat_id.txt" ]]; then
        CONFIG[TELEGRAM_CHAT_ID]=$(cat "${CONFIG_DIR}/telegram_chat_id.txt" | tr -d '\n\r ')
    fi
    
    # Load Discord webhook from text file (for security)
    if [[ -f "${CONFIG_DIR}/discord_webhook.txt" ]]; then
        CONFIG[DISCORD_WEBHOOK]=$(cat "${CONFIG_DIR}/discord_webhook.txt" | tr -d '\n\r ')
    fi
    
    # Load legacy config file if exists (for backward compatibility)
    if [[ -f "${CONFIG_DIR}/hades.conf" ]]; then
        source "${CONFIG_DIR}/hades.conf"
    fi
    
    log_debug "Configuration loaded (Version: ${CONFIG[VERSION]})"
}

# Get config value
get_config() {
    local key="$1"
    local value="${CONFIG[$key]}"
    # Remove any remaining quotes and newlines
    echo "$value" | sed 's/^"//;s/"$//' | tr -d '\n\r'
}

# Set config value
set_config() {
    local key="$1"
    local value="$2"
    CONFIG[$key]="$value"
    log_debug "Config set: $key=$value"
}

# Get data file path
get_data_file() {
    local filename="$1"
    local filepath="${DATA_DIR}/${filename}"
    
    if [[ -f "$filepath" ]]; then
        echo "$filepath"
    else
        log_warning "Data file not found: $filename"
        echo ""
    fi
}

# Get output directory for target
get_output_dir() {
    local target="$1"
    local sanitized=$(sanitize_filename "$target")
    local output_path="${OUTPUT_DIR}/${sanitized}"
    mkdir -p "$output_path"
    echo "$output_path"
}

# Initialize configuration
init_config() {
    # Ensure directories exist
    mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$OUTPUT_DIR"
    
    # Load configuration
    load_config
    
    log_info "Configuration initialized"
}

# Check if Telegram is configured
is_telegram_configured() {
    if [[ -n "${CONFIG[TELEGRAM_TOKEN]}" ]] && [[ -n "${CONFIG[TELEGRAM_CHAT_ID]}" ]]; then
        return 0
    fi
    return 1
}


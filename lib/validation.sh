#!/bin/bash

# HADES Validation Library
# Input validation and sanitization functions

# Source colors and logger
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${SCRIPT_DIR}/lib/colors.sh"
source "${SCRIPT_DIR}/lib/logger.sh"

# Validate domain format
validate_domain() {
    local domain="$1"
    
    if [[ -z "$domain" ]]; then
        log_error "Domain cannot be empty"
        return 1
    fi
    
    # Basic domain validation regex
    if ! [[ "$domain" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        log_error "Invalid domain format: $domain"
        return 1
    fi
    
    # Additional checks
    if [[ "$domain" =~ \.\. ]]; then
        log_error "Domain contains consecutive dots: $domain"
        return 1
    fi
    
    if [[ "$domain" =~ ^\. ]] || [[ "$domain" =~ \.$ ]]; then
        log_error "Domain starts or ends with dot: $domain"
        return 1
    fi
    
    log_debug "Domain validation passed: $domain"
    return 0
}

# Validate URL format
validate_url() {
    local url="$1"
    
    if [[ -z "$url" ]]; then
        log_error "URL cannot be empty"
        return 1
    fi
    
    # Basic URL validation
    if ! [[ "$url" =~ ^https?:// ]]; then
        log_error "URL must start with http:// or https://: $url"
        return 1
    fi
    
    # Extract domain from URL
    local domain=$(echo "$url" | sed -E 's|^https?://([^/]+).*|\1|')
    if ! validate_domain "$domain"; then
        return 1
    fi
    
    log_debug "URL validation passed: $url"
    return 0
}

# Validate file exists and is readable
validate_file() {
    local file_path="$1"
    
    if [[ -z "$file_path" ]]; then
        log_error "File path cannot be empty"
        return 1
    fi
    
    if [[ ! -f "$file_path" ]]; then
        log_error "File not found: $file_path"
        return 1
    fi
    
    if [[ ! -r "$file_path" ]]; then
        log_error "File is not readable: $file_path"
        return 1
    fi
    
    log_debug "File validation passed: $file_path"
    return 0
}

# Sanitize filename (remove dangerous characters)
sanitize_filename() {
    local filename="$1"
    # Remove or replace dangerous characters
    echo "$filename" | sed 's/[^a-zA-Z0-9._-]/_/g' | sed 's/__*/_/g'
}

# Validate directory path
validate_directory() {
    local dir_path="$1"
    
    if [[ -z "$dir_path" ]]; then
        log_error "Directory path cannot be empty"
        return 1
    fi
    
    if [[ ! -d "$dir_path" ]]; then
        log_error "Directory not found: $dir_path"
        return 1
    fi
    
    if [[ ! -r "$dir_path" ]]; then
        log_error "Directory is not readable: $dir_path"
        return 1
    fi
    
    log_debug "Directory validation passed: $dir_path"
    return 0
}

# Check if command exists
validate_command() {
    local cmd="$1"
    
    if ! command -v "$cmd" &> /dev/null; then
        log_error "Command not found: $cmd"
        return 1
    fi
    
    log_debug "Command validation passed: $cmd"
    return 0
}


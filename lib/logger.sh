#!/bin/bash

# HADES Logging Library
# Centralized logging functionality

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/hades-$(date +%Y%m%d).log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Log levels
LOG_DEBUG=0
LOG_INFO=1
LOG_WARNING=2
LOG_ERROR=3
LOG_LEVEL=${LOG_LEVEL:-$LOG_INFO}

# Source colors
source "${SCRIPT_DIR}/lib/colors.sh"

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    local level_name=""
    local color=""
    
    case $level in
        $LOG_DEBUG)
            level_name="DEBUG"
            color="${COLORS[DIM]}"
            ;;
        $LOG_INFO)
            level_name="INFO"
            color="${COLORS[INFO]}"
            ;;
        $LOG_WARNING)
            level_name="WARNING"
            color="${COLORS[WARNING]}"
            ;;
        $LOG_ERROR)
            level_name="ERROR"
            color="${COLORS[DANGER]}"
            ;;
    esac
    
    # Only log if level is appropriate
    if [ $level -ge $LOG_LEVEL ]; then
        # Console output
        echo -e "${color}[${level_name}]${RESET} ${message}" >&2
        # File output
        echo "[${timestamp}] [${level_name}] ${message}" >> "$LOG_FILE"
    fi
}

# Convenience functions
log_debug() {
    log $LOG_DEBUG "$@"
}

log_info() {
    log $LOG_INFO "$@"
}

log_warning() {
    log $LOG_WARNING "$@"
}

log_error() {
    log $LOG_ERROR "$@"
}

# Log command execution
log_command() {
    local cmd="$@"
    log_debug "Executing: $cmd"
    eval "$cmd" 2>&1 | while IFS= read -r line; do
        log_debug "$line"
    done
}


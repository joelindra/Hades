#!/bin/bash

# HADES Color Library
# Centralized color definitions for consistent UI across all modules

# Color palette - RGB colors for better compatibility
declare -A COLORS=(
    [PRIMARY]='\e[38;2;120;200;255m'    # Soft blue
    [ACCENT]='\e[38;2;255;125;175m'     # Soft pink
    [SUCCESS]='\e[38;2;125;255;175m'    # Soft green
    [WARNING]='\e[38;2;255;230;125m'    # Soft yellow
    [DANGER]='\e[38;2;255;125;125m'     # Soft red
    [MUTED]='\e[38;2;150;150;180m'      # Faded purple
    [BRIGHT]='\e[38;2;235;235;255m'     # Bright white
    [DIM]='\e[38;2;100;100;120m'        # Dim gray
    [INFO]='\e[38;2;100;200;255m'       # Info blue
)

# Text effects
BOLD='\e[1m'
ITALIC='\e[3m'
UNDERLINE='\e[4m'
RESET='\e[0m'

# Legacy color support (for backward compatibility)
MAGENTA='\033[1;35m'
NC='\033[0m'
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'

# Color functions for easier usage
color_primary() {
    echo -e "${COLORS[PRIMARY]}${1}${RESET}"
}

color_success() {
    echo -e "${COLORS[SUCCESS]}${1}${RESET}"
}

color_warning() {
    echo -e "${COLORS[WARNING]}${1}${RESET}"
}

color_danger() {
    echo -e "${COLORS[DANGER]}${1}${RESET}"
}

color_info() {
    echo -e "${COLORS[INFO]}${1}${RESET}"
}


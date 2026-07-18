#!/bin/bash

# HADES YAML Parser Library
# Simple YAML parser for bash (handles basic YAML structure)

# Parse YAML file and extract value
# Usage: yaml_get_value <yaml_file> <key_path>
# Example: yaml_get_value config.yaml "framework.version"
yaml_get_value() {
    local yaml_file="$1"
    local key_path="$2"
    
    if [[ ! -f "$yaml_file" ]]; then
        return 1
    fi
    
    # Convert key path to regex pattern
    # framework.version -> ^[[:space:]]*version:[[:space:]]*(.+)$
    local key=$(echo "$key_path" | sed 's/.*\.//')
    local parent=$(echo "$key_path" | sed 's/\.[^.]*$//')
    
    # If no parent, search for top-level key
    if [[ -z "$parent" ]]; then
        grep -E "^[[:space:]]*${key}:[[:space:]]*(.+)$" "$yaml_file" | \
            sed -E "s/^[[:space:]]*${key}:[[:space:]]*//" | \
            sed 's/^"//;s/"$//' | \
            tr -d '\n\r' | \
            head -1
    else
        # Find parent section and get value
        local in_section=false
        local indent_level=0
        
        while IFS= read -r line; do
            # Skip comments and empty lines
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line// }" ]] && continue
            
            # Check if we're entering the parent section
            if [[ "$line" =~ ^[[:space:]]*${parent}:[[:space:]]*$ ]]; then
                in_section=true
                indent_level=$(echo "$line" | sed 's/[^ ].*//' | wc -c)
                continue
            fi
            
            # Check if we're leaving the section (new section at same or less indent)
            if [[ "$in_section" == "true" ]]; then
                local current_indent=$(echo "$line" | sed 's/[^ ].*//' | wc -c)
                if [[ $current_indent -le $indent_level ]] && [[ ! "$line" =~ ^[[:space:]]*${key}:[[:space:]]* ]]; then
                    in_section=false
                    continue
                fi
                
                # Check if this is our target key
                if [[ "$line" =~ ^[[:space:]]*${key}:[[:space:]]*(.+)$ ]]; then
                    echo "$line" | sed -E "s/^[[:space:]]*${key}:[[:space:]]*//" | sed 's/^"//;s/"$//' | tr -d '\n\r'
                    return 0
                fi
            fi
        done < "$yaml_file"
    fi
    
    return 1
}

# Get all values from a section
# Usage: yaml_get_section <yaml_file> <section>
yaml_get_section() {
    local yaml_file="$1"
    local section="$2"
    local in_section=false
    local indent_level=0
    
    while IFS= read -r line; do
        # Skip comments
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Check if we're entering the section
        if [[ "$line" =~ ^[[:space:]]*${section}:[[:space:]]*$ ]]; then
            in_section=true
            indent_level=$(echo "$line" | sed 's/[^ ].*//' | wc -c)
            continue
        fi
        
        # Check if we're leaving the section
        if [[ "$in_section" == "true" ]]; then
            local current_indent=$(echo "$line" | sed 's/[^ ].*//' | wc -c)
            if [[ $current_indent -le $indent_level ]] && [[ ! "$line" =~ ^[[:space:]]*[a-zA-Z_]+:[[:space:]]* ]]; then
                break
            fi
            
            # Output lines in section
            if [[ "$line" =~ ^[[:space:]]*[a-zA-Z_]+:[[:space:]]* ]]; then
                echo "$line"
            fi
        fi
    done < "$yaml_file"
}

# Load YAML config into associative array
# Usage: yaml_load_config <yaml_file> <array_name>
yaml_load_config() {
    local yaml_file="$1"
    local array_name="$2"
    
    if [[ ! -f "$yaml_file" ]]; then
        return 1
    fi
    
    # Create array if it doesn't exist
    declare -gA "$array_name"
    
    local current_section=""
    local in_section=false
    local indent_level=0
    
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Check for section header
        if [[ "$line" =~ ^[[:space:]]*([a-zA-Z_]+):[[:space:]]*$ ]]; then
            current_section="${BASH_REMATCH[1]}"
            in_section=true
            indent_level=$(echo "$line" | sed 's/[^ ].*//' | wc -c)
            continue
        fi
        
        # Check for key-value pair
        if [[ "$line" =~ ^[[:space:]]*([a-zA-Z_]+):[[:space:]]*(.+)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"
            
            # Remove quotes and trim whitespace/newlines
            value=$(echo "$value" | sed 's/^"//;s/"$//' | tr -d '\n\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            
            # Build full key path
            local full_key="${current_section}.${key}"
            if [[ -z "$current_section" ]]; then
                full_key="$key"
            fi
            
            # Store in array (use printf to safely handle special characters)
            printf -v safe_value "%q" "$value"
            eval "${array_name}[\"${full_key}\"]=$safe_value"
        fi
    done < "$yaml_file"
    
    return 0
}

# Simple YAML value getter (more robust)
yaml_get() {
    local yaml_file="$1"
    local key_path="$2"
    
    # Try using yq if available (more reliable)
    if command -v yq &> /dev/null; then
        yq eval ".${key_path}" "$yaml_file" 2>/dev/null | sed 's/^"//;s/"$//' | tr -d '\n\r'
        return $?
    fi
    
    # Fallback to simple parser
    local result=$(yaml_get_value "$yaml_file" "$key_path")
    if [[ -n "$result" ]]; then
        echo "$result" | tr -d '\n\r'
        return 0
    fi
    return 1
}


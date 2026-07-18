#!/bin/bash

# Function to check internet connection
check_internet() {
    echo "Checking Internet Connection..."
    if ping -c 1 google.com &> /dev/null; then
        echo "Internet connection: ONLINE."
    else
        echo "Internet connection: OFFLINE. Please check your connection."
        exit 1
    fi
}

# Function to install required dependencies
install_requirements() {
    echo "Detecting Operating System..."

    case "$(uname)" in
        "Darwin")
            echo "macOS Detected. Installing macOS requirements..."
            # Assuming 'require/require-mac.sh' exists and is executable
            (cd require && bash require-mac.sh) || {
                echo "Error: Could not install macOS requirements."
                exit 1
            }
            ;;
        "Linux")
            echo "Linux Detected. Installing Linux requirements..."
            # Assuming 'require/require.sh' exists and is executable
            (cd require && bash require.sh) || {
                echo "Error: Could not install Linux requirements."
                exit 1
            }
            ;;
        *)
            echo "Unsupported Operating System. This script only supports macOS and Linux."
            exit 1
            ;;
    esac
}

# Main function
main() {
    clear
    echo "System Installation Assistant - Simplified Setup"

    check_internet
    echo "Internet check complete."

    install_requirements
    echo "Requirements installation complete."

    echo "Installation process finished."
}

# Start script
main

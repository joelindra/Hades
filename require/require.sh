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

# Check root privileges
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Error: This script must be run as root."
        exit 1
    fi
    figlet Root Privileges Verified...
    echo ""
}

# System update function
update_system() {
    echo "Updating system packages..."
    echo ""
    if apt update && apt upgrade -y; then
        echo "System updated successfully."
    else
        echo "Error: Failed to update system."
        exit 1
    fi
}

# Install base packages
install_base_packages() {
    echo "Installing Base Packages..."
    echo ""
    packages=(
        "figlet" "wafw00f" "git" "subjack" "seclists"
        "massdns" "ffuf" "nmap" "golang" "subfinder"
        "pip" "curl" "wget" "amass" "python3-pip" "bc" "dos2unix" "dirsearch"
    )

    for package in "${packages[@]}"; do
        echo -n "Installing ${package}... "
        if apt install -y "$package" &>/dev/null; then
            echo "Done."
        else
            echo "Failed."
        fi
    done
}

# Install pip packages
install_pip_packages() {
    echo "Installing Pip Packages..."
    echo "Installing Shodan, CORSScanner, Ghauri, XSStrike, and Dirsearch..."
    echo ""
    pip install shodan corscanner ghauri xsstrike dirsearch --break-system-packages
}

# Install Go tools
install_go_tools() {
    echo "Installing Go Tools..."
    echo ""
    go_tools=(
        "github.com/Emoe/kxss@latest"
        "github.com/kacakb/jsfinder@latest"
        "github.com/tomnomnom/unfurl@latest"
        "github.com/hahwul/dalfox/v2@latest"
        "github.com/tomnomnom/httprobe@latest"
        "github.com/tomnomnom/waybackurls@latest"
        "github.com/tomnomnom/assetfinder@latest"
        "github.com/tomnomnom/anew@latest"

        # Core ProjectDiscovery tools
        "github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest"
        "github.com/projectdiscovery/httpx/cmd/httpx@latest"
        "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    )

    for tool in "${go_tools[@]}"; do
        echo -n "Installing ${tool##*/}... "
        if go install "$tool" &>/dev/null; then
            echo "Done."
        else
            echo "Failed."
        fi
    done
}

# Install MassDNS Resolvers
install_massdns_resolvers() {
    echo "Installing MassDNS Resolvers..."
    echo ""
    cd /root || exit
    if wget https://raw.githubusercontent.com/blechschmidt/massdns/master/lists/resolvers.txt; then
        cp resolvers.txt /usr/share/seclists/
        rm -rf resolvers.txt
        echo "MassDNS Resolvers installed successfully."
    else
        echo "Error: Failed to install MassDNS Resolvers."
        exit 1
    fi
}

# Install GF
install_gf() {
    echo "Installing GF..."
    echo ""
    cd /root || exit
    git clone https://github.com/tomnomnom/gf.git
    mkdir -p /usr/local/go/{src,bin}
    cd gf && cp *.zsh /usr/local/go/src
    cd /root && git clone https://github.com/1ndianl33t/Gf-Patterns.git
    go install github.com/tomnomnom/gf@latest
    cp /root/go/bin/gf /usr/local/go/bin/
    echo "source /usr/local/go/src/gf-completion.zsh" >> ~/.zshrc
    source ~/.zshrc
    mkdir -p ~/.gf
    cp -r gf/examples ~/.gf
    cp Gf-Patterns/*.json ~/.gf
    echo "GF installed successfully."
}


# Copy tools to system path
copy_tools() {
    echo "Copying tools to system path..."
    echo ""
    cp /root/go/bin/* /usr/bin/
    # Check if hades directory exists before attempting to create symlink
    if [ -d "/root/hades" ] && [ -f "/root/hades/hades" ]; then
        echo '#!/bin/bash' | sudo tee /usr/bin/hades > /dev/null
        echo 'bash /root/hades/hades $1' | sudo tee -a /usr/bin/hades > /dev/null
        chmod +x /usr/bin/hades
        echo "All tools copied successfully."
    else
        echo "Warning: hades directory not found, skipping symlink creation."
        echo "Go tools copied successfully."
    fi
}

# Main function
main() {
    clear
    check_root
    update_system
    install_base_packages
    install_pip_packages
    install_go_tools
    install_massdns_resolvers
    install_gf
    copy_tools

    dos2unix ../function/dirsearchpatrol.sh
    dos2unix ../function/masssqlinject.sh

    echo "Installation Complete!"
}

# Start script execution
main

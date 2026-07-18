#!/bin/bash
# ============================================================================
# HADES Quick Setup Script
# Script for quick and easy setup of HADES Security Testing Framework
# ============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Banner
echo -e "${CYAN}"

# Function: Print step
print_step() {
    echo -e "\n${BLUE}${BOLD}[STEP $1/$2]${NC} ${CYAN}$3${NC}"
    echo "──────────────────────────────────────────────────────────────"
}

# Function: Print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function: Print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function: Print error
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function: Check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function: Check Python version
check_python() {
    print_step "1" "11" "Checking Python Installation"
    
    if ! command_exists python3; then
        print_error "Python3 not found!"
        echo -e "${YELLOW}Please install Python 3.12 or higher:${NC}"
        echo "  - Ubuntu/Debian: sudo apt install python3.12 python3.12-venv python3-pip"
        echo "  - macOS: brew install python@3.12"
        echo "  - Windows: Download from https://www.python.org/downloads/"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]); then
        print_error "Python 3.12+ required, found: $PYTHON_VERSION"
        exit 1
    fi
    
    print_success "Python $PYTHON_VERSION found"
    
    # Check pip
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    elif python3 -m pip --version >/dev/null 2>&1; then
        PIP_CMD="python3 -m pip"
    else
        print_error "pip not found! Installing pip..."
        python3 -m ensurepip --upgrade || {
            print_error "Failed to install pip. Please install manually."
            exit 1
        }
        PIP_CMD="python3 -m pip"
    fi
    
    print_success "pip found: $PIP_CMD"
}

# Function: Check and setup Docker
check_docker() {
    print_step "2" "11" "Checking Docker Installation"
    
    if ! command_exists docker; then
        print_warning "Docker not found!"
        echo -e "${YELLOW}Docker is required for AI Agent Mode.${NC}"
        read -p "Do you want to install Docker? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker
        else
            print_warning "Skipping Docker installation. AI Agent Mode will not work."
            SKIP_DOCKER=true
            return
        fi
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running!"
        echo -e "${YELLOW}Please start Docker:${NC}"
        
        # WSL Specific hint
        if grep -qE "(Microsoft|WSL)" /proc/version 2>/dev/null; then
            echo "  [WSL Detected] Try: sudo service docker start"
            echo "  Or ensure Docker Desktop integration is enabled for your WSL distro."
        fi

        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "  sudo systemctl start docker"
            echo "  sudo usermod -aG docker $USER"
            echo "  newgrp docker"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  Open Docker Desktop application"
        else
            echo "  Start Docker Desktop"
        fi
        
        read -p "Press Enter after starting Docker (or Ctrl+C to abort)..."
        
        if ! docker info >/dev/null 2>&1; then
            print_error "Docker daemon still not running. AI Agent mode will likely fail."
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
    
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    print_success "Docker $DOCKER_VERSION is running"
    
    # Check Docker permissions
    if ! docker ps >/dev/null 2>&1; then
        print_warning "Docker permission denied. Adding user to docker group..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo usermod -aG docker "$USER" 2>/dev/null || true
            print_warning "Please logout and login again, or run: newgrp docker"
        fi
    fi
}

# Function: Install Docker
install_docker() {
    print_step "2.1" "11" "Installing Docker"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Installing Docker on Linux..."
        sudo apt update
        sudo apt install -y docker.io
        
        # Check if systemctl is available, otherwise use service
        if command -v systemctl >/dev/null 2>&1 && systemctl >/dev/null 2>&1; then
            sudo systemctl enable docker --now
        else
            sudo service docker start || true
        fi
        
        sudo usermod -aG docker "$USER"
        print_success "Docker installed and attempted to start. Please logout/login or run: newgrp docker"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Please install Docker Desktop for macOS:"
        echo "  https://www.docker.com/products/docker-desktop"
        exit 1
    else
        echo "Please install Docker Desktop for your OS:"
        echo "  https://www.docker.com/products/docker-desktop"
        exit 1
    fi
}

# Function: Pull Docker image
pull_docker_image() {
    if [ "$SKIP_DOCKER" = true ]; then
        return
    fi
    
    print_step "3" "11" "Pulling Docker Image"
    
    DOCKER_IMAGE="ghcr.io/joelindra/hades-sandbox-now:v1.0"
    
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${DOCKER_IMAGE}$"; then
        print_success "Docker image already exists: $DOCKER_IMAGE"
    else
        echo "Pulling Docker image: $DOCKER_IMAGE"
        echo "This may take a few minutes..."
        if docker pull "$DOCKER_IMAGE"; then
            print_success "Docker image pulled successfully"
        else
            print_error "Failed to pull Docker image"
            print_warning "You can pull it manually later: docker pull $DOCKER_IMAGE"
        fi
    fi
}

# Function: Install Python dependencies
install_dependencies() {
    print_step "4" "11" "Installing Python Dependencies"
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    echo "Installing dependencies from requirements.txt..."
    echo "This may take a few minutes..."
    
    # Try different pip commands
    if $PIP_CMD install -r requirements.txt --break-system-packages 2>&1 | tee /tmp/hades_install.log; then
        print_success "Python dependencies installed"
    else
        # Try without --break-system-packages (for some systems)
        print_warning "Retrying without --break-system-packages flag..."
        if $PIP_CMD install -r requirements.txt 2>&1 | tee /tmp/hades_install.log; then
            print_success "Python dependencies installed"
        else
            print_error "Failed to install some dependencies"
            print_warning "Check /tmp/hades_install.log for details"
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
}

# Function: Install Playwright browsers
install_playwright() {
    print_step "5" "11" "Installing Playwright Browsers"
    
    if command_exists playwright; then
        echo "Installing Playwright browsers..."
        playwright install chromium 2>/dev/null || python3 -m playwright install chromium || true
        print_success "Playwright browsers installed"
    else
        print_warning "Playwright not found, skipping browser installation"
        print_warning "Browsers will be installed automatically on first use"
    fi
}

# Function: Check Node.js and npm
check_nodejs() {
    print_step "6" "11" "Checking Node.js and npm"
    
    if ! command_exists node; then
        print_warning "Node.js not found!"
        echo -e "${YELLOW}Node.js is required for Web Interface.${NC}"
        read -p "Do you want to install Node.js? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_nodejs
        else
            print_warning "Skipping Node.js installation. Web Interface will not work."
            SKIP_NODEJS=true
            return
        fi
    fi
    
    NODE_VERSION=$(node --version 2>/dev/null | sed 's/v//')
    print_success "Node.js $NODE_VERSION found"
    
    if ! command_exists npm; then
        print_error "npm not found!"
        echo -e "${YELLOW}npm should come with Node.js. Please reinstall Node.js.${NC}"
        SKIP_NODEJS=true
        return
    fi
    
    NPM_VERSION=$(npm --version 2>/dev/null)
    print_success "npm $NPM_VERSION found"
}

# Function: Install Node.js
install_nodejs() {
    print_step "6.1" "11" "Installing Node.js"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Installing Node.js on Linux..."
        if command_exists curl; then
            curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
            sudo apt-get install -y nodejs
        elif command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y nodejs npm
        else
            print_error "Cannot install Node.js automatically. Please install manually:"
            echo "  https://nodejs.org/"
            SKIP_NODEJS=true
            return
        fi
        print_success "Node.js installed"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command_exists brew; then
            brew install node
            print_success "Node.js installed"
        else
            print_error "Homebrew not found. Please install Node.js manually:"
            echo "  https://nodejs.org/"
            SKIP_NODEJS=true
            return
        fi
    else
        print_error "Please install Node.js manually:"
        echo "  https://nodejs.org/"
        SKIP_NODEJS=true
        return
    fi
}

# Function: Setup Web Interface
setup_web_interface() {
    print_step "8" "11" "Setting Up Web Interface"
    
    WEB_DIR="$SCRIPT_DIR/hades/web"
    
    if [ ! -d "$WEB_DIR" ]; then
        print_warning "Web directory not found: $WEB_DIR"
        print_warning "Skipping web interface setup"
        return
    fi
    
    if [ "$SKIP_NODEJS" = true ]; then
        print_warning "Skipping web interface setup (Node.js not available)"
        return
    fi
    
    # Install backend dependencies
    echo "Installing backend dependencies (fastapi, uvicorn)..."
    if $PIP_CMD install fastapi uvicorn --break-system-packages 2>/dev/null; then
        print_success "Backend dependencies installed"
    elif $PIP_CMD install fastapi uvicorn 2>/dev/null; then
        print_success "Backend dependencies installed"
    else
        print_warning "Failed to install some backend dependencies"
    fi
    
    # Install frontend dependencies
    FRONTEND_DIR="$SCRIPT_DIR/frontend"
    if [ -d "$FRONTEND_DIR" ] && [ -f "$FRONTEND_DIR/package.json" ]; then
        echo "Installing frontend dependencies..."
        cd "$FRONTEND_DIR"

        if npm install 2>&1 | tee /tmp/hades_npm_install.log; then
            print_success "Frontend dependencies installed"

            # Build frontend
            # This runs: cd frontend && npm run build
            echo "Building frontend..."
            echo "Running: cd $FRONTEND_DIR && npm run build"
            if npm run build 2>&1 | tee /tmp/hades_npm_build.log; then
                print_success "Frontend built successfully"
            else
                print_warning "Frontend build failed (check /tmp/hades_npm_build.log)"
                print_warning "You can build it manually later: cd $FRONTEND_DIR && npm run build"
            fi
        else
            print_warning "Failed to install frontend dependencies (check /tmp/hades_npm_install.log)"
            print_warning "You can install manually later: cd $FRONTEND_DIR && npm install"
        fi
        
        cd "$SCRIPT_DIR"
    else
        print_warning "Frontend directory or package.json not found"
        print_warning "Skipping frontend setup"
    fi
}

# Function: Setup environment variables
setup_environment() {
    print_step "7" "11" "Setting Up Environment Variables"
    
    # Check if .env file exists
    ENV_FILE="$SCRIPT_DIR/.env"
    ENV_EXAMPLE="$SCRIPT_DIR/.env.example"
    
    if [ -f "$ENV_FILE" ]; then
        print_success ".env file already exists"
        # Safely source .env file - only export valid KEY=VALUE pairs
        set +e  # Temporarily disable exit on error
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip empty lines and comments
            line_trimmed=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [[ -z "$line_trimmed" || "$line_trimmed" =~ ^# ]]; then
                continue
            fi
            # Only process lines with = sign (handle both KEY=VALUE and export KEY=VALUE)
            if [[ "$line_trimmed" =~ ^(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*= ]]; then
                # Remove 'export' keyword if present
                line_clean=$(echo "$line_trimmed" | sed 's/^export[[:space:]]*//')
                # Extract key and value
                if [[ "$line_clean" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                    key="${BASH_REMATCH[1]}"
                    value="${BASH_REMATCH[2]}"
                    # Remove quotes if present
                    value=$(echo "$value" | sed 's/^["'\'']//;s/["'\'']$//')
                    # Export the variable safely
                    export "$key=$value" 2>/dev/null || true
                fi
            fi
        done < "$ENV_FILE"
        set -e  # Re-enable exit on error
    else
        echo -e "${YELLOW}Setting up environment variables...${NC}"
        echo ""
        
        # LLM Provider
        echo "Select LLM Provider:"
        echo "  1) Gemini 2.5 Pro (Recommended)"
        echo "  2) OpenAI GPT-4"
        echo "  3) Anthropic Claude"
        echo "  4) Skip (set manually later)"
        read -p "Choice [1-4]: " LLM_CHOICE
        
        case $LLM_CHOICE in
            1)
                HADES_LLM="gemini/gemini-2.5-pro"
                echo ""
                echo -e "${YELLOW}Get your API key from: https://aistudio.google.com/apikey${NC}"
                read -p "Enter your Google AI API Key: " LLM_API_KEY
                ;;
            2)
                HADES_LLM="openai/gpt-4"
                echo ""
                echo -e "${YELLOW}Get your API key from: https://platform.openai.com/api-keys${NC}"
                read -p "Enter your OpenAI API Key: " LLM_API_KEY
                ;;
            3)
                HADES_LLM="anthropic/claude-3-5-sonnet-20241022"
                echo ""
                echo -e "${YELLOW}Get your API key from: https://console.anthropic.com/settings/keys${NC}"
                read -p "Enter your Anthropic API Key: " LLM_API_KEY
                ;;
            *)
                HADES_LLM=""
                LLM_API_KEY=""
                print_warning "Skipping LLM setup. Set manually:"
                echo "  export HADES_LLM='gemini/gemini-2.5-pro'"
                echo "  export LLM_API_KEY='your-api-key'"
                ;;
        esac
        
        # Create .env file
        if [ -n "$HADES_LLM" ] && [ -n "$LLM_API_KEY" ]; then
            cat > "$ENV_FILE" <<EOF
# HADES Environment Variables
HADES_LLM="$HADES_LLM"
LLM_API_KEY="$LLM_API_KEY"

# Optional: Docker image override
# HADES_IMAGE="ghcr.io/joelindra/hades-sandbox-now:latest"

# Optional: Runtime backend
# HADES_RUNTIME_BACKEND="docker"
EOF
            chmod 600 "$ENV_FILE"
            print_success ".env file created"
            # Safely source .env file - only export valid KEY=VALUE pairs
            set +e  # Temporarily disable exit on error
            while IFS= read -r line || [ -n "$line" ]; do
                # Skip empty lines and comments
                line_trimmed=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                if [[ -z "$line_trimmed" || "$line_trimmed" =~ ^# ]]; then
                    continue
                fi
                # Only process lines with = sign (handle both KEY=VALUE and export KEY=VALUE)
                if [[ "$line_trimmed" =~ ^(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*= ]]; then
                    # Remove 'export' keyword if present
                    line_clean=$(echo "$line_trimmed" | sed 's/^export[[:space:]]*//')
                    # Extract key and value
                    if [[ "$line_clean" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                        key="${BASH_REMATCH[1]}"
                        value="${BASH_REMATCH[2]}"
                        # Remove quotes if present
                        value=$(echo "$value" | sed 's/^["'\'']//;s/["'\'']$//')
                        # Export the variable safely
                        export "$key=$value" 2>/dev/null || true
                    fi
                fi
            done < "$ENV_FILE"
            set -e  # Re-enable exit on error
        else
            print_warning "No .env file created. Set environment variables manually."
        fi
    fi
    
    # Show current environment
    echo ""
    echo "Current environment:"
    if [ -n "$HADES_LLM" ]; then
        echo -e "  ${GREEN}HADES_LLM${NC} = $HADES_LLM"
    else
        echo -e "  ${YELLOW}HADES_LLM${NC} = (not set)"
    fi
    if [ -n "$LLM_API_KEY" ]; then
        echo -e "  ${GREEN}LLM_API_KEY${NC} = ${LLM_API_KEY:0:10}... (hidden)"
    else
        echo -e "  ${YELLOW}LLM_API_KEY${NC} = (not set)"
    fi
}

# Function: Initialize database
init_database() {
    print_step "9" "11" "Initializing SQLite Database"
    
    # Create config directory
    mkdir -p config/profile_images
    
    # Initialize database using Python
    echo "Creating database schema..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
from hades.web.database import init_database, migrate_from_json
try:
    init_database()
    migrated_users, migrated_tokens = migrate_from_json()
    if migrated_users > 0 or migrated_tokens > 0:
        print(f'Migrated {migrated_users} users and {migrated_tokens} tokens from JSON')
    print('Database initialized successfully')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" 2>&1; then
        print_success "Database initialized successfully"
        if [ -f "config/hades.db" ]; then
            print_success "Database file created: config/hades.db"
        fi
    else
        print_error "Failed to initialize database"
        return 1
    fi
}

# Function: Verify setup
verify_setup() {
    print_step "11" "11" "Verifying Setup"
    
    local errors=0
    
    # Test Python import
    echo "Testing Python imports..."
    if python3 -c "import rich, yaml, fastapi, uvicorn, pydantic, docker, sqlite3" 2>/dev/null; then
        print_success "Core Python packages imported successfully"
    else
        print_error "Some Python packages failed to import"
        errors=$((errors + 1))
    fi
    
    # Test database
    if [ -f "config/hades.db" ]; then
        print_success "Database file exists"
    else
        print_warning "Database file not found (will be created on first run)"
    fi
    
    # Test Docker
    if [ "$SKIP_DOCKER" != true ]; then
        if docker info >/dev/null 2>&1; then
            print_success "Docker is running"
            
            if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "hades-sandbox-now"; then
                print_success "Docker image is available"
            else
                print_warning "Docker image not found (will be pulled on first use)"
            fi
        else
            print_error "Docker is not running"
            errors=$((errors + 1))
        fi
    else
        print_warning "Docker check skipped"
    fi
    
    # Test HADES script
    if [ -f "hades.py" ]; then
        if python3 hades.py --help >/dev/null 2>&1; then
            print_success "HADES script is working"
        else
            print_warning "HADES script may have issues (check manually)"
        fi
    fi
    
    # Test Web Interface
    if [ "$SKIP_NODEJS" != true ]; then
        if command_exists node && command_exists npm; then
            print_success "Node.js and npm are available"

            FRONTEND_DIR="$SCRIPT_DIR/frontend"
            if [ -d "$FRONTEND_DIR" ] && [ -f "$FRONTEND_DIR/package.json" ]; then
                if [ -d "$FRONTEND_DIR/dist" ] || [ -d "$FRONTEND_DIR/build" ]; then
                    print_success "Web interface frontend is built"
                else
                    print_warning "Web interface frontend not built (run setup again or build manually)"
                fi
            fi
        fi
    else
        print_warning "Web interface check skipped (Node.js not available)"
    fi
    
    if [ $errors -eq 0 ]; then
        print_success "Setup verification completed"
        return 0
    else
        print_warning "Setup verification found $errors issue(s)"
        return 1
    fi
}

# Function: Setup Hades command link
setup_hades_link() {
    print_step "10" "11" "Setting up Hades command"
    
    if [ -f "$SCRIPT_DIR/hades.py" ]; then
        chmod +x "$SCRIPT_DIR/hades.py"
        ln -sf hades.py hades
        print_success "Created executable 'hades' link"
    else
        print_error "hades.py not found, skipping link creation"
    fi
}
print_completion() {
    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║              ✅  SETUP COMPLETED SUCCESSFULLY!  ✅           ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    echo -e "${CYAN}${BOLD}Next Steps:${NC}\n"
    
    echo -e "${YELLOW}1. Load environment variables:${NC}"
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo "   source $SCRIPT_DIR/.env"
    else
        echo "   export HADES_LLM='gemini/gemini-2.5-pro'"
        echo "   export LLM_API_KEY='your-api-key'"
    fi
    
    echo ""
    echo -e "${YELLOW}2. Run HADES:${NC}"
    echo "   # AI Agent Mode"
    echo "   ./hades --target https://example.com"
    echo ""
    echo "   # Shell Module Mode"
    echo "   ./hades --mass-recon"
    echo ""
    echo "   # Web Interface"
    echo "   ./hades --web"
    echo "   Then open: http://localhost:9656"
    echo ""
    echo "   # Help"
    echo "   ./hades --help"
    
    echo ""
    echo -e "${YELLOW}3. Documentation:${NC}"
    echo "   - README.md - Main documentation"
    echo "   - DOCKER_SETUP.md - Docker setup guide"
    
    echo ""
    echo -e "${GREEN}Happy Hacking! 🎉${NC}\n"
}

# Main execution
main() {
    check_python
    check_docker
    pull_docker_image
    install_dependencies
    install_playwright
    check_nodejs
    setup_environment
    setup_web_interface
    init_database
    setup_hades_link
    verify_setup
    
    print_completion
}

# Run main
main


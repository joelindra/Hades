#!/bin/bash
set -e

# Package version and info
VERSION="1.0.0-vpro"
PACKAGE_NAME="hades"
MAINTAINER="Joel Indra | Anonre <anonre@hades.com>"
ARCHITECTURE="all"
SECTION="security"
PRIORITY="optional"
DESCRIPTION="HADES Modern Pro Edition - Advanced Security Testing Framework (vPro-1.0.0)"
OUTPUT_DIR="deb_output"

# Build directory in WSL home to avoid Windows mount permission issues
BUILD_ROOT="/tmp/hades_build"
PKG_DIR="${BUILD_ROOT}/${PACKAGE_NAME}_${VERSION}_${ARCHITECTURE}"

echo "[*] Cleaning previous build..."
rm -rf "$BUILD_ROOT" 2>/dev/null || true
rm -rf "$OUTPUT_DIR"/* 2>/dev/null || true
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/opt/hades"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$OUTPUT_DIR"

echo "[*] Verifying frontend build..."
if [ ! -d "frontend/dist" ]; then
    echo "[!] Frontend build not found! Attempting to build..."
    (cd frontend && npm install && npm run build)
fi

echo "[*] Copying core project files (including built frontend)..."
# Exclude source dependencies and junk, but KEEP built 'dist'
rsync -av --progress ./ "$PKG_DIR/opt/hades/" \
    --exclude "node_modules" \
    --exclude ".git" \
    --exclude ".github" \
    --exclude ".gemini" \
    --exclude ".env" \
    --exclude ".env.example" \
    --exclude "__pycache__" \
    --exclude "*.pyc" \
    --exclude "agent_runs" \
    --exclude "build_deb_pkg" \
    --exclude "build_deb.sh" \
    --exclude "build_deb_vpro.sh" \
    --exclude "frontend/src" \
    --exclude "frontend/public" \
    --exclude "*.config.*" \
    --exclude "tsconfig.*" \
    --exclude "config/telegram_*.txt" \
    --exclude "config/*.db" \
    --exclude "deb_output" \
    --exclude "reports/*"

echo "[*] Creating entry point wrapper..."
cat <<EOF > "$PKG_DIR/usr/bin/hades"
#!/bin/bash
# Wrapper for HADES Security Framework (System)
export PYTHONIOENCODING=utf-8
# Use the virtual environment's python
/opt/hades/venv/bin/python3 /opt/hades/hades.py "\$@"
EOF

echo "[*] Creating control file..."
cat <<EOF > "$PKG_DIR/DEBIAN/control"
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: ${SECTION}
Priority: ${PRIORITY}
Architecture: ${ARCHITECTURE}
Maintainer: ${MAINTAINER}
Depends: python3, python3-venv, python3-pip, bash, rsync, curl, docker.io, figlet, nmap, git
Description: ${DESCRIPTION}
 Hades is a high-performance security framework that includes pre-pulled 
 sandboxed execution environments for safe scanning.
EOF

echo "[*] Creating postinst script..."
cat <<'EOF' > "$PKG_DIR/DEBIAN/postinst"
#!/bin/bash
set -e
cd /opt/hades

echo "[*] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[*] Installing Python dependencies in venv..."
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir

# Pull the core Docker image with verbose output showing layers
HADES_IMAGE="ghcr.io/joelindra/hades-sandbox-now:v1.0"
HADES_REGISTRY="ghcr.io (GitHub Container Registry)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           PRE-CACHING HADES SANDBOX ENVIRONMENT             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  📦 Image Name : ${HADES_IMAGE}"
echo "  🌐 Registry   : ${HADES_REGISTRY}"
echo "  📂 Saved to   : /var/lib/docker/image/ (Docker local cache)"
echo ""
echo "  ⏳ Downloading layers... (each line = 1 Docker layer)"
echo "──────────────────────────────────────────────────────────────"

if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        echo "  🚀 Starting high-speed download from GitHub Registry..."
        echo "──────────────────────────────────────────────────────────────"
        echo ""
        
        # Run docker pull directly to preserve the native progress bars and percentages
        # This is much clearer for the user as they see real-time bars
        docker pull "${HADES_IMAGE}"
        PULL_EXIT_CODE=$?
        
        echo ""
        echo "──────────────────────────────────────────────────────────────"
        if [ "$PULL_EXIT_CODE" -eq 0 ]; then
            echo "  ✅ Image pulled successfully!"
            echo "  📦 Sandbox environment is ready for use."
        else
            echo "  ❌ ERROR: Pull failed (Status: $PULL_EXIT_CODE)"
            echo "  💡 Note: Ensure your internet connection is stable."
            echo "  ⚠️  The sandbox will try to pull again on first run."
        fi
    else
        echo "  ⚠️  Docker daemon not running. Image will be pulled on first run."
    fi
else
    echo "  ⚠️  Docker not found! Image will be pulled when Docker is installed."
fi
echo ""

# Setup default .env from example if not present
if [ ! -f "/opt/hades/.env" ]; then
    echo "[*] Creating default .env configuration..."
    # Copy from the package location (we need to make sure .env.example was copied or we use a heredoc)
    cat <<EOT > /opt/hades/.env
# HADES CONFIGURATION
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOT
    chmod 600 /opt/hades/.env
fi

echo "[*] HADES installed successfully!"
echo "    Usage: hades --help"
exit 0
EOF

echo "[*] Creating prerm script..."
cat <<EOF > "$PKG_DIR/DEBIAN/prerm"
#!/bin/bash
set -e
exit 0
EOF

echo "[*] Creating postrm script (Deep Purge)..."
cat <<EOF > "$PKG_DIR/DEBIAN/postrm"
#!/bin/bash
set -e
if [ "\$1" = "purge" ]; then
    echo "[*] Purging all HADES data from /opt/hades..."
    rm -rf /opt/hades
fi
exit 0
EOF

echo "[*] Fixing permissions for security hardening..."
# Base: 755 for dirs, 644 for files
find "$PKG_DIR" -type d -exec chmod 755 {} \;
find "$PKG_DIR" -type f -exec chmod 644 {} \;

# Execute permissions for scripts and binaries
chmod 755 "$PKG_DIR/DEBIAN/postinst"
chmod 755 "$PKG_DIR/DEBIAN/prerm"
chmod 755 "$PKG_DIR/DEBIAN/postrm"
chmod 755 "$PKG_DIR/usr/bin/hades"

# Ensure all .sh files in opt/hades are executable
find "$PKG_DIR/opt/hades" -name "*.sh" -exec chmod 755 {} \;
# hades.py also needs to be executable if called directly, but wrapper uses python path. 
# Keep it 755 just in case.
chmod 755 "$PKG_DIR/opt/hades/hades.py"

echo "[*] Generating MD5 sums..."
(cd "$PKG_DIR" && find . -type f ! -regex '.*DEBIAN/.*' -printf '%P\0' | xargs -0 md5sum > DEBIAN/md5sums)
chmod 644 "$PKG_DIR/DEBIAN/md5sums"

echo "[*] Building .deb package..."
dpkg-deb --build "$PKG_DIR"

echo "[*] Copying built package to output directory..."
cp "${BUILD_ROOT}/${PACKAGE_NAME}_${VERSION}_${ARCHITECTURE}.deb" "./${OUTPUT_DIR}/hades-v1.0.deb"

echo "[*] Package built successfully: ./${OUTPUT_DIR}/hades-v1.0.deb"

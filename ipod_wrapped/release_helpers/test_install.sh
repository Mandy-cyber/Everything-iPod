#!/usr/bin/env bash
set -e

# =====================================================
# Test iPod Wrapped Installation in Docker
# =====================================================
# Tests the installer in a fresh environment
# =====================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISTRO="${1:-ubuntu:24.04}"

echo "Testing iPod Wrapped installation in fresh $DISTRO environment..."
echo ""

# check for tarball
if [ ! -f "$SCRIPT_DIR/ipod-wrapped-linux-x86_64.tar.gz" ]; then
    echo "Error: Release tarball not found!"
    echo "Please run ./package_release.sh first"
    exit 1
fi

# create dockerfile
cat > /tmp/ipod-wrapped-test.dockerfile << 'EOF'
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# install basic tools
RUN if command -v apt-get >/dev/null 2>&1; then \
        apt-get update && apt-get install -y sudo curl tar; \
    elif command -v dnf >/dev/null 2>&1; then \
        dnf install -y sudo curl tar; \
    elif command -v pacman >/dev/null 2>&1; then \
        pacman -Sy --noconfirm sudo curl tar; \
    elif command -v zypper >/dev/null 2>&1; then \
        zypper install -y sudo curl tar; \
    fi

# create test user with sudo
RUN useradd -m -s /bin/bash testuser && \
    echo "testuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER testuser
WORKDIR /home/testuser

# copy release tarball
COPY ipod-wrapped-linux-x86_64.tar.gz /home/testuser/

# extract
RUN tar -xzf ipod-wrapped-linux-x86_64.tar.gz

WORKDIR /home/testuser/ipod-wrapped-linux-x86_64

CMD ["/bin/bash"]
EOF

# build docker image
echo "Building test Docker image..."
docker build \
    --build-arg BASE_IMAGE="$DISTRO" \
    -f /tmp/ipod-wrapped-test.dockerfile \
    -t ipod-wrapped-test \
    "$SCRIPT_DIR" \
    2>&1 | grep -v "^#" || true

echo ""
echo "=========================================="
echo "Docker container ready!"
echo "=========================================="
echo ""
echo "To test the installation:"
echo ""
echo "  1. Run: docker run -it ipod-wrapped-test"
echo "  2. Inside container, run: ./install.sh"
echo "  3. Follow the installer prompts"
echo ""
echo "Note: The AppImage won't run in Docker (no display),"
echo "but you can verify the installation process works."
echo ""
echo "To test on different distros:"
echo "  ./test_install.sh ubuntu:22.04"
echo "  ./test_install.sh ubuntu:24.04"
echo "  ./test_install.sh fedora:39"
echo "  ./test_install.sh fedora:40"
echo "  ./test_install.sh archlinux:latest"
echo ""

#!/bin/bash
# Comprehensive setup script for iLOrest tool in the Ansible toolkit
# This ensures ilorest is available for the playbooks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   iLOrest Setup for Ansible Toolkit      ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install via package manager
install_via_package_manager() {
    echo -e "${YELLOW}Installing ilorest via system package manager...${NC}"
    
    if command_exists apt; then
        echo "Detected APT package manager (Debian/Ubuntu)"
        sudo apt update -qq
        sudo apt install -y ilorest python3-ilorest
        return 0
    elif command_exists yum; then
        echo "Detected YUM package manager (RHEL/CentOS)"
        sudo yum install -y python3-ilorest
        return 0
    elif command_exists dnf; then
        echo "Detected DNF package manager (Fedora/RHEL 8+)"
        sudo dnf install -y python3-ilorest
        return 0
    elif command_exists zypper; then
        echo "Detected Zypper package manager (SUSE)"
        sudo zypper install -y python3-ilorest
        return 0
    else
        echo -e "${RED}No supported package manager found${NC}"
        return 1
    fi
}

# Check if ilorest is already available
if command_exists ilorest; then
    echo -e "${GREEN}✓ ilorest is already available on the system!${NC}"
    ILOREST_PATH=$(which ilorest)
    echo "  Location: $ILOREST_PATH"
    
    # Test basic functionality
    echo -e "${YELLOW}Testing ilorest functionality...${NC}"
    if ilorest --help >/dev/null 2>&1; then
        echo -e "${GREEN}✓ ilorest is working correctly${NC}"
        echo ""
        echo -e "${GREEN}Setup complete! ilorest is ready for use.${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ ilorest found but may have issues. Attempting reinstall...${NC}"
    fi
fi

# Try to install via package manager
if install_via_package_manager; then
    echo ""
    if command_exists ilorest; then
        echo -e "${GREEN}✓ ilorest successfully installed!${NC}"
        ILOREST_PATH=$(which ilorest)
        echo "  Location: $ILOREST_PATH"
        
        # Test functionality
        echo -e "${YELLOW}Testing ilorest functionality...${NC}"
        if ilorest --help >/dev/null 2>&1; then
            echo -e "${GREEN}✓ ilorest is working correctly${NC}"
        else
            echo -e "${YELLOW}⚠ ilorest installed but may have some warnings (this is usually normal)${NC}"
        fi
        
        echo ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}         Setup Successful!                 ${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo ""
        echo "ilorest is now available for the Ansible toolkit."
        echo "The playbooks will automatically use the system installation."
        echo ""
        echo "To test ilorest manually, run:"
        echo "  ilorest --help"
        echo ""
        exit 0
    else
        echo -e "${RED}✗ Package installation completed but ilorest command not found${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Failed to install ilorest via package manager${NC}"
    echo ""
    echo -e "${YELLOW}Manual installation required:${NC}"
    echo "1. Download ilorest from: https://www.hpe.com/us/en/servers/restful-api.html"
    echo "2. Install the appropriate package for your OS"
    echo "3. Run this script again to verify the installation"
    echo ""
    exit 1
fi

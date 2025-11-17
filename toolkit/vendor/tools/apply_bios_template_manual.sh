#!/bin/bash

# Manual BIOS Template Application Script for G6 Servers
# Usage: ./apply_bios_template_manual.sh <server_ip> <username> <password>

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <server_ip> <username> <password>"
    echo "Example: $0 192.168.1.100 admin password123"
    exit 1
fi

SERVER_IP="$1"
USERNAME="$2"
PASSWORD="$3"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ILOREST_WRAPPER="$SCRIPT_DIR/ilorest_wrapper.sh"
BIOS_TEMPLATE="/mnt/AnsibleMediakit/HA/BiosTemplates/HAG6/HA_G6_Intel_HA810_HA820_G6.json"

# Check if BIOS template exists
if [ ! -f "$BIOS_TEMPLATE" ]; then
    echo "❌ Error: BIOS template not found at $BIOS_TEMPLATE"
    echo "Please ensure AnsibleMediakit is mounted and template file exists."
    exit 1
fi

# Check if ilorest wrapper exists
if [ ! -f "$ILOREST_WRAPPER" ]; then
    echo "❌ Error: iLOrest wrapper not found at $ILOREST_WRAPPER"
    exit 1
fi

echo "📋 Starting BIOS Template Application"
echo "=================================="
echo "Server IP: $SERVER_IP"
echo "Username: $USERNAME"
echo "Template: $BIOS_TEMPLATE"
echo ""

# Step 1: Login to iLO
echo "🔐 Step 1: Logging into iLO..."
if ! "$ILOREST_WRAPPER" login "$SERVER_IP" -u "$USERNAME" -p "$PASSWORD"; then
    echo "❌ Failed to login to iLO server $SERVER_IP"
    echo "Please check:"
    echo "- Server IP address is correct and reachable"
    echo "- Username and password are correct"
    echo "- iLO service is running on the target server"
    exit 1
fi
echo "✅ Successfully logged into iLO"
echo ""

# Step 2: Load BIOS template
echo "📁 Step 2: Loading BIOS template..."
if ! "$ILOREST_WRAPPER" load -f "$BIOS_TEMPLATE"; then
    echo "❌ Failed to load BIOS template"
    echo "Please check:"
    echo "- Template file format is correct"
    echo "- Template is compatible with target server"
    "$ILOREST_WRAPPER" logout
    exit 1
fi
echo "✅ BIOS template loaded successfully"
echo ""

# Step 3: Show pending changes
echo "📋 Step 3: Showing pending BIOS changes..."
"$ILOREST_WRAPPER" pending
echo ""

# Step 4: Commit changes
echo "💾 Step 4: Committing BIOS changes..."
if ! "$ILOREST_WRAPPER" commit; then
    echo "❌ Failed to commit BIOS changes"
    "$ILOREST_WRAPPER" logout
    exit 1
fi
echo "✅ BIOS changes committed successfully"
echo ""

# Step 5: Logout
echo "🚪 Step 5: Logging out from iLO..."
"$ILOREST_WRAPPER" logout
echo "✅ Logged out successfully"
echo ""

echo "🎉 BIOS Template Application Completed!"
echo "======================================"
echo "✅ G6 BIOS template has been successfully applied to server $SERVER_IP"
echo "✅ BIOS configuration changes have been committed"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "   1. The server may need to be rebooted for all BIOS changes to take effect"
echo "   2. You can now proceed with firmware updates using SPV/SUM tools"
echo "   3. Verify BIOS settings after reboot if needed"
echo ""
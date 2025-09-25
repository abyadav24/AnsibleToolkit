#!/bin/bash

# Firmware Management Validation Script
echo "=== Supermicro Firmware Management Validation ==="
echo

# Check if required files exist
echo "Checking required files..."

FILES=(
    "version_config.yaml"
    "config/servers.csv"
    "firmware_management_master.yaml"
    "Firmware-X13 CopyFIle .yaml"
    "firmware_update_single_server.yaml"
    "check_firmware_versions.yaml"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file missing"
    fi
done

echo

# Check mounted directory
MOUNTED_DIR="/SMCI/Mounted/MediaKit"
echo "Checking mounted directory..."
if [ -d "$MOUNTED_DIR" ]; then
    echo "✓ Mounted directory exists: $MOUNTED_DIR"
    echo "  Contents:"
    ls -la "$MOUNTED_DIR" | head -10
else
    echo "✗ Mounted directory missing: $MOUNTED_DIR"
    echo "  Please ensure the directory is mounted with firmware files"
fi

echo

# Check SAA tool
SAA_TOOL="/home/ubuntu/smci/saa_1.3.0_Linux_x86_64/saa"
echo "Checking SAA tool..."
if [ -f "$SAA_TOOL" ]; then
    echo "✓ SAA tool exists: $SAA_TOOL"
    if [ -x "$SAA_TOOL" ]; then
        echo "✓ SAA tool is executable"
    else
        echo "⚠ SAA tool needs execute permission"
        echo "  Run: chmod +x $SAA_TOOL"
    fi
else
    echo "✗ SAA tool missing: $SAA_TOOL"
fi

echo

echo "Validating servers.csv format..."
if [ -f "config/servers.csv" ]; then
    echo "✓ servers.csv exists"
    echo "  Sample content:"
    head -3 config/servers.csv
    
    # Check if it has the required columns
    HEADER=$(head -1 config/servers.csv)
    if [[ "$HEADER" == *"hostname"* ]] && [[ "$HEADER" == *"ipv4"* ]] && [[ "$HEADER" == *"vendor"* ]] && [[ "$HEADER" == *"model"* ]]; then
        echo "✓ Required columns present in servers.csv"
    else
        echo "⚠ servers.csv may be missing required columns (hostname, ipv4, vendor, model)"
    fi
else
    echo "✗ servers.csv missing"
fi

echo

# Check ansible installation
echo "Checking Ansible installation..."
if command -v ansible-playbook &> /dev/null; then
    echo "✓ Ansible is installed"
    ansible-playbook --version | head -1
else
    echo "✗ Ansible not found"
    echo "  Install with: sudo apt update && sudo apt install ansible"
fi

echo

# Test connectivity to first server (if exists)
echo "Testing server connectivity..."
if [ -f "config/servers.csv" ] && [ $(wc -l < config/servers.csv) -gt 1 ]; then
    FIRST_SERVER=$(sed -n '2p' config/servers.csv | cut -d',' -f2)
    if [ ! -z "$FIRST_SERVER" ]; then
        echo "Testing connectivity to first server: $FIRST_SERVER"
        if ping -c 1 -W 3 "$FIRST_SERVER" &> /dev/null; then
            echo "✓ Server $FIRST_SERVER is reachable"
        else
            echo "⚠ Server $FIRST_SERVER is not reachable (network issue or server down)"
        fi
    fi
else
    echo "⚠ No servers found in servers.csv for connectivity test"
fi

echo

# Summary
echo "=== Validation Summary ==="
echo "If all checks show ✓, you can run the firmware management playbooks."
echo "Address any ✗ or ⚠ issues before proceeding."
echo
echo "To run:"
echo "  Full process:     ansible-playbook multi_vendor_firmware_master.yaml -e operation=full"
echo "  Check only:       ansible-playbook multi_vendor_firmware_master.yaml -e operation=check"
echo "  Servers only:     ansible-playbook multi_vendor_firmware_master.yaml -e operation=servers_only"
echo "  IO cards only:    ansible-playbook multi_vendor_firmware_master.yaml -e operation=io_only"
echo "  Legacy (direct):  ansible-playbook \"Firmware-X13 CopyFIle .yaml\""

#!/bin/bash
# Comprehensive Ansible Toolkit Setup Script
# This script handles all setup tasks for new deployments

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENDOR_PYTHON_LIBS="$SCRIPT_DIR/vendor/python-libs"
ILOREST_TOOLS_DIR="$SCRIPT_DIR/vendor/tools"

echo "=========================================="
echo "  Ansible Toolkit Setup & Verification   "
echo "=========================================="

# 0. Set permissions for vendor tools
echo "Step 0: Setting permissions for vendor utilities..."
echo "Configuring vendor tools: rpm, gawk, strings from local-bin..."

VENDOR_BIN_DIR="$SCRIPT_DIR/vendor/tools/local-bin"

if [ -d "$VENDOR_BIN_DIR" ]; then
    # Set execute permissions for all tools in local-bin
    chmod +x "$VENDOR_BIN_DIR"/* 2>/dev/null || true
    
    # Verify each critical tool
    for tool in rpm gawk strings; do
        if [ -f "$VENDOR_BIN_DIR/$tool" ]; then
            chmod +x "$VENDOR_BIN_DIR/$tool"
            if [ -x "$VENDOR_BIN_DIR/$tool" ]; then
                echo " $tool is executable in vendor/tools/local-bin/"
                
                # Test if the tool can actually run (check for missing libraries)
                if "$VENDOR_BIN_DIR/$tool" --version >/dev/null 2>&1; then
                    echo " $tool is functional"
                else
                    echo "$tool has execute permissions but may have missing library dependencies"
                    echo "  If SUM service fails, you may need to install system packages for dependencies"
                fi
            else
                echo "Failed to set execute permissions for $tool"
            fi
        else
            echo " Warning: $tool not found in vendor/tools/local-bin/"
        fi
    done
    
    # Add vendor bin directory to PATH for this session
    export PATH="$VENDOR_BIN_DIR:$PATH"
    echo " Added vendor/tools/local-bin to PATH"
else
    echo " Error: vendor/tools/local-bin directory not found"
    echo "Please ensure vendor tools are properly placed in the toolkit"
fi

# Verify dependencies are now available
echo "Verifying vendor utilities availability..."
for cmd in rpm gawk strings; do
    if command -v "$cmd" >/dev/null 2>&1; then
        CMD_PATH=$(command -v "$cmd")
        echo " $cmd is available at $CMD_PATH"
    else
        echo " $cmd is not available in PATH"
    fi
done

# 1. Fix execute permissions for vendor tools
echo "Step 1: Setting execute permissions for vendor tools..."
chmod +x "$SCRIPT_DIR/vendor/tools/ilorest_wrapper.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/vendor/tools/ilorest/usr/bin/ilorest" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/vendor/tools/saa" 2>/dev/null || true

# Fix playbooks directory permissions (required for ansible.cfg to be loaded)
echo "Fixing playbooks directory permissions for ansible.cfg..."
chmod 755 "$SCRIPT_DIR/playbooks" 2>/dev/null || true
chmod 644 "$SCRIPT_DIR/playbooks/ansible.cfg" 2>/dev/null || true
echo " Playbooks directory permissions fixed (ansible.cfg will be loaded)"

# Fix permissions for any SUM (Smart Update Manager) tools
if [ -d "$SCRIPT_DIR/vendor/tools" ]; then
    echo "Checking for SUM and other vendor tools..."
    
    # Find and fix permissions for sum_service_x64 and similar tools
    find "$SCRIPT_DIR/vendor/tools" -type f \( -name "*sum*" -o -name "*service*" -o -name "*.x64" -o -name "*.exe" -o -name "*.bin" \) -exec chmod +x {} \; 2>/dev/null || true
    
    # Find and fix permissions for any executables in bin directories
    find "$SCRIPT_DIR/vendor/tools" -type f -path "*/bin/*" -exec chmod +x {} \; 2>/dev/null || true
    
    # Find any files that should be executable based on common patterns
    find "$SCRIPT_DIR/vendor/tools" -type f \( -name "*.sh" -o -name "*wrapper*" -o -name "*tool*" \) -exec chmod +x {} \; 2>/dev/null || true
    
    echo " Execute permissions set for all vendor tools"
fi

# Verify critical permissions were actually set
if [ -x "$SCRIPT_DIR/vendor/tools/ilorest_wrapper.sh" ]; then
    echo " ilorest_wrapper.sh is executable"
else
    echo " Warning: ilorest_wrapper.sh permissions could not be set"
    # Try alternative approach
    sudo chmod +x "$SCRIPT_DIR/vendor/tools/ilorest_wrapper.sh" 2>/dev/null || echo "✗ Failed to set execute permissions"
fi

if [ -x "$SCRIPT_DIR/vendor/tools/ilorest/usr/bin/ilorest" ]; then
    echo " ilorest binary is executable"  
else
    echo " Warning: ilorest binary permissions could not be set"
    sudo chmod +x "$SCRIPT_DIR/vendor/tools/ilorest/usr/bin/ilorest" 2>/dev/null || echo "✗ Failed to set execute permissions"
fi

# 2. Clean up broken symlinks (if any exist)
echo "Step 2: Cleaning up broken symlinks..."
BROKEN_SYMLINKS=$(find "$SCRIPT_DIR/vendor/tools/ilorest/" -type l -exec test ! -e {} \; -print 2>/dev/null || true)
if [ -n "$BROKEN_SYMLINKS" ]; then
    echo "Removing broken symlinks:"
    echo "$BROKEN_SYMLINKS" | while read -r symlink; do
        rm -f "$symlink" && echo "  - Removed: $symlink"
    done
    echo " Broken symlinks cleaned up"
else
    echo " No broken symlinks found"
fi

# 3. Verify Python dependencies
echo "Step 3: Verifying Python dependencies..."
if [ ! -d "$VENDOR_PYTHON_LIBS" ]; then
    echo "✗ Error: $VENDOR_PYTHON_LIBS directory not found"
    exit 1
fi

REQUIRED_MODULES=("jsonpatch" "jsonpointer" "prettytable" "requests" "urllib3" "jsonpath_rw" "ply" "pyaes" "jsondiff" "tabulate")
MISSING_MODULES=()

for module in "${REQUIRED_MODULES[@]}"; do
    if [ ! -f "$VENDOR_PYTHON_LIBS/$module.py" ] && [ ! -d "$VENDOR_PYTHON_LIBS/$module" ]; then
        MISSING_MODULES+=("$module")
    fi
done

if [ ${#MISSING_MODULES[@]} -eq 0 ]; then
    echo " All required Python modules are present"
else
    echo " Missing modules: ${MISSING_MODULES[*]}"
    echo "Please ensure these modules are included in vendor/python-libs directory"
    exit 1
fi

# 4. Test Python imports
echo "Step 4: Testing Python module imports..."
export PYTHONPATH="$VENDOR_PYTHON_LIBS:$PYTHONPATH"
if python3 -c "import jsonpatch, jsonpointer, prettytable, jsonpath_rw, ply, pyaes, jsondiff, tabulate" 2>/dev/null; then
    echo " All Python modules import successfully"
else
    echo " Warning: Some Python modules may not be accessible"
fi

# 5. Test iLOrest wrapper
echo "Step 5: Testing iLOrest wrapper..."
cd "$ILOREST_TOOLS_DIR"
if ./ilorest_wrapper.sh --version 2>&1 | grep -q "RESTful Interface Tool"; then
    VERSION=$(./ilorest_wrapper.sh --version 2>&1 | grep "RESTful Interface Tool" | head -1)
    echo " iLOrest working: $VERSION"
else
    echo " Warning: iLOrest test failed"
    # Show the actual error for debugging
    echo "Error details:"
    ./ilorest_wrapper.sh --version 2>&1 | head -10
fi

# 6. Validate SUM (Smart Update Manager) dependencies
echo "Step 6: Validating SUM service dependencies..."
SUM_ISSUES=()
VENDOR_BIN_DIR="$SCRIPT_DIR/vendor/tools/local-bin"

# Check for rpm, gawk, strings in vendor directory
for cmd in rpm gawk strings; do
    if [ -f "$VENDOR_BIN_DIR/$cmd" ] && [ -x "$VENDOR_BIN_DIR/$cmd" ]; then
        # Test if the command actually works
        if "$VENDOR_BIN_DIR/$cmd" --version >/dev/null 2>&1; then
            echo " $cmd available and functional in vendor tools"
        else
            echo " $cmd available in vendor tools but has library dependency issues"
            SUM_ISSUES+=("$cmd may need system libraries installed")
        fi
    else
        SUM_ISSUES+=("Missing or non-executable vendor command: $cmd")
    fi
done

# Check for sum_service_x64 if it exists
if [ -f "$SCRIPT_DIR/vendor/tools/sum_service_x64" ]; then
    if [ -x "$SCRIPT_DIR/vendor/tools/sum_service_x64" ]; then
        echo " sum_service_x64 found and executable"
    else
        echo " sum_service_x64 found but not executable, fixing..."
        chmod +x "$SCRIPT_DIR/vendor/tools/sum_service_x64"
        if [ -x "$SCRIPT_DIR/vendor/tools/sum_service_x64" ]; then
            echo " sum_service_x64 permissions fixed"
        else
            SUM_ISSUES+=("sum_service_x64 permissions could not be fixed")
        fi
    fi
fi

if [ ${#SUM_ISSUES[@]} -eq 0 ]; then
    echo " SUM service dependencies validated using vendor tools"
else
    echo " SUM service issues found:"
    for issue in "${SUM_ISSUES[@]}"; do
        echo "  - $issue"
    done
    echo ""
    echo "Note: If SUM service fails with library errors, you may need to install:"
    echo "  - For rpm: sudo apt install librpm9 librpmio9"
    echo "  - For gawk: sudo apt install libsigsegv2"
    echo ""
    echo "To use vendor tools, add to PATH:"
    echo "export PATH=\"$VENDOR_BIN_DIR:\$PATH\""
fi

echo "=========================================="
echo " Ansible Toolkit setup completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test your playbooks"
echo "2. Verify connectivity to target servers"
echo "3. Check that all required files are present"
echo ""
echo "Important: For SUM service support, ensure PATH includes vendor tools:"
echo "export PATH=\"$SCRIPT_DIR/vendor/tools/local-bin:\$PATH\""
echo ""
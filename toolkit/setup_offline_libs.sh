#!/bin/bash
#
# Offline Installation Script for Supermicro Ansible Toolkit
# This script sets up the toolkit to use bundled Python libraries
#
# Usage: ./setup_offline_libs.sh
#

set -e

TOOLKIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_PATH="${TOOLKIT_ROOT}/vendor/python-libs"
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

echo "=== Supermicro Ansible Toolkit Offline Library Setup ==="
echo "Toolkit Root: ${TOOLKIT_ROOT}"
echo "Python Version: ${PYTHON_VERSION}"
echo

# Check if bundled libraries exist
if [ ! -d "${VENDOR_PATH}" ]; then
    echo "ERROR: Bundled libraries not found at ${VENDOR_PATH}"
    echo "Please ensure the vendor/python-libs directory exists with the required packages."
    exit 1
fi

echo "Found bundled libraries:"
ls -la "${VENDOR_PATH}"
echo

# Test prettytable import
echo "Testing library imports..."
python3 -c "
import sys
sys.path.insert(0, '${VENDOR_PATH}')
try:
    from prettytable import PrettyTable
    print('✓ prettytable import successful')
except ImportError as e:
    print('✗ prettytable import failed:', e)
    sys.exit(1)

try:
    import wcwidth
    print('✓ wcwidth import successful')
except ImportError as e:
    print('✗ wcwidth import failed:', e)
    sys.exit(1)
"

echo
echo "=== Testing Ansible Module ==="
cd "${TOOLKIT_ROOT}/playbooks"

# Test if the display_discovery_table module works
python3 -c "
import sys
import os
sys.path.insert(0, os.path.join('${TOOLKIT_ROOT}', 'plugins', 'modules'))
sys.path.insert(0, os.path.join('${TOOLKIT_ROOT}', 'plugins', 'module_utils'))

try:
    from display_discovery_table import HAS_PRETTYTABLE
    if HAS_PRETTYTABLE:
        print('✓ display_discovery_table module can import prettytable')
    else:
        print('✗ display_discovery_table module cannot import prettytable')
        sys.exit(1)
except ImportError as e:
    print('✗ Error importing display_discovery_table:', e)
    sys.exit(1)
"

echo
echo "=== Setup Complete ==="
echo "The toolkit is now configured to use offline libraries."
echo "No internet connection is required for prettytable functionality."
echo
echo "To verify the setup, run:"
echo "  cd ${TOOLKIT_ROOT}/playbooks"
echo "  ansible-playbook ansibleautodiscover_with_tables.yml --check"
echo

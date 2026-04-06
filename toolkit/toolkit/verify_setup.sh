#!/bin/bash
# Quick verification script for new environments

echo "🔧 Quick Ansible Toolkit Verification"
echo "====================================="

# Check if files exist
if [ ! -f "/home/ubuntu/smci/AnsibleToolkit/toolkit/setup_toolkit.sh" ]; then
    echo "❌ Toolkit not found. Please copy AnsibleToolkit directory first."
    exit 1
fi

# Run setup
cd /home/ubuntu/smci/AnsibleToolkit/toolkit
echo "Running setup script..."
./setup_toolkit.sh

# Quick manual test
echo ""
echo "🧪 Manual verification:"
echo "----------------------"
cd vendor/tools

echo "Testing iLOrest version..."
if ./ilorest_wrapper.sh --version 2>&1 | grep -q "RESTful Interface Tool"; then
    echo "✅ iLOrest: $(./ilorest_wrapper.sh --version)"
else
    echo "❌ iLOrest: FAILED"
    exit 1
fi

echo "Testing Python dependencies..."
if PYTHONPATH="../python-libs:$PYTHONPATH" python3 -c "import jsonpath_rw, pyaes, jsonpatch, jsondiff, tabulate" 2>/dev/null; then
    echo "✅ Python dependencies: ALL OK"
else
    echo "❌ Python dependencies: MISSING"
    exit 1
fi

echo ""
echo "🎉 Toolkit is ready for use!"
echo "You can now run your Ansible playbooks."
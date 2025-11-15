#!/bin/bash
# iLOrest Tool Setup Script
# This script ensures iLOrest tool and its dependencies are available

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up iLOrest tool for the toolkit...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
TOOLKIT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Check if ilorest is already available system-wide
if command -v ilorest &> /dev/null; then
    echo -e "${GREEN}ilorest is already available system-wide.${NC}"
    echo "$(which ilorest)"
    exit 0
fi

# Check if our bundled version exists
BUNDLED_ILOREST="$SCRIPT_DIR/ilorest/usr/bin/ilorest"
if [ -f "$BUNDLED_ILOREST" ]; then
    echo -e "${YELLOW}Bundled ilorest found, checking dependencies...${NC}"
    
    # Create a virtual environment for dependencies if needed
    VENV_DIR="$SCRIPT_DIR/venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate virtual environment
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    # Install required Python packages
    pip install --quiet prompt-toolkit jsonpatch requests urllib3 jsonpointer
    
    # Create wrapper script that uses the virtual environment
    cat > "$SCRIPT_DIR/ilorest_bundled" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="$SCRIPT_DIR/ilorest/usr/lib/python3/dist-packages:$PYTHONPATH"
"$SCRIPT_DIR/ilorest/usr/bin/ilorest" "$@"
EOF
    chmod +x "$SCRIPT_DIR/ilorest_bundled"
    
    echo -e "${GREEN}Bundled ilorest setup complete!${NC}"
    echo "ilorest is available at: $SCRIPT_DIR/ilorest_bundled"
    exit 0
fi

echo -e "${YELLOW}Bundled ilorest not found, attempting to install system packages...${NC}"

# Try to install ilorest using system package manager
if command -v apt &> /dev/null; then
    echo "Installing ilorest via apt..."
    sudo apt update -qq
    sudo apt install -y ilorest python3-ilorest
    echo -e "${GREEN}ilorest installed successfully!${NC}"
elif command -v yum &> /dev/null; then
    echo "Installing ilorest via yum..."
    sudo yum install -y python3-ilorest
    echo -e "${GREEN}ilorest installed successfully!${NC}"
elif command -v dnf &> /dev/null; then
    echo "Installing ilorest via dnf..."
    sudo dnf install -y python3-ilorest
    echo -e "${GREEN}ilorest installed successfully!${NC}"
else
    echo -e "${RED}Could not install ilorest automatically.${NC}"
    echo "Please install ilorest manually or contact support."
    exit 1
fi

#!/bin/bash
# Enhanced iLOrest Tool Setup and Wrapper Script
# This script sets up the bundled iLOrest tool with all dependencies for offline environments

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
TOOLKIT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ILOREST_DIR="$SCRIPT_DIR/ilorest"
PYTHON_LIBS_DIR="$TOOLKIT_ROOT/vendor/python-libs"

# Create a comprehensive Python path including all dependencies
export PYTHONPATH="$ILOREST_DIR/usr/lib/python3/dist-packages:$PYTHON_LIBS_DIR:$PYTHONPATH"

# Add all wheel files to Python path
if [ -d "$PYTHON_LIBS_DIR" ]; then
    for wheel_file in "$PYTHON_LIBS_DIR"/*.whl; do
        if [ -f "$wheel_file" ]; then
            export PYTHONPATH="$wheel_file:$PYTHONPATH"
        fi
    done
fi

# Install wheel files to a local site-packages if they're not already extracted
SITE_PACKAGES_DIR="$PYTHON_LIBS_DIR/site-packages"
if [ ! -d "$SITE_PACKAGES_DIR" ]; then
    mkdir -p "$SITE_PACKAGES_DIR"
    
    # Extract wheel files for better compatibility
    for wheel_file in "$PYTHON_LIBS_DIR"/*.whl; do
        if [ -f "$wheel_file" ]; then
            echo "Extracting $(basename "$wheel_file")..."
            cd "$SITE_PACKAGES_DIR"
            python3 -m zipfile -e "$wheel_file" .
            cd - > /dev/null
        fi
    done
fi

# Add extracted packages to Python path
if [ -d "$SITE_PACKAGES_DIR" ]; then
    export PYTHONPATH="$SITE_PACKAGES_DIR:$PYTHONPATH"
fi

# Suppress the error messages by redirecting stderr for module loading issues
exec 2> >(grep -v "ERROR.*loading command.*versioning\|ERROR.*loading command.*rdmc_base_classes" >&2)

# Execute ilorest with the bundled version
"$ILOREST_DIR/usr/bin/ilorest" "$@"
#!/bin/bash
# iLOrest Tool Setup and Wrapper Script
# This script sets up the bundled iLOrest tool and provides a wrapper for execution

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
TOOLKIT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ILOREST_DIR="$SCRIPT_DIR/ilorest"

# Set up Python path for the ilorest libraries
export PYTHONPATH="$ILOREST_DIR/usr/lib/python3/dist-packages:$PYTHONPATH"

# Execute ilorest with the bundled version
"$ILOREST_DIR/usr/bin/ilorest" "$@"

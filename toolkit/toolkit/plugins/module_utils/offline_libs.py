#!/usr/bin/env python3
"""
Offline Library Loader for Supermicro Ansible Toolkit
This module handles loading of bundled Python libraries for offline use.
"""

import sys
import os

def setup_offline_libraries():
    """
    Add bundled Python libraries to the Python path for offline use.
    This allows the toolkit to work without internet access.
    """
    # Multiple possible paths to try for robust path detection
    possible_paths = [
        # Path when run from module_utils directory (plugins/module_utils/)
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'vendor', 'python-libs'),
        # Path when run from toolkit root
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor', 'python-libs'),
        # Path relative to current working directory
        os.path.join(os.getcwd(), 'vendor', 'python-libs'),
        os.path.join(os.getcwd(), '..', 'vendor', 'python-libs'),
    ]
    
    for vendor_path in possible_paths:
        if os.path.exists(vendor_path) and vendor_path not in sys.path:
            sys.path.insert(0, vendor_path)
            return True
    
    return False

def import_prettytable():
    """
    Import prettytable with fallback to bundled version.
    Returns (PrettyTable_class, success_flag)
    """
    try:
        # Try to import from system
        from prettytable import PrettyTable
        return PrettyTable, True
    except ImportError:
        try:
            # Setup offline libraries and try again
            setup_offline_libraries()
            from prettytable import PrettyTable
            return PrettyTable, True
        except ImportError:
            return None, False

# Auto-setup when module is imported
setup_offline_libraries()

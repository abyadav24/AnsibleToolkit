#!/usr/bin/env python3
"""
Parse and format network adapter information from lspci output
"""

import sys
import re

def strip_ansi_codes(text):
    """
    Remove ANSI escape sequences from text (color codes, etc.)
    Pattern matches: ESC [ ... m   and   ESC followed by single char
    """
    # Match all common ANSI escape patterns
    ansi_escape = re.compile(r'\x1B(?:\[[0-9;]*[a-zA-Z]|[^\[])')
    return ansi_escape.sub('', text)

def parse_lspci_line(line):
    """
    Parse a line from lspci -mm output
    Format: PCI_ADDR "TYPE" "VENDOR" "MODEL" -rXX "SUBVENDOR" "SUBMODEL"
    Note: -rXX is NOT in quotes
    """
    # Strip ANSI codes first
    line = strip_ansi_codes(line)
    
    # Extract PCI address (first field before space)
    parts = line.split(maxsplit=1)
    if len(parts) < 2:
        return None
    
    pci_addr = parts[0]
    rest = parts[1]
    
    # Extract quoted fields
    fields = re.findall(r'"([^"]*)"', rest)
    if len(fields) < 4:
        return None
    
    card_type = fields[0] if len(fields) > 0 else ""
    vendor = fields[1] if len(fields) > 1 else ""
    model = fields[2] if len(fields) > 2 else ""
    # fields[3] would be the subvendor (4th quoted field)
    subvendor = fields[3] if len(fields) > 3 else ""
    submodel = fields[4] if len(fields) > 4 else ""
    
    # Clean subvendor - use short form if available
    if subvendor:
        if 'Super Micro' in subvendor or 'Supermicro' in subvendor:
            subvendor = 'Super Micro'
        elif 'Emulex' in subvendor:
            subvendor = 'Emulex'
        elif 'Intel' in subvendor:
            subvendor = 'Intel'
        elif 'Mellanox' in subvendor or 'NVIDIA' in subvendor:
            subvendor = 'Mellanox/NVIDIA'
    
    return {
        'pci_addr': pci_addr,
        'type': card_type,
        'vendor': vendor,
        'model': model,
        'subvendor': subvendor,
        'submodel': submodel
    }

def format_adapters_table(lines, adapter_type="Ethernet"):
    """
    Format adapter information as a clean table
    """
    adapters = []
    
    for line in lines:
        # Strip ANSI codes
        clean_line = strip_ansi_codes(line.strip())
        if not clean_line:
            continue
        # Skip non-adapter lines
        if 'lspci' in clean_line or 'ubuntu@' in clean_line or 'Found' in clean_line or '=====' in clean_line:
            continue
        # Skip debug lines
        if clean_line.startswith('DEBUG:') or clean_line.startswith('Listing'):
            continue
        
        parsed = parse_lspci_line(clean_line)
        if parsed:
            adapters.append(parsed)
    
    if not adapters:
        return f"No {adapter_type} adapters found"
    
    # Create formatted table with proper column widths
    header = f"\n{'='*120}\n{adapter_type} Controllers Detected - Total: {len(adapters)}\n{'='*120}"
    table_header = f"\n{'PCI Address':<13} | {'Vendor':<25} | {'Model / Chipset':<50} | {'Sub-Vendor':<20}"
    separator = f"{'-'*13}-+-{'-'*25}-+-{'-'*50}-+-{'-'*20}"
    
    rows = [header, table_header, separator]
    
    for adapter in adapters:
        # Truncate long strings to fit columns
        vendor = adapter['vendor'][:25]
        model = adapter['model'][:50]
        subvendor = adapter['subvendor'][:20]
        
        row = f"{adapter['pci_addr']:<13} | {vendor:<25} | {model:<50} | {subvendor:<20}"
        rows.append(row)
    
    rows.append('='*120)
    
    return '\n'.join(rows)

def extract_adapters_list(lines):
    """
    Extract list of adapters with PCI addresses for processing
    Returns: list of dicts with pci_addr, vendor, model
    """
    adapters = []
    
    for line in lines:
        # Strip ANSI codes
        clean_line = strip_ansi_codes(line.strip())
        if not clean_line:
            continue
        # Skip non-adapter lines
        if 'lspci' in clean_line or 'ubuntu@' in clean_line or 'Found' in clean_line or '=====' in clean_line:
            continue
        # Skip debug lines
        if clean_line.startswith('DEBUG:') or clean_line.startswith('Listing'):
            continue
        
        parsed = parse_lspci_line(clean_line)
        if parsed:
            adapters.append({
                'pci_addr': parsed['pci_addr'],
                'vendor': parsed['vendor'],
                'model': parsed['model'],
                'subvendor': parsed['subvendor'],
                'submodel': parsed.get('submodel', '')
            })
    
    return adapters

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: format_adapters.py <adapter_type> [--json]")
        print("Reads lspci output from stdin")
        sys.exit(1)
    
    adapter_type = sys.argv[1]
    output_json = '--json' in sys.argv
    
    # Read from stdin
    lines = sys.stdin.readlines()
    
    if output_json:
        import json
        adapters = extract_adapters_list(lines)
        print(json.dumps(adapters, indent=2))
    else:
        formatted = format_adapters_table(lines, adapter_type)
        print(formatted)

#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/home/ubuntu/smci/AnsibleToolkit/toolkit/plugins/modules')

from ansibleautodiscover import discover_server_type, setup_logging, log_debug

# Setup logging
setup_logging()

# Test IPv4 resolution during server discovery
print("Testing server discovery with integrated IPv4 resolution...")

# Test with one known server
test_server = "fe80::7ea6:2aff:fe6e:cd2a%enp0s8"  # Known working server

print(f"Testing server discovery for: {test_server}")
server_info = discover_server_type(test_server, "admin", "cmb9.admin")

if server_info:
    print(f"Success!")
    print(f"  Type: {server_info['type']}")
    print(f"  Model: {server_info['model']}")
    print(f"  Serial: {server_info['serial_number']}")
    print(f"  IPv4: {server_info['ipv4_address']}")
else:
    print("Failed to discover server")

print("\nDone!")
#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/home/ubuntu/smci/AnsibleToolkit/toolkit/plugins/modules')

from ansibleautodiscover import resolve_ipv4_address, setup_logging, log_debug

# Setup logging
setup_logging()

# Test IPv4 resolution for known servers with their serial numbers
test_servers = [
    {
        "ipv6": "fe80::5eed:8cff:fe01:2de8%enp0s8",
        "device_info": {"serial_number": "SGH323YN27", "model": "Hitachi Advanced Server HA815 G3"}
    },
    {
        "ipv6": "fe80::5eed:8cff:fe36:b674%enp0s8", 
        "device_info": {"serial_number": "CNX24300K3", "model": "Hitachi Advanced Server HA810 G3"}
    },
    {
        "ipv6": "fe80::7ea6:2aff:fe6e:ab64%enp0s8",
        "device_info": {"serial_number": "3M1D30109P", "model": "Hitachi Advanced Server HA810 G6"}
    }
]

print("Testing improved IPv4 resolution with serial correlation...")
for server in test_servers:
    print(f"\nTesting: {server['ipv6']}")
    print(f"Serial: {server['device_info']['serial_number']}")
    print(f"Model: {server['device_info']['model']}")
    ipv4 = resolve_ipv4_address(server['ipv6'], server['device_info'])
    print(f"Result: {ipv4}")

print("\nDone!")
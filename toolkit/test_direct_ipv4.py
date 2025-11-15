#!/usr/bin/env python3
"""
Test script to verify IPv4 resolution directly from server API during discovery
"""

import sys
import os
sys.path.append('/home/ubuntu/smci/AnsibleToolkit/toolkit/plugins/modules')

from ansibleautodiscover import discover_server_type, setup_logging, log_debug

def test_direct_ipv4_discovery():
    """Test IPv4 discovery during server discovery"""
    print("Testing direct IPv4 discovery during server detection...")
    
    # Setup logging
    setup_logging()
    
    # Test with known servers
    test_servers = [
        "fe80::7ea6:2aff:fe6e:cd2a%enp0s8",  # HA810 G6
        "fe80::5eed:8cff:fe01:2de8%enp0s8",  # SGH323YN27
        "fe80::5eed:8cff:fe36:b674%enp0s8",  # CNX24300K3
    ]
    
    for i, ipv6_addr in enumerate(test_servers, 1):
        print(f"\n=== Test {i}/3: {ipv6_addr} ===")
        
        result = discover_server_type(ipv6_addr, "admin", "cmb9.admin")
        
        if result:
            print(f"✅ Server discovered:")
            print(f"   Type: {result['type']}")
            print(f"   Model: {result['model']}")
            print(f"   Serial: {result['serial_number']}")
            print(f"   IPv4: {result.get('ipv4_address', 'None')}")
            
            if result.get('ipv4_address'):
                print(f"   🎉 IPv4 successfully resolved!")
            else:
                print(f"   ❌ IPv4 not resolved")
        else:
            print(f"❌ Server discovery failed")
    
    print(f"\n=== Test Complete ===")

if __name__ == "__main__":
    test_direct_ipv4_discovery()
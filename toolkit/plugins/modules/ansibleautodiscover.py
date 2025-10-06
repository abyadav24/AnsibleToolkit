#!/usr/bin/python

# Copyright: (c) 2025, Ansible Module
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ansibleautodiscover

short_description: Discovers servers and switches via IPv6 link-local addressing

version_added: "1.0.0"

description: This module discovers servers and switches on the network using IPv6 link-local addressing. It can discover various server types and network switches without performing any configuration operations.

options:
    interface:
        description: Network interface to use for discovery. If not specified, all interfaces will be used.
        required: false
        type: str
    target_nodes:
        description: List of specific IPv6 addresses to discover. If provided, interface discovery is skipped.
        required: false
        type: list
    usernames:
        description: List of usernames to try for authentication
        required: false
        type: list
        default: ['admin']
    passwords:
        description: List of passwords to try for authentication
        required: false
        type: list
        default: ['cmb9.admin']
    switch_usernames:
        description: List of usernames to try for switch authentication
        required: false
        type: list
        default: ['admin']
    switch_passwords:
        description: List of passwords to try for switch authentication
        required: false
        type: list
        default: ['Passw0rd!']
    discover_servers:
        description: Whether to discover servers
        required: false
        type: bool
        default: true
    discover_switches:
        description: Whether to discover switches
        required: false
        type: bool
        default: true

author:
    - Ansible Module (@ansible)
'''

EXAMPLES = r'''
# Discover both servers and switches
- name: Discover all devices
  ansibleautodiscover:

# Discover only servers
- name: Discover servers only
  ansibleautodiscover:
    discover_switches: false

# Discover with specific interface
- name: Discover on specific interface
  ansibleautodiscover:
    interface: eth0
    usernames: ['admin', 'root']
    passwords: ['password1', 'password2']
'''

RETURN = r'''
servers:
    description: List of discovered servers
    type: list
    returned: when discover_servers is true
    sample: [
        {
            "type": "QuantaSkylake",
            "host": "fe80::aa1e:84ff:fe73:ba49%eth0",
            "ipv4_address": "192.168.1.100",
            "username": "admin",
            "password": "cmb9.admin",
            "model": "D52B",
            "serial_number": "ABC123456"
        }
    ]
switches:
    description: List of discovered switches
    type: list
    returned: when discover_switches is true
    sample: [
        {
            "type": "Nexus92348",
            "host": "fe80::aa1e:84ff:fe73:ba50%eth0",
            "ipv4_address": "192.168.1.101",
            "username": "admin",
            "password": "Passw0rd!",
            "model": "C92348GC-X"
        }
    ]
'''

import socket
import subprocess
import json
import requests
import urllib3
import itertools
import sys
import time
import os
import logging
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule

urllib3.disable_warnings()

# Setup logging
def setup_logging():
    """Setup logging to file with timestamp"""
    # Use a fixed logs directory path - avoid using module path during Ansible execution
    logs_dir = "/home/ubuntu/smci/ansible-toolkit/toolkit/logs"
    
    # Ensure logs directory exists
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"ansibleautodiscover_{timestamp}.log"
    log_path = os.path.join(logs_dir, log_filename)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stderr)  # Also log to stderr for immediate visibility
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_path}")
    return logger

# Initialize logger
logger = setup_logging()

def log_debug(message):
    """Log debug messages to both file and stderr"""
    logger.debug(message)

def get_nic_interfaces():
    """Get all non-loopback and UP NIC interfaces from /sys/class/net"""
    interfaces = []
    try:
        log_debug("Getting UP network interfaces from /sys/class/net...")
        for iface in os.listdir('/sys/class/net'):
            if iface != 'lo':
                operstate_path = f"/sys/class/net/{iface}/operstate"
                try:
                    with open(operstate_path) as f:
                        state = f.read().strip()
                    if state == "up":
                        interfaces.append(iface)
                        log_debug(f"Interface {iface} is up and added.")
                    else:
                        log_debug(f"Interface {iface} is {state}, skipping.")
                except Exception as e:
                    log_debug(f"Could not read state for {iface}: {e}")
    except Exception as e:
        log_debug(f"Error getting interfaces: {e}")
        return []
    
    log_debug(f"Found UP interfaces: {interfaces}")
    return interfaces

def get_ipv6_neighbors(interface=None):
    """Discover IPv6 link-local devices using ping6 to multicast"""
    log_debug("Starting IPv6 neighbor discovery...")
    nics = []
    if interface is None:
        nics = get_nic_interfaces()
    else:
        nics.append(str(interface))
    
    log_debug(f"Will scan interfaces: {nics}")
    
    ipv6_devices = []
    for nic in nics:
        try:
            log_debug(f"Pinging multicast on interface {nic}...")
            # Send ping to all-nodes multicast address
            cmd = ['ping6', '-c', '2', f'ff02::1%{nic}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = result.stdout
            
            log_debug(f"Parsing ping responses from interface {nic}...")
            # Parse ping responses to extract IPv6 addresses
            for line in output.splitlines():
                if line.startswith("64 bytes from fe80:"):
                    # Extract the source address
                    parts = line.split()
                    ipv6_address = parts[3].rstrip(':')  # Remove trailing colon
                    if ipv6_address not in ipv6_devices:
                        ipv6_devices.append(ipv6_address)
                        log_debug(f"Found IPv6 device: {ipv6_address}")
                        
        except Exception as e:
            log_debug(f"Error scanning interface {nic}: {e}")
            continue
    
    log_debug(f"Total IPv6 devices found: {len(ipv6_devices)}")
    return ipv6_devices

def test_ipmi_port(ipv6_node):
    """Test if IPMI port 623 is open"""
    log_debug(f"Testing IPMI port 623 on {ipv6_node}")
    try:
        addrinfo = socket.getaddrinfo(ipv6_node, 623, socket.AF_INET6, socket.SOCK_DGRAM)
        family, socktype, proto, canonname, sockaddr = addrinfo[0]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(2)  # Reduced timeout
        result = sock.connect_ex(sockaddr)
        sock.close()
        is_open = result == 0
        log_debug(f"IPMI port 623 on {ipv6_node}: {'OPEN' if is_open else 'CLOSED'}")
        return is_open
    except Exception as e:
        log_debug(f"Error testing IPMI port on {ipv6_node}: {e}")
        return False

def test_ssh_port(ipv6_address):
    """Test if SSH port 22 is open"""
    log_debug(f"Testing SSH port 22 on {ipv6_address}")
    try:
        addrinfo = socket.getaddrinfo(ipv6_address, 22, socket.AF_INET6, socket.SOCK_STREAM)
        family, socktype, proto, canonname, sockaddr = addrinfo[0]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(2)
        result = sock.connect_ex(sockaddr)
        sock.close()
        is_open = result == 0
        log_debug(f"SSH port 22 on {ipv6_address}: {'OPEN' if is_open else 'CLOSED'}")
        return is_open
    except Exception as e:
        log_debug(f"Error testing SSH port on {ipv6_address}: {e}")
        return False

def discover_server_type(ipv6_node, username, password):
    """Discover server type via Redfish API using original logic"""
    log_debug(f"Starting server discovery for {ipv6_node} with username {username}")
    
    if not test_ipmi_port(ipv6_node):
        log_debug(f"IPMI port not accessible on {ipv6_node}, skipping")
        return None
    
    # Set up Redfish API URL (use Systems/1 endpoint like original)
    redfish_api = f'https://[{ipv6_node.replace("%", "%25")}]/redfish/v1/Systems/'
    redfish_header = {
        'Content-Type': 'application/json',
        'User-Agent': 'curl/7.54.0',
        'Host': f'[{ipv6_node.split("%")[0]}]'
    }
    
    try:
        log_debug(f"Attempting Redfish connection to {redfish_api}1")
        # Connect directly to Systems/1 endpoint like original
        session = requests.get(f'{redfish_api}1', 
                             auth=(username, password), 
                             verify=False,
                             headers=redfish_header, 
                             timeout=10)
        
        log_debug(f"Redfish response status: {session.status_code}")
        
        if not session.ok:
            log_debug(f"Failed to connect to Redfish on {ipv6_node}")
            return None
            
        j = session.json()
        sku = j.get('SKU', '')
        model = j.get('Model', '')
        serial = j.get('SerialNumber', '')
        
        log_debug(f"Server info - SKU: {sku}, Model: {model}, Serial: {serial}")
        
        # Determine server type based on SKU/Model
        server_type = 'Unknown'
        if 'Advanced Server DS120_S5B-MB' in sku:
            server_type = 'DS120_G1'
        elif 'Advanced Server DS220_S5B-MB' in sku:
            server_type = 'DS220_G1'
        elif 'Advanced Server DS120 G2_S5X' in sku:
            server_type = 'DS120_G2'
        elif 'Advanced Server DS220 G2_S5X' in sku:
            server_type = 'DS220_G2'
        elif 'DS225' in sku:
            server_type = 'DS225'
        elif 'DS240' in sku:
            server_type = 'DS240'
        elif 'D52BV' in sku:
            server_type = 'D52BV'
        elif 'D52B' in sku:
            server_type = 'D52B'
        elif 'Q72D' in sku:
            server_type = 'Q72D'
        elif 'Hitachi Advanced Server' in model:
            server_type = 'HA_Server'
        
        log_debug(f"Identified server type: {server_type}")
        
        return {
            'type': server_type,
            'host': ipv6_node,
            'username': username,
            'password': password,
            'model': model,
            'sku': sku,
            'serial_number': serial,
            'ipv4_address': None  # Will be populated later if needed
        }
        
    except Exception as e:
        log_debug(f"Exception during server discovery for {ipv6_node}: {e}")
        return None

def discover_switch_type(ipv6_address, username, password):
    """Discover switch type via SSH (simplified)"""
    log_debug(f"Starting switch discovery for {ipv6_address} with username {username}")
    
    # First check if SSH port is open
    if not test_ssh_port(ipv6_address):
        log_debug(f"SSH port not accessible on {ipv6_address}, skipping")
        return None
    
    try:
        from netmiko import ConnectHandler
        
        log_debug(f"Attempting SSH connection to {ipv6_address}")
        net_connect = ConnectHandler(
            device_type='terminal_server',
            ip=ipv6_address,
            username=username,
            password=password,
            timeout=10,  # Reduced timeout
            conn_timeout=10  # Add connection timeout
        )
        
        log_debug(f"SSH connection established to {ipv6_address}")
        
        # Try different show commands
        commands = ["show version", "chassisshow"]
        output = ""
        
        for cmd in commands:
            try:
                log_debug(f"Executing command '{cmd}' on {ipv6_address}")
                result = net_connect.send_command(cmd, delay_factor=10, max_loops=50)
                output += result
                break
            except Exception as e:
                log_debug(f"Command '{cmd}' failed on {ipv6_address}: {e}")
                continue
        
        net_connect.disconnect()
        log_debug(f"SSH connection closed for {ipv6_address}")
        
        # Determine switch type based on output
        switch_type = 'Unknown'
        model = 'Unknown'
        
        if 'C92348GC-X' in output:
            switch_type = 'Nexus92348'
            model = 'C92348GC-X'
        elif '93180YC-FX3' in output:
            switch_type = 'Nexus93180YCFX3'
            model = '93180YC-FX3'
        elif '93180YC-FX' in output:
            switch_type = 'Nexus93180YCFX'
            model = '93180YC-FX'
        elif 'C93600CD-GX' in output:
            switch_type = 'Nexus93600CDGX'
            model = 'C93600CD-GX'
        elif '9332C' in output:
            switch_type = 'Nexus9332C'
            model = '9332C'
        elif 'C9316D-GX' in output:
            switch_type = 'Nexus9316D'
            model = 'C9316D-GX'
        elif 'BROCAD0000G62' in output:
            switch_type = 'G620'
            model = 'G620'
        elif 'SLKWRM0000G72' in output:
            switch_type = 'G720'
            model = 'G720'
        elif '7010T' in output:
            switch_type = 'DCS7010'
            model = '7010T'
        elif '7050SX3' in output:
            switch_type = 'DCS7050SX3'
            model = '7050SX3'
        elif '7050CX3' in output:
            switch_type = 'DCS7050CX3'
            model = '7050CX3'
        
        log_debug(f"Identified switch type: {switch_type}, model: {model}")
        
        return {
            'type': switch_type,
            'host': ipv6_address,
            'username': username,
            'password': password,
            'model': model,
            'ipv4_address': None  # Will be populated later if needed
        }
        
    except Exception as e:
        log_debug(f"Exception during switch discovery for {ipv6_address}: {e}")
        return None

def quick_ping_test(ipv6_address):
    """Quick ping test to see if device is responsive"""
    try:
        log_debug(f"Quick ping test to {ipv6_address}")
        result = subprocess.run(['ping6', '-c', '1', '-W', '1', ipv6_address], 
                              capture_output=True, timeout=3)
        is_alive = result.returncode == 0
        log_debug(f"Ping test for {ipv6_address}: {'ALIVE' if is_alive else 'NO RESPONSE'}")
        return is_alive
    except Exception as e:
        log_debug(f"Ping test failed for {ipv6_address}: {e}")
        return False

def discover_servers(ipv6_nodes, usernames, passwords):
    """Discover servers sequentially"""
    log_debug(f"Starting server discovery for {len(ipv6_nodes)} nodes")
    servers = []
    for i, ipv6_node in enumerate(ipv6_nodes):
        log_debug(f"Processing server {i+1}/{len(ipv6_nodes)}: {ipv6_node}")
        
        # Quick ping test first
        if not quick_ping_test(ipv6_node):
            log_debug(f"Device {ipv6_node} not responding to ping, skipping")
            continue
            
        result = None
        for username in usernames:
            for password in passwords:
                result = discover_server_type(ipv6_node, username, password)
                if result:
                    log_debug(f"Successfully discovered server: {result['type']}")
                    servers.append(result)
                    break  # Stop trying passwords for this node
            if result:
                break  # Stop trying usernames for this node
        
        # If no server found, log and continue to next node
        if not result:
            log_debug(f"No server discovered at {ipv6_node}")
    
    log_debug(f"Total servers discovered: {len(servers)}")
    return servers

def discover_switches(ipv6_addresses, usernames, passwords):
    """Discover switches sequentially"""
    log_debug(f"Starting switch discovery for {len(ipv6_addresses)} nodes")
    switches = []
    for i, ipv6_address in enumerate(ipv6_addresses):
        log_debug(f"Processing switch {i+1}/{len(ipv6_addresses)}: {ipv6_address}")
        
        # Quick ping test first
        if not quick_ping_test(ipv6_address):
            log_debug(f"Device {ipv6_address} not responding to ping, skipping")
            continue
            
        result = None
        for username in usernames:
            for password in passwords:
                result = discover_switch_type(ipv6_address, username, password)
                if result:
                    log_debug(f"Successfully discovered switch: {result['type']}")
                    switches.append(result)
                    break  # Stop trying passwords for this node
            if result:
                break  # Stop trying usernames for this node
        
        # If no switch found, log and continue to next node
        if not result:
            log_debug(f"No switch discovered at {ipv6_address}")
    
    log_debug(f"Total switches discovered: {len(switches)}")
    return switches

def run_module():
    logger.info("Starting ansibleautodiscover module")
    
    # Define available arguments/parameters
    module_args = dict(
        interface=dict(type='str', required=False),
        target_nodes=dict(type='list', required=False),
        usernames=dict(type='list', required=False, default=['admin']),
        passwords=dict(type='list', required=False, default=['cmb9.admin']),
        switch_usernames=dict(type='list', required=False, default=['admin']),
        switch_passwords=dict(type='list', required=False, default=['Passw0rd!']),
        discover_servers=dict(type='bool', required=False, default=True),
        discover_switches=dict(type='bool', required=False, default=True)
    )

    # Seed the result dict
    result = dict(
        changed=False,
        servers=[],
        switches=[],
        message=''
    )

    # The AnsibleModule object
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # If the user is working with this module in only check mode
    if module.check_mode:
        module.exit_json(**result)

    # Get module parameters
    interface = module.params['interface']
    target_nodes = module.params['target_nodes']
    usernames = module.params['usernames']
    passwords = module.params['passwords']
    switch_usernames = module.params['switch_usernames']
    switch_passwords = module.params['switch_passwords']
    discover_servers_flag = module.params['discover_servers']
    discover_switches_flag = module.params['discover_switches']

    logger.info(f"Module parameters - interface: {interface}, target_nodes: {target_nodes}, discover_servers: {discover_servers_flag}, discover_switches: {discover_switches_flag}")
    logger.info(f"Authentication - server usernames: {len(usernames)}, server passwords: {len(passwords)}, switch usernames: {len(switch_usernames)}, switch passwords: {len(switch_passwords)}")

    try:
        # Get IPv6 devices - either from target_nodes or interface discovery
        if target_nodes:
            logger.info(f"Using target nodes from config: {len(target_nodes)} nodes")
            ipv6_devices = target_nodes
            log_debug(f"Target nodes provided: {target_nodes}")
        else:
            logger.info("Starting IPv6 device discovery...")
            log_debug("Starting module execution...")
            ipv6_devices = get_ipv6_neighbors(interface)
        
        logger.info(f"Found {len(ipv6_devices)} IPv6 devices")
        
        if not ipv6_devices:
            logger.warning("No IPv6 devices found")
            result['message'] = 'No IPv6 devices found'
            log_debug("No IPv6 devices found, exiting")
            module.exit_json(**result)

        log_debug(f"Found {len(ipv6_devices)} IPv6 devices, starting discovery...")

        # Discover servers
        if discover_servers_flag:
            log_debug("Starting server discovery phase...")
            servers = discover_servers(ipv6_devices, usernames, passwords)
            result['servers'] = servers
            result['message'] += f'Found {len(servers)} servers. '

        # Discover switches
        if discover_switches_flag:
            log_debug("Starting switch discovery phase...")
            switches = discover_switches(ipv6_devices, switch_usernames, switch_passwords)
            result['switches'] = switches
            result['message'] += f'Found {len(switches)} switches.'

        log_debug("Discovery complete, preparing results...")
        result['changed'] = True

    except Exception as e:
        log_debug(f"Exception in module execution: {e}")
        module.fail_json(msg=f'Discovery failed: {str(e)}', **result)

    # Exit with results
    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()

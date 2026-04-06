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
import signal
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule

urllib3.disable_warnings()

# Global timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def with_timeout(timeout_seconds):
    """Decorator to add timeout to functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Set the signal handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # Disable the alarm
                return result
            except TimeoutError:
                log_debug(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
                signal.alarm(0)
                return None
            except Exception as e:
                signal.alarm(0)
                raise e
        return wrapper
    return decorator

# Setup logging
def setup_logging():
    """Setup logging to file with timestamp"""
    # Dynamically determine logs directory relative to this module
    module_dir = os.path.dirname(os.path.abspath(__file__))
    toolkit_root = os.path.dirname(os.path.dirname(module_dir))  # Go up 2 levels
    logs_dir = os.path.join(toolkit_root, 'logs')
    
    # Fallback to current working directory if toolkit structure not found
    if not os.path.exists(os.path.dirname(logs_dir)):
        logs_dir = os.path.join(os.getcwd(), 'logs')
    
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
    """Discover IPv6 link-local devices using ping6 to multicast - optimized version"""
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
    # Limit the number of devices to process for performance (optional safety limit)
    if len(ipv6_devices) > 50:
        log_debug(f"Warning: Found {len(ipv6_devices)} devices, limiting to first 50 for performance")
        ipv6_devices = ipv6_devices[:50]
    
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
        
        # Get IPv4 address directly from the server's network configuration
        ipv4_address = None
        
        try:
            log_debug(f"Getting IPv4 address directly from server {ipv6_node}")
            
            # Try different network interface endpoints to get IPv4 configuration
            network_endpoints = [
                '/redfish/v1/Managers/BMC/EthernetInterfaces/1',
                '/redfish/v1/Managers/1/EthernetInterfaces/1', 
                '/redfish/v1/Managers/BMC/EthernetInterfaces',
                '/redfish/v1/Managers/1/EthernetInterfaces'
            ]
            
            for endpoint in network_endpoints:
                try:
                    log_debug(f"Trying network endpoint: {endpoint}")
                    net_url = f'https://[{ipv6_node.replace("%", "%25")}]{endpoint}'
                    net_response = requests.get(net_url,
                                              auth=(username, password),
                                              verify=False,
                                              headers=redfish_header,
                                              timeout=5)
                    
                    if net_response.status_code == 200:
                        net_data = net_response.json()
                        log_debug(f"Got network data from {endpoint}")
                        
                        # Check for IPv4 addresses in direct response
                        if 'IPv4Addresses' in net_data and net_data['IPv4Addresses']:
                            for ipv4_entry in net_data['IPv4Addresses']:
                                if isinstance(ipv4_entry, dict) and 'Address' in ipv4_entry:
                                    ip = ipv4_entry['Address']
                                    if ip and ip != '0.0.0.0' and ip != 'null' and '.' in ip:
                                        log_debug(f"Found IPv4 {ip} from direct endpoint {endpoint}")
                                        ipv4_address = ip
                                        break
                        
                        # Check for IPv4StaticAddresses
                        if not ipv4_address and 'IPv4StaticAddresses' in net_data and net_data['IPv4StaticAddresses']:
                            for ipv4_entry in net_data['IPv4StaticAddresses']:
                                if isinstance(ipv4_entry, dict) and 'Address' in ipv4_entry:
                                    ip = ipv4_entry['Address']
                                    if ip and ip != '0.0.0.0' and ip != 'null' and '.' in ip:
                                        log_debug(f"Found IPv4 {ip} from static addresses in {endpoint}")
                                        ipv4_address = ip
                                        break
                        
                        # Check if this is a collection endpoint with members
                        if not ipv4_address and 'Members' in net_data and net_data['Members']:
                            log_debug(f"Found {len(net_data['Members'])} interface members")
                            for member in net_data['Members'][:3]:  # Check first 3 members only
                                member_url = member.get('@odata.id', '')
                                if member_url:
                                    try:
                                        member_response = requests.get(f"https://[{ipv6_node.replace('%', '%25')}]{member_url}",
                                                                     auth=(username, password),
                                                                     verify=False,
                                                                     headers=redfish_header,
                                                                     timeout=3)
                                        if member_response.status_code == 200:
                                            member_data = member_response.json()
                                            
                                            # Check IPv4 addresses in member
                                            if 'IPv4Addresses' in member_data and member_data['IPv4Addresses']:
                                                for ipv4_entry in member_data['IPv4Addresses']:
                                                    if isinstance(ipv4_entry, dict) and 'Address' in ipv4_entry:
                                                        ip = ipv4_entry['Address']
                                                        if ip and ip != '0.0.0.0' and ip != 'null' and '.' in ip:
                                                            log_debug(f"Found IPv4 {ip} from member {member_url}")
                                                            ipv4_address = ip
                                                            break
                                            
                                            if ipv4_address:
                                                break
                                    except Exception as e:
                                        log_debug(f"Failed to query member {member_url}: {e}")
                        
                        if ipv4_address:
                            break  # Found IPv4, stop trying endpoints
                            
                except Exception as e:
                    log_debug(f"Failed to query network endpoint {endpoint}: {e}")
                    continue
        
        except Exception as e:
            log_debug(f"Error getting IPv4 from server network config: {e}")
        
        # If Redfish API didn't work, try iLOrest command as fallback
        if not ipv4_address:
            ipv4_address = get_ipv4_via_ilorest(ipv6_node, username, password)
        
        if ipv4_address:
            log_debug(f"Successfully resolved IPv4 address {ipv4_address} for server {ipv6_node}")
        else:
            log_debug(f"Could not resolve IPv4 address for server {ipv6_node}")
            ipv4_address = "N/A"  # Explicitly set to N/A instead of None
        
        return {
            'type': server_type,
            'host': ipv6_node,
            'username': username,
            'password': password,
            'model': model,
            'sku': sku,
            'serial_number': serial,
            'ipv4_address': ipv4_address
        }
        
    except Exception as e:
        log_debug(f"Exception during server discovery for {ipv6_node}: {e}")
        return None

def get_ipv4_via_ilorest(ipv6_node, username, password):
    """Get IPv4 address using iLOrest command"""
    try:
        ipv6_clean = ipv6_node.split('%')[0] if '%' in ipv6_node else ipv6_node
        log_debug(f"Attempting iLOrest query for {ipv6_clean}")
        
        # Try different iLOrest commands to get network info
        commands = [
            ['ilorest', 'get', 'IPv4Addresses', '--url', f'https://[{ipv6_clean}]', '--username', username, '--password', password, '--nologo'],
            ['ilorest', 'get', 'EthernetInterfaces', '--url', f'https://[{ipv6_clean}]', '--username', username, '--password', password, '--nologo']
        ]
        
        for cmd in commands:
            try:
                log_debug(f"Running: {' '.join(cmd[:4])}...")  # Don't log credentials
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
                
                if result.returncode == 0 and result.stdout:
                    log_debug(f"iLOrest command successful, parsing output...")
                    
                    # Look for IPv4 addresses in various formats
                    lines = result.stdout.split('\n')
                    for line in lines:
                        # Look for patterns like "Address=192.168.1.100" or similar
                        if any(pattern in line.lower() for pattern in ['address=', 'ipv4address=', 'ip=']):
                            for part in line.split():
                                if '=' in part and '.' in part:
                                    ip = part.split('=')[-1].strip().strip('"\'()[]')
                                    if ip and ip != '0.0.0.0' and ip != 'null' and len(ip.split('.')) == 4:
                                        # Validate IP format
                                        try:
                                            parts = ip.split('.')
                                            if all(0 <= int(p) <= 255 for p in parts):
                                                log_debug(f"Found valid IPv4 {ip} via iLOrest")
                                                return ip
                                        except ValueError:
                                            continue
                else:
                    log_debug(f"iLOrest command failed: {result.stderr}")
                    
            except Exception as e:
                log_debug(f"iLOrest command exception: {e}")
                continue
                
        return None
        
    except Exception as e:
        log_debug(f"iLOrest query failed: {e}")
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
        
        # Resolve IPv4 address for this switch
        device_info = {
            'model': model,
            'type': switch_type
        }
        ipv4_address = resolve_ipv4_address(ipv6_address, device_info)
        
        if ipv4_address:
            log_debug(f"Resolved IPv4 address {ipv4_address} for switch {ipv6_address}")
        else:
            log_debug(f"Could not resolve IPv4 address for switch {ipv6_address}")
            ipv4_address = "N/A"  # Explicitly set to N/A instead of None
        
        return {
            'type': switch_type,
            'host': ipv6_address,
            'username': username,
            'password': password,
            'model': model,
            'ipv4_address': ipv4_address
        }
        
    except Exception as e:
        log_debug(f"Exception during switch discovery for {ipv6_address}: {e}")
        return None

def resolve_ipv4_address(ipv6_address, device_info=None):
    """Resolve IPv4 address from IPv6 link-local address - improved correlation"""
    try:
        log_debug(f"Attempting to resolve IPv4 for {ipv6_address}")
        
        # Method 1: Check system neighbor tables for IPv6->IPv4 mappings (fastest method)
        try:
            ipv6_clean = ipv6_address.split('%')[0] if '%' in ipv6_address else ipv6_address
            log_debug(f"Cleaned IPv6: {ipv6_clean}")
            
            # Check IPv6 neighbor table for MAC address
            result = subprocess.run(['ip', '-6', 'neighbor', 'show'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                log_debug(f"IPv6 neighbor table result: {result.stdout[:200]}...")
                mac_address = None
                for line in result.stdout.split('\n'):
                    if ipv6_clean.lower() in line.lower():
                        log_debug(f"Found line: {line}")
                        parts = line.split()
                        for part in parts:
                            if ':' in part and len(part) == 17:  # MAC format
                                mac_address = part
                                break
                        break
                
                # If we found MAC, look for IPv4 with same MAC
                if mac_address:
                    log_debug(f"Found MAC {mac_address} for {ipv6_address}")
                    ipv4_result = subprocess.run(['ip', 'neighbor', 'show'], 
                                                capture_output=True, text=True, timeout=2)
                    if ipv4_result.returncode == 0:
                        log_debug(f"IPv4 neighbor table result: {ipv4_result.stdout[:200]}...")
                        for line in ipv4_result.stdout.split('\n'):
                            if mac_address.lower() in line.lower():
                                parts = line.split()
                                if len(parts) > 0 and '.' in parts[0]:
                                    ipv4 = parts[0]
                                    log_debug(f"Found IPv4 {ipv4} via MAC mapping")
                                    return ipv4
                else:
                    log_debug("No MAC address found in IPv6 neighbor table")
        except Exception as e:
            log_debug(f"Neighbor table check failed: {e}")
        
        # Method 2: Try direct REST API query with very short timeout
        try:
            ipv6_clean = ipv6_address.split('%')[0] if '%' in ipv6_address else ipv6_address
            log_debug(f"Attempting direct REST query for {ipv6_clean}")
            
            url = f"https://[{ipv6_clean}]/redfish/v1/Managers/BMC/EthernetInterfaces/1"
            log_debug(f"Trying URL: {url}")
            
            response = requests.get(url, 
                                  auth=('admin', 'cmb9.admin'),
                                  verify=False, timeout=3)
            if response.status_code == 200:
                data = response.json()
                log_debug(f"Got response: {str(data)[:200]}...")
                
                # Look for IPv4 addresses in the response
                if 'IPv4Addresses' in data and data['IPv4Addresses']:
                    for ipv4_entry in data['IPv4Addresses']:
                        if 'Address' in ipv4_entry:
                            ipv4 = ipv4_entry['Address']
                            if ipv4 and ipv4 != '0.0.0.0' and ipv4 != 'null':
                                log_debug(f"Found IPv4 {ipv4} via direct query")
                                return ipv4
            else:
                log_debug(f"REST query failed with status: {response.status_code}")
                        
        except Exception as e:
            log_debug(f"Direct query failed: {e}")
        
        # Method 3: Correlate by querying devices directly via IPv4 to match serial numbers
        if device_info and device_info.get('serial_number'):
            log_debug(f"Attempting device correlation using serial number: {device_info['serial_number']}")
            ipv4 = find_ipv4_by_serial_correlation(device_info['serial_number'], ipv6_address)
            if ipv4:
                return ipv4
        
        # Method 4: Only try direct device query - remove unreliable IP scanning
        log_debug("Attempting device correlation using direct query...")
        if device_info and device_info.get('serial_number'):
            log_debug(f"Attempting device correlation using serial number: {device_info['serial_number']}")
            ipv4 = find_ipv4_by_serial_correlation(device_info['serial_number'], ipv6_address)
            if ipv4:
                return ipv4
        
        # No reliable method found - return None instead of guessing
        log_debug(f"Could not reliably resolve IPv4 for {ipv6_address}")
        return None
        
    except Exception as e:
        log_debug(f"IPv4 resolution failed for {ipv6_address}: {e}")
        return None

def find_ipv4_by_serial_correlation(target_serial, ipv6_address):
    """Find IPv4 address by querying devices and matching serial numbers - strict matching only"""
    try:
        log_debug(f"Looking for device with serial: {target_serial}")
        
        # Only try a limited set of IPs and require exact serial match
        test_ranges = [
            ("172.23.55", range(90, 120)),   # Current network range
            ("192.168.1", range(100, 110))   # Common IPMI range
        ]
        
        for base_network, host_range in test_ranges:
            for host in host_range:
                test_ip = f"{base_network}.{host}"
                try:
                    # Only proceed if device responds and we can get serial number
                    response = requests.get(f"https://{test_ip}/redfish/v1/Systems/1", 
                                          auth=('admin', 'cmb9.admin'),
                                          verify=False, timeout=3)
                    if response.status_code == 200:
                        data = response.json()
                        device_serial = data.get('SerialNumber', '')
                        # Only return IP if serial numbers match EXACTLY
                        if device_serial and device_serial == target_serial:
                            log_debug(f"Found exact serial match {device_serial} at {test_ip}")
                            return test_ip
                        elif device_serial:
                            log_debug(f"Serial mismatch at {test_ip}: expected {target_serial}, got {device_serial}")
                    else:
                        log_debug(f"No valid response from {test_ip} (status: {response.status_code})")
                except Exception as e:
                    log_debug(f"Failed to query {test_ip}: {e}")
                    continue
                    
        log_debug(f"No device found with matching serial number {target_serial}")
        return None
        
    except Exception as e:
        log_debug(f"Serial correlation failed: {e}")
        return None

def correlate_ipv4_with_ipv6(ipv4_address, ipv6_address, device_info=None):
    """Correlate IPv4 and IPv6 addresses by checking if they belong to the same device"""
    try:
        log_debug(f"Correlating {ipv4_address} with {ipv6_address}")
        
        # Method 1: Compare serial numbers if we have device info
        if device_info and device_info.get('serial_number'):
            try:
                # Query the IPv4 device for its serial number
                response = requests.get(f"https://{ipv4_address}/redfish/v1/Systems/1", 
                                      auth=('admin', 'cmb9.admin'),
                                      verify=False, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    ipv4_serial = data.get('SerialNumber', '')
                    ipv6_serial = device_info['serial_number']
                    
                    if ipv4_serial == ipv6_serial:
                        log_debug(f"Serial number match: {ipv4_serial}")
                        return True
                    else:
                        log_debug(f"Serial mismatch: IPv4={ipv4_serial}, IPv6={ipv6_serial}")
                        return False
            except Exception as e:
                log_debug(f"Serial comparison failed: {e}")
        
        # Method 2: Check if it's at least a BMC device
        try:
            response = requests.get(f"https://{ipv4_address}/redfish/v1", 
                                  verify=False, timeout=2)
            return response.status_code in [200, 401, 403]
        except:
            return False
            
    except Exception as e:
        log_debug(f"Correlation failed: {e}")
        return False

def quick_ipmi_test(ip_address):
    """Quick test to see if an IP responds to IPMI requests"""
    try:
        # Try a simple HTTPS request to see if it's a BMC
        response = requests.get(f"https://{ip_address}/redfish/v1", 
                              verify=False, timeout=2)
        return response.status_code in [200, 401, 403]  # Any of these suggest an active BMC
    except Exception:
        return False

def scan_for_ipv4_address(ipv6_address, device_info=None):
    """Scan common IP ranges to find the IPv4 address of the device"""
    try:
        log_debug(f"Scanning for IPv4 address corresponding to {ipv6_address}")
        
        # Get the MAC address from IPv6 neighbor table
        mac_address = get_mac_from_ipv6(ipv6_address)
        if mac_address:
            log_debug(f"Found MAC address {mac_address} for {ipv6_address}")
            
            # Look for this MAC in IPv4 ARP table
            ipv4_from_mac = find_ipv4_by_mac(mac_address)
            if ipv4_from_mac:
                return ipv4_from_mac
        
        # If MAC lookup fails, try scanning common IP ranges
        common_networks = [
            "192.168.1",
            "192.168.0", 
            "10.0.0",
            "172.16.1"
        ]
        
        log_debug(f"Scanning common networks: {common_networks}")
        
        for network in common_networks:
            # Scan a limited range of the network
            for i in range(100, 106):  # Only scan 100-105 to be fast
                test_ip = f"{network}.{i}"
                
                # Quick ping test
                if ping_test(test_ip):
                    # If it responds, test if it's an IPMI device
                    if test_ipmi_device(test_ip):
                        log_debug(f"Found potential IPMI device at {test_ip}")
                        return test_ip
        
        # If device info suggests specific ranges, try those too
        if device_info:
            model = device_info.get('model', '').lower()
            
            # Define common IP ranges for different server types
            ip_ranges = []
            if 'hitachi' in model or 'ha810' in model:
                ip_ranges = [
                    ("192.168.1", range(100, 106)),
                    ("192.168.0", range(100, 106))
                ]
            else:
                # Generic SMCI server ranges  
                ip_ranges = [
                    ("192.168.1", range(100, 106))
                ]
            
            # Scan each range quickly
            for network, host_range in ip_ranges:
                for host in host_range:
                    test_ip = f"{network}.{host}"
                    
                    # Quick ping test
                    if ping_test(test_ip):
                        # If it responds, test if it's an IPMI device
                        if test_ipmi_device(test_ip):
                            log_debug(f"Found potential IPMI device at {test_ip}")
                            return test_ip
        
        return None
        
    except Exception as e:
        log_debug(f"IPv4 scanning failed for {ipv6_address}: {e}")
        return None

def get_mac_from_ipv6(ipv6_address):
    """Extract MAC address from IPv6 neighbor table"""
    try:
        result = subprocess.run(['ip', '-6', 'neighbor', 'show'], 
                              capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ipv6_address.lower() in line.lower():
                    parts = line.split()
                    for part in parts:
                        # Look for MAC address format (XX:XX:XX:XX:XX:XX)
                        if ':' in part and len(part) == 17:
                            return part.lower()
        return None
    except Exception as e:
        log_debug(f"Failed to get MAC from IPv6: {e}")
        return None

def find_ipv4_by_mac(mac_address):
    """Find IPv4 address with matching MAC from ARP table"""
    try:
        result = subprocess.run(['ip', 'neighbor', 'show'], 
                              capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if mac_address.lower() in line.lower():
                    parts = line.split()
                    if len(parts) > 0 and '.' in parts[0]:
                        ipv4 = parts[0]
                        log_debug(f"Found IPv4 {ipv4} with MAC {mac_address}")
                        return ipv4
        return None
    except Exception as e:
        log_debug(f"Failed to find IPv4 by MAC: {e}")
        return None

def ping_test(ip_address):
    """Quick ping test to check if IP responds"""
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '1', ip_address], 
                              capture_output=True, timeout=2)
        return result.returncode == 0
    except Exception:
        return False

def test_ipmi_device(ip_address):
    """Test if IP address is an IPMI-enabled device"""
    try:
        import socket
        
        # Test IPMI port (623)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip_address, 623))
        sock.close()
        
        if result == 0:
            return True
            
        # Test HTTP/HTTPS management ports
        for port in [80, 443]:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            if result == 0:
                return True
                
        return False
    except Exception:
        return False

def query_server_ipv4_config(ipv6_address, device_info):
    """Query server via IPv6 to get its IPv4 configuration using iLOrest API"""
    try:
        log_debug(f"Querying IPv4 config for server {ipv6_address} using iLOrest API")
        
        # Extract IPv6 address without interface identifier for API calls
        ipv6_clean = ipv6_address.split('%')[0] if '%' in ipv6_address else ipv6_address
        
        import requests
        from requests.auth import HTTPBasicAuth
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Try iLOrest network interface API endpoints
        endpoints = [
            f"https://[{ipv6_clean}]/redfish/v1/Managers/1/EthernetInterfaces/1",
            f"https://[{ipv6_clean}]/redfish/v1/Managers/1/EthernetInterfaces/2",
            f"https://[{ipv6_clean}]/redfish/v1/Managers/1/EthernetInterfaces",
            f"https://[{ipv6_clean}]/rest/v1/Managers/1/EthernetInterfaces/1",
            f"https://[{ipv6_clean}]/rest/v1/Managers/1/EthernetInterfaces/2"
        ]
        
        for endpoint in endpoints:
            try:
                log_debug(f"Trying iLOrest endpoint: {endpoint}")
                response = requests.get(endpoint, 
                                      auth=HTTPBasicAuth('admin', 'cmb9.admin'),
                                      verify=False, timeout=5,
                                      headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    data = response.json()
                    log_debug(f"Got response from {endpoint}")
                    
                    # Check for IPv4 addresses in different response formats
                    ipv4_addresses = []
                    
                    # Format 1: Direct IPv4Addresses array
                    if 'IPv4Addresses' in data:
                        for addr in data['IPv4Addresses']:
                            if isinstance(addr, dict):
                                ip = addr.get('Address')
                                if ip and ip != '0.0.0.0' and ip != '::' and '.' in ip:
                                    log_debug(f"Found IPv4 {ip} via IPv4Addresses")
                                    return ip
                    
                    # Format 2: IPv4StaticAddresses array  
                    if 'IPv4StaticAddresses' in data:
                        for addr in data['IPv4StaticAddresses']:
                            if isinstance(addr, dict):
                                ip = addr.get('Address')
                                if ip and ip != '0.0.0.0' and ip != '::' and '.' in ip:
                                    log_debug(f"Found IPv4 {ip} via IPv4StaticAddresses")
                                    return ip
                    
                    # Format 3: Members collection (if this is a collection endpoint)
                    if 'Members' in data:
                        for member in data['Members']:
                            member_url = member.get('@odata.id', '')
                            if member_url:
                                try:
                                    member_response = requests.get(f"https://[{ipv6_clean}]{member_url}",
                                                                 auth=HTTPBasicAuth('admin', 'cmb9.admin'),
                                                                 verify=False, timeout=5)
                                    if member_response.status_code == 200:
                                        member_data = member_response.json()
                                        
                                        # Check IPv4Addresses in member
                                        if 'IPv4Addresses' in member_data:
                                            for addr in member_data['IPv4Addresses']:
                                                if isinstance(addr, dict):
                                                    ip = addr.get('Address')
                                                    if ip and ip != '0.0.0.0' and ip != '::' and '.' in ip:
                                                        log_debug(f"Found IPv4 {ip} via member IPv4Addresses")
                                                        return ip
                                        
                                        # Check IPv4StaticAddresses in member
                                        if 'IPv4StaticAddresses' in member_data:
                                            for addr in member_data['IPv4StaticAddresses']:
                                                if isinstance(addr, dict):
                                                    ip = addr.get('Address')
                                                    if ip and ip != '0.0.0.0' and ip != '::' and '.' in ip:
                                                        log_debug(f"Found IPv4 {ip} via member IPv4StaticAddresses")
                                                        return ip
                                                        
                                except Exception as e:
                                    log_debug(f"Failed to query member {member_url}: {e}")
                            
            except Exception as e:
                log_debug(f"iLOrest API query failed for {endpoint}: {e}")
                continue
        
        log_debug(f"No IPv4 address found via iLOrest API for {ipv6_address}")
        return None
                
    except Exception as e:
        log_debug(f"Server IPv4 query failed: {e}")
    
    return None

def test_device_correlation(ipv6_address, ipv4_address):
    """Test if IPv4 and IPv6 addresses belong to same device"""
    try:
        # Test if both addresses respond to common IPMI/web ports
        ipv6_responsive = test_common_ports(ipv6_address)
        ipv4_responsive = test_common_ports(ipv4_address)
        
        # If they have similar open ports, likely same device
        common_ports = set(ipv6_responsive) & set(ipv4_responsive)
        if len(common_ports) >= 1:  # At least 1 common open port
            log_debug(f"Device correlation positive: {len(common_ports)} common ports")
            return True
            
        return False
    except Exception:
        return False

def test_common_ports(address):
    """Test common ports on a device (fast version)"""
    import socket
    
    # Focus on most common IPMI/management ports
    common_ports = [623, 80, 443]  # IPMI, HTTP, HTTPS
    open_ports = []
    
    for port in common_ports:
        try:
            if ':' in address and '%' in address:  # IPv6 with interface
                # Extract IPv6 without interface for socket connection
                ipv6_addr = address.split('%')[0]
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.settimeout(0.5)  # Very short timeout
                result = sock.connect_ex((ipv6_addr, port))
            elif ':' in address:  # IPv6
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((address, port))
            else:  # IPv4
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((address, port))
            
            if result == 0:
                open_ports.append(port)
            sock.close()
        except Exception:
            continue
    
    return open_ports

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

@with_timeout(120)  # 2 minute total timeout for all servers
def discover_servers(ipv6_nodes, usernames, passwords):
    """Discover servers with improved performance and parallel processing"""
    log_debug(f"Starting server discovery for {len(ipv6_nodes)} nodes")
    servers = []
    
    # First, do a quick IPMI port scan to filter out non-server devices
    log_debug("Phase 1: Quick IPMI port filtering...")
    potential_servers = []
    for i, ipv6_node in enumerate(ipv6_nodes):
        try:
            log_debug(f"Quick check {i+1}/{len(ipv6_nodes)}: {ipv6_node}")
            if quick_ipmi_check(ipv6_node):
                potential_servers.append(ipv6_node)
                log_debug(f"Added {ipv6_node} to potential servers list")
        except Exception as e:
            log_debug(f"Quick check failed for {ipv6_node}: {e}")
            continue
    
    log_debug(f"Phase 1 complete: {len(potential_servers)} potential servers out of {len(ipv6_nodes)} IPv6 devices")
    
    # Phase 2: Detailed discovery on filtered list with reduced timeout per device
    log_debug("Phase 2: Detailed server discovery...")
    for i, ipv6_node in enumerate(potential_servers):
        try:
            log_debug(f"Processing server {i+1}/{len(potential_servers)}: {ipv6_node}")
            
            result = None
            # Try each credential combination with shorter timeout
            for username in usernames:
                for password in passwords:
                    try:
                        result = discover_server_type_fast(ipv6_node, username, password)
                        if result:
                            log_debug(f"Successfully discovered server: {result['type']}")
                            servers.append(result)
                            break  # Stop trying passwords for this node
                    except Exception as e:
                        log_debug(f"Discovery failed for {ipv6_node} with {username}: {e}")
                        continue
                        
                if result:
                    break  # Stop trying usernames for this node
            
            # If no server found, log and continue to next node
            if not result:
                log_debug(f"No server discovered at {ipv6_node}")
                
        except Exception as e:
            log_debug(f"Error processing server {ipv6_node}: {e}")
            continue
    
    log_debug(f"Total servers discovered: {len(servers)}")
    return servers

def quick_ipmi_check(ipv6_node):
    """Fast IPMI port check with very short timeout"""
    try:
        log_debug(f"Quick IPMI check for {ipv6_node}")
        addrinfo = socket.getaddrinfo(ipv6_node, 623, socket.AF_INET6, socket.SOCK_DGRAM)
        family, socktype, proto, canonname, sockaddr = addrinfo[0]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(0.5)  # Very short timeout for quick filtering
        result = sock.connect_ex(sockaddr)
        sock.close()
        is_open = result == 0
        log_debug(f"Quick IPMI check {ipv6_node}: {'PASS' if is_open else 'SKIP'}")
        return is_open
    except Exception as e:
        log_debug(f"Quick IPMI check failed for {ipv6_node}: {e}")
        return False

def discover_server_type_fast(ipv6_node, username, password):
    """Fast server discovery with reduced timeouts"""
    log_debug(f"Fast server discovery for {ipv6_node} with username {username}")
    
    # Set up Redfish API URL 
    redfish_api = f'https://[{ipv6_node.replace("%", "%25")}]/redfish/v1/Systems/'
    redfish_header = {
        'Content-Type': 'application/json',
        'User-Agent': 'curl/7.54.0',
        'Host': f'[{ipv6_node.split("%")[0]}]'
    }
    
    try:
        log_debug(f"Attempting fast Redfish connection to {redfish_api}1")
        # Connect with shorter timeout
        session = requests.get(f'{redfish_api}1', 
                             auth=(username, password), 
                             verify=False,
                             headers=redfish_header, 
                             timeout=3)  # Reduced from 10 to 3 seconds
        
        log_debug(f"Redfish response status: {session.status_code}")
        
        if not session.ok:
            log_debug(f"Failed to connect to Redfish on {ipv6_node}")
            return None
            
        j = session.json()
        sku = j.get('SKU', '')
        model = j.get('Model', '')
        serial = j.get('SerialNumber', '')
        
        log_debug(f"Server info - SKU: {sku}, Model: {model}, Serial: {serial}")
        
        # Determine server type based on SKU/Model - expanded detection
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
        elif 'DS120' in model and 'G6' in model:
            server_type = 'DS120_G6'
        elif 'DS120' in model:
            server_type = 'DS120_G6'  # Default DS120 to G6
        elif 'SuperServer' in model:
            server_type = 'SuperServer'
        elif model and model != 'Unknown':
            server_type = f"Server_{model.replace(' ', '_')}"
        
        log_debug(f"Identified server type: {server_type}")
        
        # Fast IPv4 resolution - only try the most reliable methods
        device_info = {
            'model': model,
            'sku': sku,
            'type': server_type
        }
        ipv4_address = resolve_ipv4_address(ipv6_node, device_info)
        
        if ipv4_address:
            log_debug(f"Resolved IPv4 address {ipv4_address} for server {ipv6_node}")
        else:
            log_debug(f"Could not resolve IPv4 address for server {ipv6_node}")
        
        return {
            'type': server_type,
            'host': ipv6_node,
            'username': username,
            'password': password,
            'model': model,
            'sku': sku,
            'serial_number': serial,
            'ipv4_address': ipv4_address
        }
        
    except Exception as e:
        log_debug(f"Exception during fast server discovery for {ipv6_node}: {e}")
        return None

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

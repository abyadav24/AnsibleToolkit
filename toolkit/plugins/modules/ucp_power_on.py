#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ucp_power_on
short_description: Power on servers using iLO REST API
version_added: "1.0.0"
description:
- This module powers on servers by connecting to their iLO management interface
- Reads server credentials from a CSV file
- Uses iLO REST commands to power on the servers

options:
    servers_csv:
        description:
        - Path to CSV file containing server details (ipaddress, username, password)
        required: true
        type: str
    ilorest_path:
        description:
        - Path to ilorest executable
        required: false
        default: "ilorest"
        type: str

author:
    - Ansible Toolkit Team
'''

EXAMPLES = r'''
- name: Power on all servers
  ucp_power_on:
    servers_csv: "/path/to/servers.csv"
    ilorest_path: "/usr/bin/ilorest"
'''

RETURN = r'''
powered_on_servers:
    description: List of servers that were powered on
    type: list
    returned: always
    sample: ["10.1.1.1", "10.1.1.2"]
failed_servers:
    description: List of servers that failed to power on
    type: list
    returned: always
    sample: []
'''

import csv
import subprocess
import os
from ansible.module_utils.basic import AnsibleModule


def read_servers_csv(csv_file):
    """Read server details from CSV file"""
    servers = []
    try:
        with open(csv_file, 'r') as file:
            # Use the actual field names from the CSV file
            reader = csv.DictReader(file, delimiter=',')
            for row in reader:
                # Store both IPv6 and IPv4 for fallback support
                server_info = {
                    'ipaddress': row['Host'].strip(),  # IPv6 Host field (primary)
                    'ipv4_fallback': row['IPv4 Address'].strip(),  # IPv4 fallback
                    'username': row['Username'].strip(),
                    'password': row['Password'].strip()
                }
                servers.append(server_info)
        return servers, None
    except Exception as e:
        return None, str(e)


def power_on_server(server, ilorest_path):
    """Power on a single server using iLO REST with IPv6/IPv4 fallback"""
    try:
        ipaddress = server['ipaddress']
        ipv4_fallback = server.get('ipv4_fallback', '')
        username = server['username']
        password = server['password']
        
        # Try IPv6 first
        login_cmd = [ilorest_path, 'login', ipaddress, '-u', username, '-p', password]
        result = subprocess.run(login_cmd, capture_output=True, text=True, shell=False)
        
        # If IPv6 fails and we have IPv4 fallback, try IPv4
        if result.returncode != 0 and ipv4_fallback:
            login_cmd = [ilorest_path, 'login', ipv4_fallback, '-u', username, '-p', password]
            result = subprocess.run(login_cmd, capture_output=True, text=True, shell=False)
            if result.returncode == 0:
                ipaddress = ipv4_fallback  # Use IPv4 for power commands
        
        if result.returncode != 0:
            return False, f"Login failed (tried IPv6 and IPv4): {result.stderr}"
        
        # Power on command  
        power_cmd = [ilorest_path, 'reboot', 'On']
        result = subprocess.run(power_cmd, capture_output=True, text=True, shell=False)
        
        # Always attempt logout (even if power command fails)
        logout_cmd = [ilorest_path, 'logout']
        logout_result = subprocess.run(logout_cmd, capture_output=True, text=True, shell=False)
        
        if result.returncode != 0:
            return False, f"Power on failed: {result.stderr}"
        
        # Verify the power operation was initiated successfully
        stdout_lower = result.stdout.lower()
        if "powering on" in stdout_lower or "operation completed successfully" in stdout_lower:
            return True, f"Successfully initiated power on for {ipaddress} - Server is powering on"
        elif result.returncode == 0:
            return True, f"Power on command completed for {ipaddress}"
        else:
            return False, f"Power on command failed with output: {result.stdout}"
        
    except Exception as e:
        return False, str(e)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers_csv=dict(required=False, type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
            target_nodes=dict(required=False, default=[], type='list'),
            use_target_nodes=dict(required=False, default=False, type='bool'),
        ),
        supports_check_mode=True,
    )

    servers_csv = module.params['servers_csv']
    ilorest_path = module.params['ilorest_path']
    target_nodes = module.params['target_nodes']
    use_target_nodes = module.params['use_target_nodes']

    servers = []
    
    if use_target_nodes and target_nodes:
        # Use target nodes from configuration
        if servers_csv:
            # Try to get credentials from CSV if available
            csv_servers, csv_error = read_servers_csv(servers_csv)
            if not csv_error and csv_servers:
                default_creds = csv_servers[0]
                username = default_creds['username']
                password = default_creds['password']
                ipv4_fallback = default_creds.get('ipv4_fallback', '')
            else:
                # Use default credentials
                username = 'admin'
                password = 'cmb9.admin'
                ipv4_fallback = ''
        else:
            # Use default credentials when no CSV provided
            username = 'admin'
            password = 'cmb9.admin'
            ipv4_fallback = ''
            
        for node in target_nodes:
            server_info = {
                'ipaddress': node.strip(),  # Target node (likely IPv6)
                'ipv4_fallback': ipv4_fallback,
                'username': username,
                'password': password
            }
            servers.append(server_info)
    else:
        # Read servers from CSV normally
        if not servers_csv:
            module.fail_json(msg="servers_csv is required when use_target_nodes is False")
        servers, error = read_servers_csv(servers_csv)
        if error:
            module.fail_json(msg=f"Failed to read servers CSV: {error}")

    if module.check_mode:
        module.exit_json(changed=True, 
                        msg=f"Would power on {len(servers)} servers")

    powered_on_servers = []
    failed_servers = []

    # Power on each server
    for server in servers:
        success, message = power_on_server(server, ilorest_path)
        if success:
            powered_on_servers.append(server['ipaddress'])
        else:
            failed_servers.append({
                'ipaddress': server['ipaddress'],
                'error': message
            })

    # Determine if changes were made
    changed = len(powered_on_servers) > 0

    result = {
        'changed': changed,
        'powered_on_servers': powered_on_servers,
        'failed_servers': failed_servers,
        'msg': f"Powered on {len(powered_on_servers)} servers, {len(failed_servers)} failed"
    }

    if failed_servers and not powered_on_servers:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()

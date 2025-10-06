#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: server_status_checker
short_description: Check server status and connectivity
version_added: "1.0.0"
description:
- This module checks server connectivity and basic status
- Validates iLO access and server responsiveness
- Provides health check capabilities for server management

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
    timeout:
        description:
        - Timeout for connectivity checks in seconds
        required: false
        default: 30
        type: int

author:
    - Ansible Toolkit Team
'''

EXAMPLES = r'''
- name: Check server status
  server_status_checker:
    servers_csv: "/path/to/servers.csv"
    timeout: 30
'''

RETURN = r'''
accessible_servers:
    description: List of servers that are accessible
    type: list
    returned: always
    sample: ["10.1.1.1", "10.1.1.2"]
inaccessible_servers:
    description: List of servers that are not accessible
    type: list
    returned: always
    sample: []
server_details:
    description: Detailed status for each server
    type: dict
    returned: always
    sample: {"10.1.1.1": {"status": "accessible", "model": "HA810", "power_state": "On"}}
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
            reader = csv.DictReader(file, delimiter=',', 
                                  fieldnames=['ipaddress', 'username', 'password'])
            next(reader)  # Skip header
            for row in reader:
                servers.append(row)
        return servers, None
    except Exception as e:
        return None, str(e)


def check_server_status(server, ilorest_path, timeout):
    """Check status of a single server"""
    try:
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        
        # Login command with timeout
        login_cmd = [ilorest_path, 'login', ipaddress, '-u', username, '-p', password]
        result = subprocess.run(login_cmd, capture_output=True, text=True, 
                              shell=False, timeout=timeout)
        
        if result.returncode != 0:
            return {
                'status': 'inaccessible',
                'error': f"Login failed: {result.stderr}",
                'model': 'Unknown',
                'power_state': 'Unknown'
            }
        
        # Get server info if login successful
        info_cmd = [ilorest_path, 'serverstatus']
        info_result = subprocess.run(info_cmd, capture_output=True, text=True,
                                   shell=False, timeout=timeout)
        
        # Parse basic info from output
        model = 'Unknown'
        power_state = 'Unknown'
        
        if info_result.returncode == 0:
            output = info_result.stdout
            # Basic parsing - adjust based on actual ilorest output format
            for line in output.split('\n'):
                if 'Model' in line:
                    model = line.split(':')[-1].strip() if ':' in line else 'Unknown'
                elif 'Power' in line or 'State' in line:
                    power_state = line.split(':')[-1].strip() if ':' in line else 'Unknown'
        
        return {
            'status': 'accessible',
            'error': None,
            'model': model,
            'power_state': power_state
        }
        
    except subprocess.TimeoutExpired:
        return {
            'status': 'timeout',
            'error': 'Connection timed out',
            'model': 'Unknown',
            'power_state': 'Unknown'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'model': 'Unknown',
            'power_state': 'Unknown'
        }


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers_csv=dict(required=True, type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
            timeout=dict(required=False, default=30, type='int'),
        ),
        supports_check_mode=True,
    )

    servers_csv = module.params['servers_csv']
    ilorest_path = module.params['ilorest_path']
    timeout = module.params['timeout']

    # Read servers from CSV
    servers, error = read_servers_csv(servers_csv)
    if error:
        module.fail_json(msg=f"Failed to read servers CSV: {error}")

    if module.check_mode:
        module.exit_json(changed=False, 
                        msg=f"Would check status of {len(servers)} servers")

    accessible_servers = []
    inaccessible_servers = []
    server_details = {}

    # Check status of each server
    for server in servers:
        status_info = check_server_status(server, ilorest_path, timeout)
        server_ip = server['ipaddress']
        
        server_details[server_ip] = status_info
        
        if status_info['status'] == 'accessible':
            accessible_servers.append(server_ip)
        else:
            inaccessible_servers.append({
                'ipaddress': server_ip,
                'error': status_info['error']
            })

    result = {
        'changed': False,
        'accessible_servers': accessible_servers,
        'inaccessible_servers': inaccessible_servers,
        'server_details': server_details,
        'msg': f"Checked {len(servers)} servers: {len(accessible_servers)} accessible, {len(inaccessible_servers)} inaccessible"
    }

    module.exit_json(**result)


if __name__ == '__main__':
    main()

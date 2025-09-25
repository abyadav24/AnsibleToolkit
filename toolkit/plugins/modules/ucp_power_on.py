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
            reader = csv.DictReader(file, delimiter=',', 
                                  fieldnames=['ipaddress', 'username', 'password'])
            next(reader)  # Skip header
            for row in reader:
                servers.append(row)
        return servers, None
    except Exception as e:
        return None, str(e)


def power_on_server(server, ilorest_path):
    """Power on a single server using iLO REST"""
    try:
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        
        # Login command
        login_cmd = [ilorest_path, 'login', ipaddress, '-u', username, '-p', password]
        result = subprocess.run(login_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"Login failed: {result.stderr}"
        
        # Power on command
        power_cmd = [ilorest_path, 'reboot', 'on']
        result = subprocess.run(power_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"Power on failed: {result.stderr}"
            
        return True, "Successfully powered on"
        
    except Exception as e:
        return False, str(e)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers_csv=dict(required=True, type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
        ),
        supports_check_mode=True,
    )

    servers_csv = module.params['servers_csv']
    ilorest_path = module.params['ilorest_path']

    # Read servers from CSV
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

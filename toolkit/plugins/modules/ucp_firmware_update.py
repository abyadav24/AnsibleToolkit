#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ucp_firmware_update
short_description: Update firmware on servers using iLO REST API
version_added: "1.0.0"
description:
- This module updates firmware on servers by connecting to their iLO management interface
- Reads server credentials from a CSV file
- Uses iLO REST commands to perform firmware updates
- Supports web server management for hosting firmware files

options:
    servers_csv:
        description:
        - Path to CSV file containing server details (ipaddress, username, password)
        required: true
        type: str
    firmware_url:
        description:
        - URL of the firmware binary file
        required: true
        type: str
    ilorest_path:
        description:
        - Path to ilorest executable
        required: false
        default: "ilorest"
        type: str
    manage_nginx:
        description:
        - Whether to manage nginx web server for firmware hosting
        required: false
        default: true
        type: bool

author:
    - Ansible Toolkit Team
'''

EXAMPLES = r'''
- name: Update firmware on all servers
  ucp_firmware_update:
    servers_csv: "/path/to/servers.csv"
    firmware_url: "http://10.1.1.100:8080/firmware.bin"
    manage_nginx: true
'''

RETURN = r'''
updated_servers:
    description: List of servers that were updated successfully
    type: list
    returned: always
    sample: ["10.1.1.1", "10.1.1.2"]
failed_servers:
    description: List of servers where firmware update failed
    type: list
    returned: always
    sample: []
'''

import csv
import subprocess
import os
import time
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


def manage_nginx_server(action):
    """Start or stop nginx server"""
    try:
        if action == "start":
            result = subprocess.run(['nginx'], capture_output=True, text=True, shell=False)
            return True, "Nginx started"
        elif action == "stop":
            result = subprocess.run(['pkill', 'nginx'], capture_output=True, text=True, shell=False)
            return True, "Nginx stopped"
    except Exception as e:
        return False, str(e)


def update_firmware_on_server(server, firmware_url, ilorest_path):
    """Update firmware on a single server using iLO REST"""
    try:
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        
        # Login command
        login_cmd = [ilorest_path, 'login', ipaddress, '-u', username, '-p', password]
        result = subprocess.run(login_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"Login failed: {result.stderr}"
        
        # Firmware update command
        update_cmd = [ilorest_path, 'firmwareupdate', firmware_url]
        result = subprocess.run(update_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"Firmware update failed: {result.stderr}"
            
        return True, "Successfully updated firmware"
        
    except Exception as e:
        return False, str(e)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers_csv=dict(required=True, type='str'),
            firmware_url=dict(required=True, type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
            manage_nginx=dict(required=False, default=True, type='bool'),
        ),
        supports_check_mode=True,
    )

    servers_csv = module.params['servers_csv']
    firmware_url = module.params['firmware_url']
    ilorest_path = module.params['ilorest_path']
    manage_nginx = module.params['manage_nginx']

    # Read servers from CSV
    servers, error = read_servers_csv(servers_csv)
    if error:
        module.fail_json(msg=f"Failed to read servers CSV: {error}")

    if module.check_mode:
        module.exit_json(changed=True, 
                        msg=f"Would update firmware on {len(servers)} servers")

    # Start nginx if requested
    if manage_nginx:
        success, msg = manage_nginx_server("start")
        if not success:
            module.warn(f"Failed to start nginx: {msg}")

    updated_servers = []
    failed_servers = []

    try:
        # Update firmware on each server
        for server in servers:
            success, message = update_firmware_on_server(server, firmware_url, ilorest_path)
            if success:
                updated_servers.append(server['ipaddress'])
            else:
                failed_servers.append({
                    'ipaddress': server['ipaddress'],
                    'error': message
                })
    finally:
        # Stop nginx if we started it
        if manage_nginx:
            time.sleep(2)  # Give some time for operations to complete
            manage_nginx_server("stop")

    # Determine if changes were made
    changed = len(updated_servers) > 0

    result = {
        'changed': changed,
        'updated_servers': updated_servers,
        'failed_servers': failed_servers,
        'msg': f"Updated firmware on {len(updated_servers)} servers, {len(failed_servers)} failed"
    }

    if failed_servers and not updated_servers:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()

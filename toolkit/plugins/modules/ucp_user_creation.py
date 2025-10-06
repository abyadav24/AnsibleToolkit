#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ucp_user_creation
short_description: Create admin users on servers using iLO REST API
version_added: "1.0.0"
description:
- This module creates new admin users on servers by connecting to their iLO management interface
- Reads server credentials from a CSV file
- Uses iLO REST commands to create new admin accounts

options:
    servers_csv:
        description:
        - Path to CSV file containing server details (ipaddress, username, password)
        required: true
        type: str
    new_username:
        description:
        - Username for the new admin account
        required: false
        default: "admin"
        type: str
    new_password:
        description:
        - Password for the new admin account
        required: false
        default: "cmb9.admin"
        type: str
    user_role:
        description:
        - Role for the new admin account
        required: false
        default: "Administrator"
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
- name: Create admin users on all servers
  ucp_user_creation:
    servers_csv: "/path/to/servers.csv"
    new_username: "admin"
    new_password: "cmb9.admin"
    user_role: "Administrator"
'''

RETURN = r'''
created_users:
    description: List of servers where users were created successfully
    type: list
    returned: always
    sample: ["10.1.1.1", "10.1.1.2"]
failed_servers:
    description: List of servers where user creation failed
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


def create_user_on_server(server, new_username, new_password, user_role, ilorest_path):
    """Create a new admin user on a single server using iLO REST"""
    try:
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        
        # Create user command with all parameters
        cmd = [
            ilorest_path, 'iloaccounts', 'add', 
            new_username, new_username, new_password,
            '--role=' + user_role,
            '--url', ipaddress,
            '-u', username,
            '-p', password
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"User creation failed: {result.stderr}"
            
        return True, "Successfully created user"
        
    except Exception as e:
        return False, str(e)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers_csv=dict(required=True, type='str'),
            new_username=dict(required=False, default='admin', type='str'),
            new_password=dict(required=False, default='cmb9.admin', type='str', no_log=True),
            user_role=dict(required=False, default='Administrator', type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
        ),
        supports_check_mode=True,
    )

    servers_csv = module.params['servers_csv']
    new_username = module.params['new_username']
    new_password = module.params['new_password']
    user_role = module.params['user_role']
    ilorest_path = module.params['ilorest_path']

    # Read servers from CSV
    servers, error = read_servers_csv(servers_csv)
    if error:
        module.fail_json(msg=f"Failed to read servers CSV: {error}")

    if module.check_mode:
        module.exit_json(changed=True, 
                        msg=f"Would create user '{new_username}' on {len(servers)} servers")

    created_users = []
    failed_servers = []

    # Create user on each server
    for server in servers:
        success, message = create_user_on_server(
            server, new_username, new_password, user_role, ilorest_path
        )
        if success:
            created_users.append(server['ipaddress'])
        else:
            failed_servers.append({
                'ipaddress': server['ipaddress'],
                'error': message
            })

    # Determine if changes were made
    changed = len(created_users) > 0

    result = {
        'changed': changed,
        'created_users': created_users,
        'failed_servers': failed_servers,
        'msg': f"Created user on {len(created_users)} servers, {len(failed_servers)} failed"
    }

    if failed_servers and not created_users:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()

#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ucp_bios_save
short_description: Save BIOS settings from servers using iLO REST API
version_added: "1.0.0"
description:
- This module saves BIOS settings from servers by connecting to their iLO management interface
- Uses iLO REST commands to export BIOS configuration to JSON files
- Can save settings from a single server or multiple servers from CSV

options:
    ilo_ip:
        description:
        - IP address of the iLO (use [IPv6] format for IPv6)
        required: false
        type: str
    ilo_username:
        description:
        - Username for iLO authentication
        required: false
        type: str
    ilo_password:
        description:
        - Password for iLO authentication
        required: false
        type: str
        no_log: true
    servers_csv:
        description:
        - Path to CSV file containing server details (alternative to individual server)
        required: false
        type: str
    output_directory:
        description:
        - Directory to save BIOS configuration files
        required: false
        default: "."
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
- name: Save BIOS settings from single server
  ucp_bios_save:
    ilo_ip: "10.1.1.10"
    ilo_username: "admin"
    ilo_password: "password"
    output_directory: "/tmp/bios_configs"

- name: Save BIOS settings from multiple servers
  ucp_bios_save:
    servers_csv: "/path/to/servers.csv"
    output_directory: "/tmp/bios_configs"
'''

RETURN = r'''
saved_configs:
    description: List of servers where BIOS settings were saved successfully
    type: list
    returned: always
    sample: ["10.1.1.1", "10.1.1.2"]
failed_servers:
    description: List of servers where BIOS save failed
    type: list
    returned: always
    sample: []
config_files:
    description: List of created configuration files
    type: list
    returned: always
    sample: ["10.1.1.1_ilorest.json", "10.1.1.2_ilorest.json"]
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


def generate_filename(ilo_ip):
    """Generate output filename based on IP address"""
    file_base = ilo_ip
    if "[" in file_base:  # IPv6 format
        ipv6 = ilo_ip[1:-1]
        file_base = ipv6.split(":")[-1]
    return f"{file_base}_ilorest.json"


def save_bios_config(ilo_ip, ilo_username, ilo_password, output_directory, ilorest_path):
    """Save BIOS configuration from a single server"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)
        
        # Generate output filename
        filename = generate_filename(ilo_ip)
        output_file = os.path.join(output_directory, filename)
        
        # Save BIOS command
        cmd = [
            ilorest_path, 'save', '--select', 'Bios.',
            '--url', ilo_ip,
            '-u', ilo_username,
            '-p', ilo_password,
            '-f', output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"BIOS save failed: {result.stderr}", None
            
        return True, "Successfully saved BIOS configuration", filename
        
    except Exception as e:
        return False, str(e), None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            ilo_ip=dict(required=False, type='str'),
            ilo_username=dict(required=False, type='str'),
            ilo_password=dict(required=False, type='str', no_log=True),
            servers_csv=dict(required=False, type='str'),
            output_directory=dict(required=False, default='.', type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
        ),
        required_one_of=[
            ('ilo_ip', 'servers_csv'),
        ],
        required_together=[
            ('ilo_ip', 'ilo_username', 'ilo_password'),
        ],
        supports_check_mode=True,
    )

    ilo_ip = module.params['ilo_ip']
    ilo_username = module.params['ilo_username']
    ilo_password = module.params['ilo_password']
    servers_csv = module.params['servers_csv']
    output_directory = module.params['output_directory']
    ilorest_path = module.params['ilorest_path']

    servers = []
    
    # Determine input method
    if ilo_ip:
        servers = [{'ipaddress': ilo_ip, 'username': ilo_username, 'password': ilo_password}]
    else:
        servers, error = read_servers_csv(servers_csv)
        if error:
            module.fail_json(msg=f"Failed to read servers CSV: {error}")

    if module.check_mode:
        module.exit_json(changed=False, 
                        msg=f"Would save BIOS configuration from {len(servers)} servers")

    saved_configs = []
    failed_servers = []
    config_files = []

    # Save BIOS configuration from each server
    for server in servers:
        success, message, filename = save_bios_config(
            server['ipaddress'], 
            server['username'], 
            server['password'], 
            output_directory, 
            ilorest_path
        )
        
        if success:
            saved_configs.append(server['ipaddress'])
            if filename:
                config_files.append(filename)
        else:
            failed_servers.append({
                'ipaddress': server['ipaddress'],
                'error': message
            })

    # Determine if changes were made
    changed = len(saved_configs) > 0

    result = {
        'changed': changed,
        'saved_configs': saved_configs,
        'failed_servers': failed_servers,
        'config_files': config_files,
        'msg': f"Saved BIOS config from {len(saved_configs)} servers, {len(failed_servers)} failed"
    }

    if failed_servers and not saved_configs:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()

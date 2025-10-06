#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ucp_mount_reboot
short_description: Mount ISO and reboot servers using iLO REST API
version_added: "1.0.0"
description:
- This module mounts ISO files and reboots servers using iLO management interface
- Reads server credentials from a CSV file
- Uses iLO REST commands to mount virtual media and reboot
- Supports web server management for hosting ISO files

options:
    servers_csv:
        description:
        - Path to CSV file containing server details (ipaddress, username, password)
        required: true
        type: str
    iso_url:
        description:
        - URL of the ISO file to mount
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
        - Whether to manage nginx web server for ISO hosting
        required: false
        default: true
        type: bool
    sleep_duration:
        description:
        - Time to sleep after operations (in seconds)
        required: false
        default: 1800
        type: int

author:
    - Ansible Toolkit Team
'''

EXAMPLES = r'''
- name: Mount ISO and reboot all servers
  ucp_mount_reboot:
    servers_csv: "/path/to/servers.csv"
    iso_url: "http://10.1.1.100:8080/installer.iso"
    manage_nginx: true
    sleep_duration: 1800
'''

RETURN = r'''
mounted_servers:
    description: List of servers where ISO was mounted and rebooted successfully
    type: list
    returned: always
    sample: ["10.1.1.1", "10.1.1.2"]
failed_servers:
    description: List of servers where mounting/reboot failed
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


def mount_and_reboot_server(server, iso_url, ilorest_path):
    """Mount ISO and reboot a single server using iLO REST"""
    try:
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        
        # Login command
        login_cmd = [ilorest_path, 'login', ipaddress, '-u', username, '-p', password]
        result = subprocess.run(login_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"Login failed: {result.stderr}"
        
        # Remove existing virtual media
        remove_cmd = [ilorest_path, 'virtualmedia', '2', '--remove']
        subprocess.run(remove_cmd, capture_output=True, text=True, shell=False)
        
        # Mount new ISO with boot next reset
        mount_cmd = [ilorest_path, 'virtualmedia', '2', iso_url, '--bootnextreset']
        result = subprocess.run(mount_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"ISO mount failed: {result.stderr}"
        
        # Reboot server
        reboot_cmd = [ilorest_path, 'reboot']
        result = subprocess.run(reboot_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"Reboot failed: {result.stderr}"
            
        return True, "Successfully mounted ISO and rebooted"
        
    except Exception as e:
        return False, str(e)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers_csv=dict(required=True, type='str'),
            iso_url=dict(required=True, type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
            manage_nginx=dict(required=False, default=True, type='bool'),
            sleep_duration=dict(required=False, default=1800, type='int'),
        ),
        supports_check_mode=True,
    )

    servers_csv = module.params['servers_csv']
    iso_url = module.params['iso_url']
    ilorest_path = module.params['ilorest_path']
    manage_nginx = module.params['manage_nginx']
    sleep_duration = module.params['sleep_duration']

    # Read servers from CSV
    servers, error = read_servers_csv(servers_csv)
    if error:
        module.fail_json(msg=f"Failed to read servers CSV: {error}")

    if module.check_mode:
        module.exit_json(changed=True, 
                        msg=f"Would mount ISO and reboot {len(servers)} servers")

    # Stop any existing nginx instances
    if manage_nginx:
        manage_nginx_server("stop")
        time.sleep(3)
        
        # Start nginx
        success, msg = manage_nginx_server("start")
        if not success:
            module.warn(f"Failed to start nginx: {msg}")

    mounted_servers = []
    failed_servers = []

    try:
        # Mount and reboot each server
        for server in servers:
            success, message = mount_and_reboot_server(server, iso_url, ilorest_path)
            if success:
                mounted_servers.append(server['ipaddress'])
            else:
                failed_servers.append({
                    'ipaddress': server['ipaddress'],
                    'error': message
                })

        # Sleep for specified duration
        if sleep_duration > 0:
            time.sleep(sleep_duration)
            
    finally:
        # Stop nginx if we started it
        if manage_nginx:
            manage_nginx_server("stop")

    # Determine if changes were made
    changed = len(mounted_servers) > 0

    result = {
        'changed': changed,
        'mounted_servers': mounted_servers,
        'failed_servers': failed_servers,
        'msg': f"Mounted ISO and rebooted {len(mounted_servers)} servers, {len(failed_servers)} failed"
    }

    if failed_servers and not mounted_servers:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()

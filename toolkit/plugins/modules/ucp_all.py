#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ucp_all
short_description: Complete UCP setup for HA nodes including BIOS, SPV, and OS installation
version_added: "1.0.0"
description:
- This module performs comprehensive setup for HA nodes
- Applies BIOS templates based on server model and solution type
- Mounts and boots from SPV images
- Handles both UCP VMware and Azure Stack HCI configurations
- Supports VSSB server setup

options:
    servers_csv:
        description:
        - Path to CSV file containing server details (ipaddress, username, password, model)
        required: true
        type: str
    solution_type:
        description:
        - Type of solution (1 for UCP VMware, 9 for Azure Stack HCI, 10 for VSSB)
        required: true
        choices: ["1", "9", "10"]
        type: str
    spv_url_g2:
        description:
        - SPV Image URL for HA G2 nodes
        required: true
        type: str
    spv_url_g3:
        description:
        - SPV Image URL for HA G3 nodes
        required: true
        type: str
    kickstart_url:
        description:
        - Kickstart ISO URL (ESXi 8.0 for solution 1, Azure Stack HCI for solution 9, SUSE for solution 10)
        required: true
        type: str
    templates_directory:
        description:
        - Directory containing BIOS template files
        required: false
        default: "./HA-G2-G3BiosTemplates"
        type: str
    ilorest_path:
        description:
        - Path to ilorest executable
        required: false
        default: "ilorest"
        type: str
    manage_nginx:
        description:
        - Whether to manage nginx web server
        required: false
        default: true
        type: bool
    skip_bios_reboot:
        description:
        - Skip reboot after BIOS template application
        required: false
        default: false
        type: bool

author:
    - Ansible Toolkit Team
'''

EXAMPLES = r'''
- name: Setup UCP VMware environment
  ucp_all:
    servers_csv: "/path/to/servers.csv"
    solution_type: "1"
    spv_url_g2: "http://10.1.1.100:8080/spv_g2.iso"
    spv_url_g3: "http://10.1.1.100:8080/spv_g3.iso"
    kickstart_url: "http://10.1.1.100:8080/esxi80.iso"

- name: Setup Azure Stack HCI environment
  ucp_all:
    servers_csv: "/path/to/servers.csv"
    solution_type: "9"
    spv_url_g2: "http://10.1.1.100:8080/spv_g2.iso"
    spv_url_g3: "http://10.1.1.100:8080/spv_g3.iso"
    kickstart_url: "http://10.1.1.100:8080/azureshci.iso"
'''

RETURN = r'''
configured_servers:
    description: List of servers that were configured successfully
    type: list
    returned: always
    sample: ["10.1.1.1", "10.1.1.2"]
failed_servers:
    description: List of servers that failed configuration
    type: list
    returned: always
    sample: []
bios_templates_applied:
    description: Mapping of servers to their applied BIOS templates
    type: dict
    returned: always
    sample: {"10.1.1.1": "HA_G2_Intel_HA810_HA820_G2.json"}
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
                                  fieldnames=['ipaddress', 'username', 'password', 'model'])
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
            subprocess.run(['nginx'], capture_output=True, text=True, shell=False)
            return True, "Nginx started"
        elif action == "stop":
            subprocess.run(['pkill', 'nginx'], capture_output=True, text=True, shell=False)
            return True, "Nginx stopped"
    except Exception as e:
        return False, str(e)


def get_bios_template_for_solution(model, solution_type, templates_directory):
    """Get appropriate BIOS template based on server model and solution type"""
    template_mappings = {
        "1": {  # UCP VMware
            "default": "HA_G2_Intel_HA810_HA820_G2.json",
            "Hitachi Advanced Server HA805 G3": "HA_G3_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA815 G3": "HA_G3_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA825 G3": "HA_G3_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA810 G3": "HA_G3_Intel_HA810_HA820_G3.json",
            "Hitachi Advanced Server HA820 G3": "HA_G3_Intel_HA810_HA820_G3.json",
            "Hitachi Advanced Server HA840 G3": "HA_G3_HA840_G3.json",
        },
        "9": {  # Azure Stack HCI
            "default": "HA_G2_ASHCI.bios.json",
            "Hitachi Advanced Server HA805 G3": "HA_G3_ASHCI_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA815 G3": "HA_G3_ASHCI_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA825 G3": "HA_G3_ASHCI_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA810 G3": "HA_G3_ASHCI.bios.json",
            "Hitachi Advanced Server HA820 G3": "HA_G3_ASHCI.bios.json",
            "Hitachi Advanced Server HA840 G3": "HA_G3_ASHCI.bios.json",
        },
        "10": {  # VSSB Servers
            "default": "step1_ilorest.json",
            "step2": "step2_ilorest.json",
        }
    }
    
    template_name = template_mappings.get(solution_type, {}).get(model, 
                                                               template_mappings[solution_type]["default"])
    return os.path.join(templates_directory, template_name)


def get_spv_url_for_server(model, spv_url_g2, spv_url_g3):
    """Get appropriate SPV URL based on server model generation"""
    if 'G2' in model:
        return spv_url_g2
    elif 'G3' in model:
        return spv_url_g3
    else:
        return spv_url_g2  # Default to G2


def execute_command_safely(cmd, server_ip, description=""):
    """Execute command with error handling"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"{description} failed: {result.stderr}"
        return True, f"{description} successful"
    except Exception as e:
        return False, f"{description} exception: {str(e)}"


def configure_server_complete(server, solution_type, spv_url_g2, spv_url_g3, kickstart_url,
                            templates_directory, ilorest_path, skip_bios_reboot):
    """Complete configuration of a single server"""
    try:
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        model = server.get('model', 'Unknown')
        
        # Step 1: Login
        login_cmd = f'{ilorest_path} login {ipaddress} -u {username} -p {password}'
        success, message = execute_command_safely(login_cmd, ipaddress, "Login")
        if not success:
            return False, message, None
        
        # Step 2: Apply BIOS template
        template_file = get_bios_template_for_solution(model, solution_type, templates_directory)
        if not os.path.exists(template_file):
            return False, f"Template file not found: {template_file}", None
        
        bios_cmd = f'{ilorest_path} load -f {template_file}'
        success, message = execute_command_safely(bios_cmd, ipaddress, "BIOS template load")
        if not success:
            return False, message, template_file
        
        time.sleep(5)  # Wait after BIOS template application
        
        # Step 3: Reboot after BIOS (if not skipped)
        if not skip_bios_reboot:
            reboot_cmd = f'{ilorest_path} reboot'
            success, message = execute_command_safely(reboot_cmd, ipaddress, "BIOS reboot")
            if not success:
                return False, message, template_file
        
        # Step 4: Remove existing virtual media
        remove_media_cmd = f'{ilorest_path} virtualmedia 2 --remove'
        execute_command_safely(remove_media_cmd, ipaddress, "Remove virtual media")
        
        # Step 5: Mount SPV image
        spv_url = get_spv_url_for_server(model, spv_url_g2, spv_url_g3)
        mount_spv_cmd = f'{ilorest_path} virtualmedia 2 {spv_url} --bootnextreset'
        success, message = execute_command_safely(mount_spv_cmd, ipaddress, "Mount SPV")
        if not success:
            return False, message, template_file
        
        # Step 6: Final reboot to boot from SPV
        final_reboot_cmd = f'{ilorest_path} reboot'
        success, message = execute_command_safely(final_reboot_cmd, ipaddress, "Final reboot")
        if not success:
            return False, message, template_file
        
        return True, "Complete configuration successful", os.path.basename(template_file)
        
    except Exception as e:
        return False, str(e), None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers_csv=dict(required=True, type='str'),
            solution_type=dict(required=True, choices=['1', '9', '10'], type='str'),
            spv_url_g2=dict(required=True, type='str'),
            spv_url_g3=dict(required=True, type='str'),
            kickstart_url=dict(required=True, type='str'),
            templates_directory=dict(required=False, default='./HA-G2-G3BiosTemplates', type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
            manage_nginx=dict(required=False, default=True, type='bool'),
            skip_bios_reboot=dict(required=False, default=False, type='bool'),
        ),
        supports_check_mode=True,
    )

    servers_csv = module.params['servers_csv']
    solution_type = module.params['solution_type']
    spv_url_g2 = module.params['spv_url_g2']
    spv_url_g3 = module.params['spv_url_g3']
    kickstart_url = module.params['kickstart_url']
    templates_directory = module.params['templates_directory']
    ilorest_path = module.params['ilorest_path']
    manage_nginx = module.params['manage_nginx']
    skip_bios_reboot = module.params['skip_bios_reboot']

    # Read servers from CSV
    servers, error = read_servers_csv(servers_csv)
    if error:
        module.fail_json(msg=f"Failed to read servers CSV: {error}")

    if module.check_mode:
        solution_names = {"1": "UCP VMware", "9": "Azure Stack HCI", "10": "VSSB Servers"}
        module.exit_json(changed=True, 
                        msg=f"Would configure {solution_names.get(solution_type)} on {len(servers)} servers")

    # Start nginx if requested
    if manage_nginx:
        manage_nginx_server("start")

    configured_servers = []
    failed_servers = []
    bios_templates_applied = {}

    try:
        # Configure each server
        for server in servers:
            success, message, template = configure_server_complete(
                server, solution_type, spv_url_g2, spv_url_g3, kickstart_url,
                templates_directory, ilorest_path, skip_bios_reboot
            )
            
            if success:
                configured_servers.append(server['ipaddress'])
                if template:
                    bios_templates_applied[server['ipaddress']] = template
            else:
                failed_servers.append({
                    'ipaddress': server['ipaddress'],
                    'model': server.get('model', 'Unknown'),
                    'error': message
                })
    finally:
        # Stop nginx if we started it
        if manage_nginx:
            time.sleep(2)
            manage_nginx_server("stop")

    # Determine if changes were made
    changed = len(configured_servers) > 0

    result = {
        'changed': changed,
        'configured_servers': configured_servers,
        'failed_servers': failed_servers,
        'bios_templates_applied': bios_templates_applied,
        'msg': f"Configured {len(configured_servers)} servers, {len(failed_servers)} failed"
    }

    if failed_servers and not configured_servers:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()

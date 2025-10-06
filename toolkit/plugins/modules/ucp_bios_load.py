#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ucp_bios_load
short_description: Load BIOS settings to servers using iLO REST API
version_added: "1.0.0"
description:
- This module loads BIOS settings to servers by connecting to their iLO management interface
- Reads server credentials from a CSV file
- Uses iLO REST commands to apply BIOS templates based on server model
- Supports both UCP VMware and Azure Stack HCI configurations

options:
    servers_csv:
        description:
        - Path to CSV file containing server details (ipaddress, username, password, model)
        required: true
        type: str
    solution_type:
        description:
        - Type of solution (1 for UCP VMware, 2 for Azure Stack HCI)
        required: true
        choices: ["1", "2"]
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
    perform_reboot:
        description:
        - Whether to reboot servers after applying BIOS settings
        required: false
        default: true
        type: bool

author:
    - Ansible Toolkit Team
'''

EXAMPLES = r'''
- name: Load BIOS settings for UCP VMware
  ucp_bios_load:
    servers_csv: "/path/to/servers.csv"
    solution_type: "1"
    templates_directory: "./HA-G2-G3BiosTemplates"
    perform_reboot: true

- name: Load BIOS settings for Azure Stack HCI
  ucp_bios_load:
    servers_csv: "/path/to/servers.csv"
    solution_type: "2"
    templates_directory: "./HA-G2-G3BiosTemplates"
'''

RETURN = r'''
loaded_servers:
    description: List of servers where BIOS settings were loaded successfully
    type: list
    returned: always
    sample: ["10.1.1.1", "10.1.1.2"]
failed_servers:
    description: List of servers where BIOS load failed
    type: list
    returned: always
    sample: []
template_mappings:
    description: Mapping of servers to their applied templates
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
                                  fieldnames=['ipaddress', 'username', 'password', 'model', 'sn'])
            next(reader)  # Skip header
            for row in reader:
                servers.append(row)
        return servers, None
    except Exception as e:
        return None, str(e)


def get_bios_template(model, solution_type, templates_directory):
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
        "2": {  # Azure Stack HCI
            "default": "HA_G2_ASHCI.bios.json",
            "Hitachi Advanced Server HA805 G3": "HA_G3_ASHCI_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA815 G3": "HA_G3_ASHCI_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA825 G3": "HA_G3_ASHCI_AMD_HA805_HA815_825_G3.json",
            "Hitachi Advanced Server HA810 G3": "HA_G3_ASHCI.bios.json",
            "Hitachi Advanced Server HA820 G3": "HA_G3_ASHCI.bios.json",
            "Hitachi Advanced Server HA840 G3": "HA_G3_ASHCI.bios.json",
        }
    }
    
    template_name = template_mappings.get(solution_type, {}).get(model, 
                                                               template_mappings[solution_type]["default"])
    return os.path.join(templates_directory, template_name)


def load_bios_config(server, solution_type, templates_directory, ilorest_path, perform_reboot):
    """Load BIOS configuration to a single server"""
    try:
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        model = server.get('model', 'Unknown')
        
        # Login command
        login_cmd = [ilorest_path, 'login', ipaddress, '-u', username, '-p', password]
        result = subprocess.run(login_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"Login failed: {result.stderr}", None
        
        # Get appropriate template
        template_file = get_bios_template(model, solution_type, templates_directory)
        
        if not os.path.exists(template_file):
            return False, f"Template file not found: {template_file}", None
        
        # Load BIOS template
        load_cmd = [ilorest_path, 'load', '-f', template_file]
        result = subprocess.run(load_cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return False, f"BIOS template load failed: {result.stderr}", None
        
        time.sleep(5)  # Wait a bit after loading
        
        # Reboot if requested
        if perform_reboot:
            reboot_cmd = [ilorest_path, 'reboot']
            result = subprocess.run(reboot_cmd, capture_output=True, text=True, shell=False)
            if result.returncode != 0:
                return False, f"Reboot failed: {result.stderr}", template_file
                
        return True, "Successfully loaded BIOS configuration", os.path.basename(template_file)
        
    except Exception as e:
        return False, str(e), None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            servers_csv=dict(required=True, type='str'),
            solution_type=dict(required=True, choices=['1', '2'], type='str'),
            templates_directory=dict(required=False, default='./HA-G2-G3BiosTemplates', type='str'),
            ilorest_path=dict(required=False, default='ilorest', type='str'),
            perform_reboot=dict(required=False, default=True, type='bool'),
        ),
        supports_check_mode=True,
    )

    servers_csv = module.params['servers_csv']
    solution_type = module.params['solution_type']
    templates_directory = module.params['templates_directory']
    ilorest_path = module.params['ilorest_path']
    perform_reboot = module.params['perform_reboot']

    # Read servers from CSV
    servers, error = read_servers_csv(servers_csv)
    if error:
        module.fail_json(msg=f"Failed to read servers CSV: {error}")

    if module.check_mode:
        solution_name = "UCP VMware" if solution_type == "1" else "Azure Stack HCI"
        module.exit_json(changed=True, 
                        msg=f"Would load BIOS templates for {solution_name} on {len(servers)} servers")

    loaded_servers = []
    failed_servers = []
    template_mappings = {}

    # Load BIOS configuration on each server
    for server in servers:
        success, message, template = load_bios_config(
            server, solution_type, templates_directory, ilorest_path, perform_reboot
        )
        
        if success:
            loaded_servers.append(server['ipaddress'])
            if template:
                template_mappings[server['ipaddress']] = template
        else:
            failed_servers.append({
                'ipaddress': server['ipaddress'],
                'model': server.get('model', 'Unknown'),
                'error': message
            })

    # Determine if changes were made
    changed = len(loaded_servers) > 0

    result = {
        'changed': changed,
        'loaded_servers': loaded_servers,
        'failed_servers': failed_servers,
        'template_mappings': template_mappings,
        'msg': f"Loaded BIOS config on {len(loaded_servers)} servers, {len(failed_servers)} failed"
    }

    if failed_servers and not loaded_servers:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()

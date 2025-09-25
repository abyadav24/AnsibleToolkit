#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import json
import logging
import os
from datetime import datetime

try:
    from prettytable import PrettyTable
    HAS_PRETTYTABLE = True
except ImportError:
    HAS_PRETTYTABLE = False

# Setup logging
def setup_logging():
    """Setup logging to file with timestamp"""
    # Use a fixed logs directory path - avoid using module path during Ansible execution
    logs_dir = "/home/ubuntu/smci/ansible-toolkit/toolkit/logs"
    
    # Ensure logs directory exists
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"display_discovery_table_{timestamp}.log"
    log_path = os.path.join(logs_dir, log_filename)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()  # Also log to stderr for immediate visibility
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Display module logging initialized. Log file: {log_path}")
    return logger

# Initialize logger
logger = setup_logging()

def display_servers_table(servers):
    """Display servers in a pretty table format similar to original autodiscover.py"""
    logger.info(f"Displaying servers table for {len(servers) if servers else 0} servers")
    
    if not servers:
        logger.info("No servers to display")
        return "No servers discovered"
    
    # Create the servers table
    table = PrettyTable()
    table.field_names = ["Equipment Type", "Name", "Model", "Serial", "IPv4 Address", "Username", "Password"]
    table.sortby = "Name"
    
    for server in servers:
        # Clean IPv6 address to create a readable hostname
        hostname = server.get('host', '').replace('[', '').replace(']', '')
        # Create a cleaner hostname using serial number
        clean_hostname = f"server_{server.get('serial_number', 'unknown')}"
        ipv4 = server.get('ipv4_address', 'N/A')
        
        logger.debug(f"Adding server to table: {clean_hostname} - {server.get('model', 'N/A')}")
        
        table.add_row([
            server.get('type', 'Unknown'),
            clean_hostname,
            server.get('model', 'N/A'),
            server.get('serial_number', 'N/A'),
            ipv4,
            server.get('username', 'N/A'),
            server.get('password', 'N/A')
        ])
    
    logger.info("Servers table created successfully")
    return str(table)

def display_switches_table(switches):
    """Display switches in a pretty table format"""
    logger.info(f"Displaying switches table for {len(switches) if switches else 0} switches")
    
    if not switches:
        logger.info("No switches to display")
        return "No switches discovered"
    
    # Create the switches table
    table = PrettyTable()
    table.field_names = ["Equipment Type", "Name", "IPv4 Address", "Username", "Password", "Model"]
    table.sortby = "Name"
    
    for switch in switches:
        hostname = switch.get('host', '').replace('[', '').replace(']', '')
        logger.debug(f"Adding switch to table: {hostname} - {switch.get('model', 'N/A')}")
        
        table.add_row([
            switch.get('type', 'Unknown'),
            hostname,
            switch.get('ipv4_address', 'N/A'),
            switch.get('username', 'N/A'),
            switch.get('password', 'N/A'),
            switch.get('model', 'N/A')
        ])
    
    logger.info("Switches table created successfully")
    return str(table)

def main():
    logger.info("Starting display_discovery_table module")
    
    module_args = dict(
        servers=dict(type='list', required=False, default=[]),
        switches=dict(type='list', required=False, default=[]),
        display_servers=dict(type='bool', required=False, default=True),
        display_switches=dict(type='bool', required=False, default=True)
    )

    result = dict(
        changed=False,
        message='',
        servers_table='',
        switches_table=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if not HAS_PRETTYTABLE:
        logger.error("prettytable library is not available")
        module.fail_json(msg="prettytable library is required for this module")

    servers = module.params['servers']
    switches = module.params['switches']
    display_servers = module.params['display_servers']
    display_switches = module.params['display_switches']

    logger.info(f"Module parameters - servers: {len(servers)}, switches: {len(switches)}, display_servers: {display_servers}, display_switches: {display_switches}")

    messages = []
    
    if display_servers and servers:
        logger.info("Processing servers table display")
        servers_table = display_servers_table(servers)
        result['servers_table'] = servers_table
        messages.append(f"\n{'=' * 48} Discovered Servers Table {'=' * 49}\n{servers_table}")
    
    if display_switches and switches:
        logger.info("Processing switches table display")
        switches_table = display_switches_table(switches)
        result['switches_table'] = switches_table
        messages.append(f"\n{'=' * 50} Discovered Switches Table {'=' * 50}\n{switches_table}")
    
    if not messages:
        logger.info("No devices to display")
        messages.append("No devices to display")
    
    result['message'] = '\n'.join(messages)
    
    logger.info("Display module completed successfully")
    module.exit_json(**result)

if __name__ == '__main__':
    main()

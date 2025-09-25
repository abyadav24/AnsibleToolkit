#!/usr/bin/python

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import socket
import requests
import logging
import os
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: server_discover
short_description: Identify server type by querying Redfish API using IPv6.
description:
  - Connects to a server's Redfish endpoint using IPv6 and credentials to determine hardware model/SKU.
options:
  ipv6_address:
    description:
      - The IPv6 address of the target server.
    required: true
    type: str
  username:
    description:
      - Username for Redfish login.
    required: false
    default: admin
    type: str
  password:
    description:
      - Password for Redfish login.
    required: false
    default: cmb9.admin
    type: str
author:
  - Your Name
'''

RETURN = r'''
server_type:
  description: The identified server type (e.g. DS120_G1, DS220_G1, etc.)
  type: str
  returned: on success
model:
  description: Model string from Redfish API
  type: str
  returned: on success
SKU:
  description: SKU string from Redfish API
  type: str
  returned: on success
'''

def setup_logger():
    """Creates a timestamped logger in /tmp/server_discover_logs"""
    log_dir = "/tmp/server_discover_logs"
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"server_discover_{timestamp}.log")

    logging.basicConfig(
        filename=log_path,
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.debug("Logger initialized")
    return log_path


def main():
    log_path = setup_logger()

    module = AnsibleModule(
        argument_spec=dict(
            ipv6_address=dict(required=True, type='str'),
            username=dict(required=False, type='str', default='admin'),
            password=dict(required=False, type='str', default='cmb9.admin')
        ),
        supports_check_mode=True
    )

    ipv6_address = module.params['ipv6_address']
    username = module.params['username']
    password = module.params['password']

    logging.info(f"Starting discovery for {ipv6_address}")

    try:
        # Check IPMI UDP port 623
        addrinfo = socket.getaddrinfo(ipv6_address, 623, socket.AF_INET6, socket.SOCK_DGRAM)
        family, socktype, proto, canonname, sockaddr = addrinfo[0]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(3)
        result = sock.connect_ex(sockaddr)
        sock.close()
        if result != 0:
            msg = f"IPMI port 623 is not open on {ipv6_address}"
            logging.warning(msg)
            module.fail_json(msg=msg)

        logging.info("IPMI port check passed.")

        # Redfish base query
        redfishapi = f"https://[{ipv6_address.replace('%', '%25')}]/redfish/v1/Systems"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'curl/7.54.0',
            'Host': f"[{ipv6_address.split('%')[0]}]"
        }

        logging.debug(f"Querying Redfish base API: {redfishapi}")
        response = requests.get(redfishapi, auth=(username, password), headers=headers, verify=False, timeout=10)

        if not response.ok:
            msg = f"Failed Redfish login for {ipv6_address}, status={response.status_code}"
            logging.error(msg)
            module.fail_json(msg=msg)

        j = response.json()
        logging.debug(f"Redfish base API response: {j}")

        if 'Members' not in j or not j['Members']:
            msg = f"No Systems members found at Redfish API for {ipv6_address}"
            logging.error(msg)
            module.fail_json(msg=msg)

        # Query first system
        system_url = f"https://[{ipv6_address.replace('%', '%25')}]{j['Members'][0]['@odata.id']}"
        logging.debug(f"Querying Redfish system URL: {system_url}")
        response = requests.get(system_url, auth=(username, password), headers=headers, verify=False, timeout=10)
        j = response.json()
        logging.debug(f"System info response: {j}")

        SKU = j.get('SKU', '')
        model = j.get('Model', '')

        # Server type mapping
        if 'Advanced Server DS120_S5B-MB' in SKU:
            server_type = 'DS120_G1'
        elif 'Advanced Server DS220_S5B-MB' in SKU:
            server_type = 'DS220_G1'
        elif 'Advanced Server DS120 G2_S5X' in SKU:
            server_type = 'DS120_G2'
        elif 'Advanced Server DS220 G2_S5X' in SKU:
            server_type = 'DS220_G2'
        elif 'DS225' in SKU:
            server_type = 'DS225'
        elif 'DS240' in SKU:
            server_type = 'DS240'
        elif 'D52BV' in SKU:
            server_type = 'D52BV'
        elif 'D52B' in SKU:
            server_type = 'D52B'
        elif 'Q72D' in SKU:
            server_type = 'Q72D'
        else:
            server_type = f"Unknown ({SKU})" if SKU else "Unknown"

        logging.info(f"Identified: server_type={server_type}, model={model}, SKU={SKU}")
        module.exit_json(changed=False, server_type=server_type, SKU=SKU, model=model)

    except Exception as e:
        logging.exception("Unexpected error occurred")
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()

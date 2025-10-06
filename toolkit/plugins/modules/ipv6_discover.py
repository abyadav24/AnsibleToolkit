#!/usr/bin/python
#working code 
import itertools
import socket
import requests
import multiprocessing
from subprocess import Popen, PIPE
from ansible.module_utils.basic import AnsibleModule
import os
import subprocess
import logging

# Setup logging
log_path = "/tmp/customAnsibleModuleExecution.log"
logging.basicConfig(
    filename=log_path,
    filemode='a',  # append mode
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logging.debug("Starting custom IPv6 discovery module.")

def get_nic_interfaces():
    """Get all non-loopback and UP NIC interfaces from /sys/class/net"""
    interfaces = []
    try:
        for iface in os.listdir('/sys/class/net'):
            if iface != 'lo':
                operstate_path = f"/sys/class/net/{iface}/operstate"
                with open(operstate_path) as f:
                    state = f.read().strip()
                if state == "up":
                    interfaces.append(iface)
                    logging.info(f"Interface {iface} is up and added.")
                else:
                    logging.info(f"Interface {iface} is {state}, skipping.")
    except Exception as e:
        logging.error(f"Failed to list interfaces: {e}")
        raise RuntimeError(f"Failed to list interfaces: {str(e)}")
    return interfaces


def ping_and_discover(interface):
    """Ping ff02::1 on a given interface and parse neighbors"""
    discovered = []
    try:
        cmd = ['ping6', '-c', '2', f'ff02::1%{interface}']
        logging.info(f"Pinging from interface {interface}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        output = result.stdout.decode()
        logging.info(f"Output  {output}")

        for line in output.splitlines():
            if line.startswith("64 bytes from fe80:"):
                # Extract the source address
                parts = line.split()
                ipv6_address = parts[3].rstrip(':') 
                discovered.append(ipv6_address)
                logging.info(f"Discovered neighbor: {ipv6_address}")
    except Exception as e:
        raise RuntimeError(f"Failed to discover IPv6 neighbors on {interface}: {str(e)}")
        
    return discovered


def discoverNodes(IPv6nodes, usernames=['ADMIN'], passwords=['cmb9.admin']):
    logging.info(f"Starting Node Discovery against {len(IPv6nodes)} devices.")
    logging.info("disocvering nodes")
    combinations = list(itertools.product(IPv6nodes, usernames, passwords))
    pool = multiprocessing.Pool(processes=30)
    results = pool.starmap(discoverNodeType, combinations)
    pool.close()
    pool.join()
    return [x for x in results if x is not None]

def discoverNodeType(IPv6node, username, password):
    logging.info("discovering node type...")
    try:
        logging.info("discovering node type...")
        addrinfo = socket.getaddrinfo(IPv6node, 623, socket.AF_INET6, socket.SOCK_DGRAM)
        (family, socktype, proto, canonname, sockaddr) = addrinfo[0]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(5)
        result = sock.connect_ex(sockaddr)
        sock.close()
        if result != 0:
            logging.warning(f"No IPMI on {IPv6node}")
            return None
    except Exception as e:
        logging.error(f"Socket error for {IPv6node}: {e}")
        return None

    #redfishapi = f'https://[{IPv6node.replace("%", "%25")}]/redfish/v1/'
    redfishapi = f'https://[{IPv6node.replace("%", "%25")}]/redfish/v1/Systems/'
    redfishheader = {
        'Content-Type': 'application/json',
        'User-Agent': 'curl/7.54.0',
        'Host': f'[{IPv6node.split("%")[0]}]'
    }

    #passwords = [password, lawcompliance.passwordencode(IPv6node, getPassword())]
    passwords = [password,password]
    session = None
    members = None

    for pwd in passwords:
        try:
            logging.info("creating session ...")
            session = requests.get(redfishapi + '1', auth=(username, pwd), verify=False,
                                   headers=redfishheader, timeout=30)
            logging.info(f"session ......{session}")
            j = session.json()
            logging.info(f"j of session : {j}")
            if j.get('error', {}).get('code') == "Base.1.0.PasswordChangeFromIPMI":
                #tempNode = quantaskylake.QuantaSkylake(IPv6node, username, password)
                
                #password = lawcompliance.passwordencode(IPv6node, getPassword())
                password = password
                #tempNode.forcePasswordChange(password)
                #del tempNode
            members = j.get('Members')
            if members:
                break
        except Exception as e:
            logging.error(f"Redfish access failed for {IPv6node}: {e}")
            continue

    if not members:
        return None

    try:
        for member in members:
            redfishapi = f'https://[{IPv6node.replace("%", "%25")}]{member["@odata.id"]}'
            logging.info(f"redfish api resp for: {member} {redfishapi} ")
            break
        session = requests.get(redfishapi, auth=(username, password), verify=False,
                               headers=redfishheader, timeout=30)
        j = session.json()
    except:
        return None

    try:
        SKU = j['SKU']
        model = j['Model']
    except:
        logging.error(f"Missing SKU/Model for {IPv6node}")
        return None

    
    if 'Q72D' in SKU:
        logging.info("other node discovered...")
    elif "Super" in model:
        logging.info("smci node discovered...")
        #write_to_csv_for_HA(IPv6node, username, password, model, j)
        #return quantaskylake.HA820_G2(IPv6node, username, password, model)
    else:
        #logging.warning(f"Unknown SKU for {IPv6node}: {SKU}")
        return None


def run_module():
    logging.debug("Starting run module.")
    module_args = dict(
        interface=dict(type='str', required=False, default=None),
    )

    result = dict(
        changed=False,
        interfaces=[],
        ipv6_neighbors=[],
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        if module.params['interface']:
            interfaces = [module.params['interface']]
        else:
            logging.debug("Nic interface call...")
            interfaces = get_nic_interfaces()

        result['interfaces'] = interfaces

        all_neighbors = []
        for iface in interfaces:
            neighbors = ping_and_discover(iface)
            all_neighbors.extend(neighbors)

        unique_neighbors = list(set(all_neighbors))
        result['ipv6_neighbors'] = list(set(all_neighbors))

        logging.info("calling discover nodes...")
        # Node discovery and classification
        nodes = discoverNodes(unique_neighbors)
        result['nodes_discovered'] = [str(node) for node in nodes]  # Customize as needed

    except Exception as e:
        module.fail_json(msg=str(e), **result)

    module.exit_json(**result)


def main():
    logging.debug("Main function call.")
    run_module()


if __name__ == '__main__':
    main()

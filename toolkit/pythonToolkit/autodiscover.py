import datetime
import random
import string
import requests
import urllib3

urllib3.disable_warnings()
import multiprocessing
import itertools
import quantaskylake
import sys
from netmiko import ConnectHandler
import cisconexus
import brocadefc
import aristaeos
from pexpect.popen_spawn import PopenSpawn
import pexpect
import socket
import lawcompliance
import time
import minios
import esxi
import copy
import concurrent.futures
import badtime
import helper
import json
import networkconfig
import vsphere
import prettytable
import os
import csv
# from prettytable import PrettyTable

# SubModule Logging
import logging
import toolkit_config
from quantaskylake import QuantaSkylake
from esxi import ESXi
logger = logging.getLogger(__name__)

HA_MODEL = {
    "Hitachi Advanced Server HA820 G2": "P05174-B21",
    "Hitachi Advanced Server HA810 G2": "P28948-B21",
    "Hitachi Advanced Server HA810 G3": "WC3382-008",
    "Hitachi Advanced Server HA820 G3": "NA",
    "Hitachi Advanced Server HA825 G3": "NA",
    "Hitachi Advanced Server HA815 G3": "NA",
    "Hitachi Advanced Server HA805 G3": "NA",
    "Hitachi Advanced Server HA840 G3": "P56092-B21"
}
CSV_FILE_PATH = 'HA8XX_scripts/servers.csv'
# TOOLKIT_LAB_TEST_NETWORKCONFIG = toolkit_config.getConfig().lab_test_networkconfig

def getPassword(theinput="default"):
    thedict = {
        "default": "UCPMSP.",
        "esxi": "UCPESXI."
    }
    return thedict[theinput]


def getNICInterfaces():
    interfacelist = []
    if 'win' in sys.platform:
        # Start route print
        session = PopenSpawn('route print')
        # Get output from session
        output = session.read(2000)
        # Convert to utf-8
        output = output.decode('utf-8')
        # Split by =====
        output = output.split('===========================================================================')
        if len(output) < 4:
            raise ValueError('Route print returned incorrect output.')
        # Get Interface Line and parse output
        for line in output:
            # Go to line with Interface List string
            if 'Interface List' in line:
                # Split everything by newline
                splitline = line.splitlines()
                # Remove lines without ...
                # https://stackoverflow.com/questions/3416401/removing-elements-from-a-list-containing-specific-characters
                splitline = [x for x in splitline if "..." in x]
                # Get NIC Number and append to interfacelist
                for nic in splitline:
                    # Get the index number from line
                    index = nic[:3].lstrip()
                    # Once list gets to loopback, break
                    if index is '1':
                        break
                    # Add index to list
                    interfacelist.append(nic[:3].lstrip())
    # Assuming everything else is linux
    else:
        session = pexpect.spawn('ls /sys/class/net')
        output = session.read(2000)
        output = output.decode('utf-8')
        output = output.split()
        for item in output:
            if 'lo' not in item:
                interfacelist.append(item)
    
    return interfacelist


def useTargetNodes():
    return toolkit_config.getConfig().nodes


def getIPv6Neighbors(interface=None):
    IPv6Devices = useTargetNodes()
    if len(IPv6Devices) != 0:
        logger.info("Operation will be performed on these nodes:")
        for node in IPv6Devices:
            print("\t", node)

        input('\nHit Enter to continue..')
        return IPv6Devices
    else:
        # Get Interfaces if interface is None, otherwise program Interface from input
        NICs = []
        if interface is None:
            NICs = getNICInterfaces()
        else:
            NICs.append(str(interface))
        # Send link-local ping to each NIC
        logger.info('Discovering IPv6 devices on the following interfaces:')
        logger.info(NICs)
        # Set and start ping threads
        hosts = []
        if 'win' in sys.platform:
            for NIC in NICs:
                host = 'ff02::1%' + NIC
                hosts.append((host,))
            pool = multiprocessing.Pool(processes=10)
            pool.starmap(ping, hosts)
            pool.close()
            pool.join()
            # Get IPv6 Neighbors for each NIC
            IPv6Devices = []
            for NIC in NICs:
                logger.info('Getting IPv6 Neighbors for NIC#' + NIC)
                # Get output from netsh command
                session = PopenSpawn('netsh interface ipv6 show neighbors ' + NIC)
                output = session.read(200000)
                # Split output by newlines
                splitline = output.splitlines()
                # Remove lines without ...
                # https://stackoverflow.com/questions/3416401/removing-elements-from-a-list-containing-specific-characters
                splitline = [x for x in splitline if b'fe80::' in x]
                # Create IPv6 Regular Expression
                for line in splitline:
                    # Get IPv6 Device from line
                    IPv6Device = line[:44].rstrip().decode("utf-8") + '%' + NIC
                    logger.info(IPv6Device)
                    IPv6Devices.append(IPv6Device)
        # Assume everything else is linux platform
        else:
            IPv6Devices = []
            for NIC in NICs:
                session = pexpect.spawn('ping6 -c 2 ff02::1%' + str(NIC))
                session.wait()
                output = session.read(20000)
                output = output.decode('utf-8')
                output = output.splitlines()
                for line in output:
                    if line.startswith("64 bytes from fe80:"):
                        IPv6Devices.append(line.split()[3][:-1] + '%' + str(NIC))
        return IPv6Devices
        # return ['fe80::aa1e:84ff:fe73:ba49%11',
        # 'fe80::aa1e:84ff:fecf:34e%11']
        # return ['fe80::aa1e:84ff:fe73:ba49%11']


def ping(host):
    # For Windows, IPv6 neighbors can be discovered by sending a link-local packet across the whole L2 network.
    # Response time should be <1ms since the toolkit needs to physically be near the nodes.
    session = PopenSpawn('ping -w 1 -n 8 ' + host)
    output = session.read(2000)
    output = output.decode('utf-8')
    logger.debug(output)
    return output


def discoverNodes(IPv6nodes, usernames=['admin'], passwords=['cmb9.admin']):
    logger.info('Starting Node Discovery against ' + str(len(IPv6nodes)) + ' IPv6 Devices')
    # time.sleep(5)
    # empty the csv file before processing
    with open(CSV_FILE_PATH, 'w') as file:
        file.write('')

    # Create all combinations of commands
    tuples = []
    for combination in itertools.product(IPv6nodes, usernames, passwords):
        tuples.append(combination)

    pool = multiprocessing.Pool(processes=30)
    results = pool.starmap(discoverNodeType, tuples)
    pool.close()
    pool.join()
    # https://stackoverflow.com/questions/16096754/remove-none-value-from-a-list-without-removing-the-0-value
    results = [x for x in results if x is not None]
    # Add forwarding ports for linux applications that do not support IPv6 Link-Local Addressing
    return results


def discoverNodeType(IPv6node, username, password):
    # Output the address, username and password
    temp = IPv6node + ' ' + username + ' ' + password
    logger.info('Start  ' + temp)

    # Check if IPMI Port is Open
    # https://stackoverflow.com/questions/4030269/why-doesnt-a-en0-suffix-work-to-connect-a-link-local-ipv6-tcp-socket-in-python
    addrinfo = socket.getaddrinfo(IPv6node, 623, socket.AF_INET6, socket.SOCK_DGRAM)
    # print(addrinfo)
    (family, socktype, proto, canonname, sockaddr) = addrinfo[0]
    sock = socket.socket(family, socktype, proto)
    sock.settimeout(5)
    # print(sockaddr)
    result = sock.connect_ex(sockaddr)
    sock.close()
    if result == 0:
        logger.info('IPMI   ' + IPv6node)
    else:
        logger.warning('NoIPMI ' + IPv6node)
        return None

    # Set the address
    # Also %25 has to be used for URLs instead of % due to URL Encoding rules.
    redfishapi = 'https://[' + IPv6node.replace('%', '%25') + ']/redfish/v1/'
    # Have to remove the lin-local zone ID for correct curl command
    redfishheader = {
        'Content-Type': 'application/json',
        'User-Agent': 'curl/7.54.0',
        'Host': '[' + IPv6node.split('%')[0] + ']'
    }

    # Attempt to login with two passwords
    passwords = [password, lawcompliance.passwordencode(IPv6node, getPassword())]
    session = None
    members = None

    for password in passwords:
        # Let user know we are checking this username and password
        temp = IPv6node + ' ' + username + ' ' + password
        logger.info("Check  " + temp)

        # Attempt to connect. If specific force password change is required, change password.
        try:
            session = requests.get(redfishapi + 'Systems', auth=(username, password), verify=False,
                                   headers=redfishheader, timeout=30)
            try:
                j = session.json()
                if j['error']['code'] == "Base.1.0.PasswordChangeFromIPMI":
                    # Create a temp node and update the password. Destroy Node
                    tempNode = quantaskylake.QuantaSkylake(IPv6node, 'admin', 'cmb9.admin')
                    password = lawcompliance.passwordencode(IPv6node, getPassword())
                    # tempNode.forcePasswordChange(password)
                    logger.info("CPASS  " + IPv6node + " Changing Password to " + password)
                    tempNode.forcePasswordChange(password)
                    del tempNode
            except:
                pass
            try:
                members = j['Members']
                break
            except:
                pass
        except:
            logger.error('NoRF   ' + temp)
            continue

        '''
        # If Session is not good, return nothing
        if not session.ok:
            print('NoRF   ' + temp)
            session = None
            continue
        else:
            break
        '''
    # Return nothing if nothing is found
    if session is None or members is None:
        return None

    logger.debug('RFDATA ' + IPv6node + ' ' + str(j))

    # Loop through members and get first member
    for member in members:
        try:
            redfishapi = 'https://[' + IPv6node.replace('%', '%25') + ']' + member['@odata.id']
            break
        except:
            # Return nothing if @odata.id key doesn't exist
            return None

    ''' Discover which type of node this is '''
    # Try to get first member details
    try:
        session = requests.get(redfishapi, auth=(username, password), verify=False,
                               headers=redfishheader, timeout=30)
    except:
        logger.error('Error  ' + temp)
        return None
    # If Session is not good, return nothing
    if not session.ok:
        logger.error('Error  ' + temp)
        return None

    # Attempt to decode JSON data
    try:
        j = session.json()
    except:
        # If return data isn't JSON, return nothing.
        logger.error('Error  ' + temp)
        return None

    logger.debug('RFDATA ' + IPv6node + ' ' + str(j))

    # Attempt to get SKU Data
    try:
        SKU = j['SKU']
        model = j['Model']
    except:
        logger.error('NOSKU   ' + temp)
        return None
    # if 'NA' in SKU:
    #     print(j)
    if (' ' is SKU):
        cmd = 'ipmitool -I lanplus -H ' + IPv6node + ' -U ' + username + ' -P ' + password + ' fru print'
        print(cmd)
        session = PopenSpawn(cmd)
        output = session.read(2000)
        output = output.decode('utf-8')
        if 'Error' in output:
            logger.error('ErrIPMI ' + temp)
            return None
        lines = output.splitlines()
        for line in lines:
            if 'Product Name' in line:
                try:
                    SKU = line.split(':', 1)[1].strip()
                    break
                # if 'Board Product' in line:
                #      try:
                #         SKU = line.split(':', 1)[1].strip()
                #         break
                except:
                    continue

    # Decode which node this is
    # If its a D52B Series, return Skylake Server
    if 'Advanced Server DS120_S5B-MB' in SKU:  # QError fe80::aa1e:84ff:fea5:33cd%3 admin cmb9.admin SKU='Advanced Server DS120_S5B-MB 1U (LBG-4)'
        logger.info('Found  ' + temp)
        return quantaskylake.DS120_G1(IPv6node, username, password)
    if 'Advanced Server DS220_S5B-MB' in SKU:
        logger.info('Found  ' + temp)
        return quantaskylake.DS220_G1(IPv6node, username, password)
    elif 'Advanced Server DS120 G2_S5X' in SKU:
        logger.info('Found  ' + temp)
        return quantaskylake.DS120_G2(IPv6node, username, password)
    elif 'Advanced Server DS220 G2_S5X' in SKU:
        logger.info('Found  ' + temp)
        return quantaskylake.DS220_G2(IPv6node, username, password)
    elif 'DS225' in SKU:
        logger.info('Found  ' + temp)
        return quantaskylake.DS225(IPv6node, username, password)
    elif 'DS240' in SKU:
        logger.info('Found  ' + temp)
        return quantaskylake.DS240(IPv6node, username, password)
    elif 'D52BV' in SKU:
        logger.info('Found  ' + temp)
        return quantaskylake.D52BV(IPv6node, username, password)
    elif 'D52B' in SKU:
        logger.info('Found  ' + temp)
        return quantaskylake.D52B(IPv6node, username, password)
    elif 'Q72D' in SKU:
        logger.info('Found  ' + temp)
        return quantaskylake.Q72D(IPv6node, username, password)
    elif model in HA_MODEL.keys():
        logger.info(f'Found HA Node: {model}') 
        write_to_csv_for_HA(IPv6node, username, password, model, j)
        return quantaskylake.HA820_G2(IPv6node, username, password,model)
    else:
        # If it doesn't match anything, return nothing
        logger.error('QError ' + temp + ' SKU=\'' + SKU + '\'')
        return None


def write_to_csv_for_HA(IPv6node, username, password, model, sku_data):
    IPv6node = IPv6node.split("%")[0]
    IPv6node = f"[{IPv6node}]"
    # Define the data you want to append
    new_data = [
        IPv6node, username, password, model, sku_data['SerialNumber']
    ]

    # Define the file path and fieldnames (header) for your CSV file

    fieldnames = ['IPv6', 'Username', 'Password', 'Model', 'SerialNumber']
    # rows = []
    # with open(CSV_FILE_PATH, newline='') as csvfile:
    #     readers = csv.DictReader(csvfile,fieldnames=fieldnames)
    #     # if any(readers):
    #     #    next(readers)
    #     updated = False
    #     # print(f"reaching here //////////////////////////////{list(readers)}")
    #     list_reader = list(readers)
    #     for read in list_reader:
    #         print(f"{read} <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< read are")
    #         if read['IPv6'] == IPv6node:
    #             read['Password'] = password
    #             updated=True
    #         rows.extend(list(read))
    #     if not updated:
    #         rows.extend(new_data)
    # print(f"rows are >>>>>>>>>>>>>>>>>>>>>>>>>>>>>{rows}")
    # Append the new data to the CSV file

    with open(CSV_FILE_PATH, mode='a+', newline='') as file:
        writer = csv.writer(file)

        # Check if the file is empty and write the header if necessary
        file.seek(0)
        if not any(line.strip() for line in file):
            writer.writerow(fieldnames)
        # Write the new data to the file
        writer.writerow(new_data)
        logger.info(f"Added HA node detilas {IPv6node} to the {CSV_FILE_PATH}")


def discoverSwitches(IPv6Addresses, usernames=['admin'], passwords=['Passw0rd!']):
    logger.info('Starting Switch Discovery against ' + str(len(IPv6Addresses)) + ' IPv6 Devices')
    # Create all combinations of command
    tuples = []
    for combination in itertools.product(IPv6Addresses, usernames, passwords):
        tuples.append(combination)
    pool = multiprocessing.Pool(processes=30)
    results = pool.starmap(discoverSwitchType, tuples)
    pool.close()
    pool.join()
    # https://stackoverflow.com/questions/16096754/remove-none-value-from-a-list-without-removing-the-0-value
    results = [x for x in results if x is not None]
    # Add forwarding ports for linux applications that do not support IPv6 Link-Local Addressing

    # logger.info("TEST: toolkit_config.getConfig().networkconfig_100g_to_the_host" + str(
    #     id(toolkit_config_global)) + str(toolkit_config_global.networkconfig_100g_to_the_host))
    # logger.info("TEST: global_9316d = " + str(global_9316d))
    # For 100G-to-the-host configuration, need to change 93600 type from spine to leaf
    # if global_9316d:
    #     for switch in results:
    #         if switch.model is "C93600CD-GX":
    #             logger.debug('discoverSwitches() networkconfig_100g_to_the_host found C93600CD-GX: type=' + switch.type)
    #             switch.type = "leaf"

    return results


def discoverSwitchType(IPv6Address, username, password):
    # Attempt to login with two passwords
    passwords = [password, lawcompliance.passwordencode(IPv6Address, getPassword())]

    for password in passwords:
        # Output the address, username and password
        temp = IPv6Address + ' ' + username + ' ' + password
        logger.info('Start  ' + temp)

        net_connect = None

        # SSH Into Switch as generic SSH device
        try:
            net_connect = ConnectHandler(device_type='terminal_server', ip=IPv6Address, username=username,
                                         password=password, timeout=30)
            break
        except:
            # If we failed to connect, return nothing
            logger.info('Finish ' + temp)

    if net_connect is None:
        return None

    # Check for Cisco Nexus/Arista EOS switches and Brocade FOS
    cmds = ["show version", "chassisshow"]
    for cmd in cmds:
        try:
            output = net_connect.send_command(cmd, delay_factor=10, max_loops=50)
        except:
            output = 'Failed'
        # output = net_connect.send_command(cmd, delay_factor=5)
        # If Nexus 92348 is in output, return Nexus Object

        if 'C92348GC-X ' in output:
            logger.info('Data   ' + IPv6Address + ' Found a Nexus92348 Switch')
            net_connect.disconnect()
            mgmt_switch = cisconexus.Nexus92348(IPv6Address, username, password)

            if toolkit_config.getConfig().lab_test_networkconfig == "100g":
                logger.info('TOOLKIT_LAB_TEST: Shutting down some switch ports for 100G-to-the-host network testing.')
                config_commands = ["interface eth1/35", "shutdown", "interface eth1/36", "shutdown", "interface eth1/37", "no shutdown", "interface eth1/38", "no shutdown"]
                mgmt_switch.runconfig(config_commands)
            elif toolkit_config.getConfig().lab_test_networkconfig == "standard":
                logger.info(
                    'TOOLKIT_LAB_TEST: Shutting down some switch ports for Standard Network testing.')
                config_commands = ["interface eth1/35", "no shutdown", "interface eth1/36", "no shutdown", "interface eth1/37", "shutdown", "interface eth1/38", "shutdown"]
                mgmt_switch.runconfig(config_commands)

            return mgmt_switch
        # If the 9k YC switch is in the output, return 9k YC object.
        elif '93180YC-FX ' in output:
            logger.info('Data   ' + IPv6Address + ' Found a Nexus93180YC-FX Switch')
            net_connect.disconnect()
            return cisconexus.Nexus93180YCFX(IPv6Address, username, password)
        elif '93180YC-FX3' in output:
            logger.info('Data   ' + IPv6Address + ' Found a Nexus93180YC-FX3/FX3H Switch')
            net_connect.disconnect()
            return cisconexus.Nexus93180YCFX3(IPv6Address, username, password)
        elif 'C93600CD-GX ' in output:
            logger.info('Data   ' + IPv6Address + ' Found a NexusC93600CD-GX Switch')
            net_connect.disconnect()
            return cisconexus.Nexus93600CDGX(IPv6Address, username, password)
        # If the 9k 9332C switch is in the output, return 9k 9332 object.
        elif '9332C ' in output:
            logger.info('Data   ' + IPv6Address + ' Found a Nexus9332C Switch')
            net_connect.disconnect()
            return cisconexus.Nexus9332C(IPv6Address, username, password)
        elif 'C9316D-GX' in output:
            logger.info('Data   ' + IPv6Address + ' Found a Nexus 9316D Switch')
            net_connect.disconnect()
            # global global_9316d
            # global_9316d = True
            # logger.info("TEST: global_9316d = " + str(global_9316d))
            # logger.info("TEST: toolkit_config.getConfig().networkconfig_100g_to_the_host" + str(
            #     id(toolkit_config.getConfig())) + str(toolkit_config.getConfig().networkconfig_100g_to_the_host))
            return cisconexus.Nexus9316D(IPv6Address, username, password)
        # If the part number for a G620 is found, return G620 Object
        elif 'BROCAD0000G62' in output:
            logger.info('Data   ' + IPv6Address + ' Found a G620 Switch')
            net_connect.disconnect()
            return brocadefc.G620(IPv6Address, username, password)
        elif 'SLKWRM0000G72' in output:
            logger.info('Data   ' + IPv6Address + ' Found a G720 Switch')
            net_connect.disconnect()
            return brocadefc.G720(IPv6Address, username, password)
        # If their is a DCS-7010T-48-R in the output, return DCS7010 object
        elif '7010T' in output:
            logger.info('Data   ' + IPv6Address + ' Found a DCS-7010 Switch')
            net_connect.disconnect()
            return aristaeos.DCS7010(IPv6Address, username, password)
        elif '7050SX3' in output:
            logger.info('Data   ' + IPv6Address + ' Found a DCS-7050SX3 Switch')
            net_connect.disconnect()
            return aristaeos.DCS7050SX3(IPv6Address, username, password)
        elif '7050CX3' in output:
            logger.info('Data   ' + IPv6Address + ' Found a DCS-7050CX3 Switch')
            net_connect.disconnect()
            return aristaeos.DCS7050CX3(IPv6Address, username, password)


def discoverOS(nodes, potentialpassword="Passw0rd!"):
    logger.info('Starting OS Discovery against ' + str(len(nodes)) + ' Server Devices')
    nodes = copy.deepcopy(nodes)
    instances = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(discoverOSType, node, potentialpassword) for node in nodes]
        for future in concurrent.futures.as_completed(futures):
            instances.append(future.result())

    return instances


def discoverOSType(node, potentialpassword="Passw0rd!"):
    # The CTRL-C, Enter, and logout command in string format
    cmds = ['\x03', '\n', 'exit']
    count = 0
    tnode = copy.deepcopy(node)
    del node
    node = tnode
    while count < 10:
        # Attempt to get the login prompt output.
        # If Ubuntu is found, return MiniOS object. If ESXi is found, return ESXi object after logging in.
        output = ''
        for cmd in cmds:
            ret = node.SOLActivate()
            node.SOLSession.sendline(cmd)
            time.sleep(2)
            node.SOLDeactivate()
            output += node.SOLSession.read(20000)
        if "Ubuntu" in output or "ubuntu" in output:
            logger.info(node.host + " Found a MiniOS Instance")
            instance = minios.minios(node)
            instance.login()
            return instance
        elif "ESXi" in output:
            logger.info(node.host + " Found a ESXi Instance")
            # The known passwords so far in UCP lineup
            passwords = [potentialpassword, lawcompliance.passwordencode(node.host, getPassword('esxi')), 'Passw0rd!',
                         'Hitachi2019!']
            instance = esxi.ESXi(node, 'root', '')
            for password in passwords:
                logger.info(node.host + " Attempting to log into ESXi with \"root\" and \"" + password + "\"")
                instance.password = password
                try:
                    instance.login()
                    logger.info(node.host + " Logged into ESXi with \"root\" and \"" + password + "\" successfully")
                    return instance
                except:
                    logger.error(node.host + " Failed to log into ESXi with \"root\" and \"" + password + "\"")
                    continue
            del instance
        else:
            logger.info(node.host + " No OS detected. Waiting 30 seconds to try again")
            count += 1
            time.sleep(30)
            continue
    return None


def discover(nodesnum=0, usernames=['admin'], passwords=['cmb9.admin'], from_main=None):
    nodesnum = int(nodesnum)
    # Get the nodes
    logger.info('I\'m going to use all your NIC interfaces to detect IPv6 devices.')
    if nodesnum > 0:
        input('Hit enter to continue!')

    while True:
        nodes = None
        # Get Any Nodes
        nodes = discoverNodes(getIPv6Neighbors(), usernames, passwords)

        logger.info('\nGetting IPv4 Addresses via IPv6 Link-Local Addresses')
        for node in nodes:
            node.getIPv4Address()
        #print(' ')

        # Nodesnum override I.E. Just return any discovered node
        if nodesnum < 1:
            return nodes

        if len(nodes) < 1:
            input('Uffff.... I wasn\'t able to detect any nodes man. Sorry about that. Hit enter to try again.')
        elif len(nodes) != int(nodesnum):
            input('Uh oh, I have detected a ' + str(len(
                nodes)) + ' node(s) in the rack, instead of ' + str(
                nodesnum) + '.\nPlease make sure all the BMC connections are connected or disconnected on the same flat network. Hit enter to try again.')
        else:
            input('Perfect! I have detected ' + str(len(nodes)) + '!!! Hit enter to continue!')
            return nodes


def main():
    # Print welcome screen
    badtime.hitachi()
    badtime.version()

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_file_name = "autodiscover_" + datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + '.log'
    log_file_name = os.path.join(os.getcwd(), 'logs', log_file_name)
    console_handler = logging.StreamHandler()

    file_handler = logging.FileHandler(log_file_name)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    nodes = None
    logger.info(
        "This autodiscover tool will attempt to detect nodes, switches and the ESXi instances.\n\nPlease make sure "
        "all equipment is powered on")
    input("Hit enter to continue")

    # Ask the user which rack number they are working on
    IPv6Devices = useTargetNodes()
    while True:
        logger.info("\n\nWhat would you like to discover?\n\n"
                    "1. HA and DS nodes only.\n"
                    "2. Switches only.\n"
                    "3. Both switches and HA/DS nodes.\n")

        option_selected = input("Please select one : ")

        if option_selected == "1" or option_selected == "2" or option_selected == "3":
            break

        logger.info("Invalid selection. Please try again.")

    discover_nodes = False
    # Discover nodes for option 1 and 3
    if option_selected == "1" or option_selected == "3":
        discover_nodes = True
        nodes = discoverNodes(getIPv6Neighbors(), ['admin'], ['cmb9.admin'])
        logger.info('Getting IPv4 Addresses via IPv6 Link-Local Addresses')
        for node in nodes:
            node.getIPv4Address()
        logger.info(' ')

    # Discover switches for option 2 and 3
    UCPNet = None
    if option_selected == "2" or option_selected == "3":
        racknum = "1"
        try:
            # Read the JSON File
            filename = "networkconfig.json"
            with open(filename) as json_file:
                networkconfigjson = json.load(json_file)
            rackjson = networkconfigjson['rack'][str(racknum)]
        except:
            logger.error("Rack #" + str(
                racknum) + " doesn't exist in the networkconfig.json file. Please make sure you enter the correct rack number.")
            return False
        switches = discoverSwitches(getIPv6Neighbors(), ['admin'], ['Passw0rd!'])
        if switches:
            UCPNet = networkconfig.networkstack("1", switches, networkconfigjson)
            UCPNet.detectOrder()
            UCPNet.getDetails()
        else:
            logger.info("Switches Not found")

    # Will clean up this block if no issues for a while.
    #
    # target_switch = helper.askForTargetSwitch()
    # if len(IPv6Devices) == 0:
    #     racknum = helper.askRackNumber()
    #
    #     # Ask the user how many nodes that rack has
    #     # nodesnum = helper.askNodeQuantity()
    #
    #     # Ask the user if there are any switches
    #     checkswitches = helper.askForSwitches()
    # else:
    #     racknum = 1
    #     nodesnum = str(len(IPv6Devices))
    #     checkswitches = False
    #
    # if not target_switch:
    #     while True:
    #         # Get D52B Nodes
    #         nodes = discoverNodes(getIPv6Neighbors(), ['admin'], ['cmb9.admin'])
    #
    #         logger.info('Getting IPv4 Addresses via IPv6 Link-Local Addresses')
    #         for node in nodes:
    #             node.getIPv4Address()
    #         logger.info(' ')
    #         break
    #
    # if checkswitches or target_switch or not target_switch:
    #     # Attempt to get rack details
    #     try:
    #         # Read the JSON File
    #         filename = "networkconfig.json"
    #         with open(filename) as json_file:
    #             networkconfigjson = json.load(json_file)
    #         rackjson = networkconfigjson['rack'][str(racknum)]
    #     except:
    #         logger.error("Rack #" + str(
    #             racknum) + " doesn't exist in the networkconfig.json file. Please make sure you enter the correct rack number.")
    #         return False
    #     # Discover the switches
    #     if checkswitches or target_switch:
    #         switches = discoverSwitches(getIPv6Neighbors(), ['admin'], ['Passw0rd!'])
    #     else:
    #         logger.info(
    #             "Not discovering switches, Either User provided 0 switches on this rack, or the script is enabled to use 'use_target_nodes'")
    #         switches = 0
    #     if switches:
    #
    #         UCPNet = networkconfig.networkstack(racknum, switches, networkconfigjson)
    #         UCPNet.detectOrder()
    #         UCPNet.getDetails()
    #     else:
    #         logger.info("Switches Not found")
    #         UCPNet = None
    # else:
    #     UCPNet = None

    # skip ESXi detection if #2 switch only
    if option_selected == "2":
        detectESXi = False
    else:
        answer = input("Shall I attempt to detect ESXi instances? (y/n) :")
        if "y" in answer or "Y" in answer:
            logger.info("Attempting to detect OS nodes")
            detectESXi = True
        else:
            detectESXi = False

    thecluster = None

    #filter out HA servers from the nodes array and detecting esxi on DS nodes only
    if nodes:
        nodes = [node for node in nodes if not hasattr(node, 'servertype')]
        if nodes:
            if detectESXi:
        #         # Create vSphere Cluster object
                thecluster = vsphere.cluster()
        #         # Detect the ESXi instances within nodes
                thecluster.detectESXi(nodes)
        #         # Get the details (Mainly for ipv4 details)
                thecluster.getDetails()

  
    #Discovering ESXi on HA ndoes.
    HA_ESXi_details = {}
    if detectESXi:
        try:
            with open(CSV_FILE_PATH, newline='') as csvfile:
                reader = csv.DictReader(csvfile, fieldnames=[
                                    'ipaddress', 'username', 'password','Model','SerialNumber'])
                next(reader)
                servers = list(reader)
                for server in servers:
                    #host = server['ipaddress'][1:-1]+"%7"
                    host = server['ipaddress'][1:-1]
                    user = server['username']
                    password = server['password']
                    node = QuantaSkylake(host, user, password)
                    #creating ESXi Object 
                    passwords = [password, lawcompliance.passwordencode(node.host, getPassword('esxi')), 'Passw0rd!',
                         'Hitachi2019!']
                    instance = esxi.ESXi(node, 'root', '')
                    for password in passwords:
                        logger.info(node.host + " Attempting to log into ESXi with \"root\" and \"" + password + "\"")
                        instance.password = password
                        try:
                            instance.login()
                            if(instance.loggedin == True):
                                logger.info(node.host + " Logged into ESXi with \"root\" and \"" + password + "\" successfully")
                                HA_ESXi_details[node.host.split("%")[0]] = password
                                instance.logout()
                                logger.info(f"logout check : {instance.loggedin}")
                                break
                        except Exception as e:
                            logger.info(f"Exception : {e}")
        except Exception as e:
            logger.info(f"Exception : {e}")


        # if nodes:
        #     print(f"all ha nodes are : {nodes}")
        #     print("test1 : calling vsphere cluster: ")
        #     quanta_node = QuantaSkylake("fe80::5eed:8cff:fe36:9684%7", "admin", "cmb9.admin")
        #     print("Test os discovery.")
            
        #     discoverOSType(quanta_node)
        #     node = ESXi(quanta_node,"root","Passw0rd!")
        #     node.login()
        #     HA_Nodes.append(node)
        #     HA_cluster = vsphere.cluster()
        #     print("test2 : calling vsphere cluster detect esxi func: ")
        #     HA_cluster.detectESXi(nodes)
        #     HA_cluster.getDetails()


    # Print out the username and passwords
    thetable = prettytable.PrettyTable()
    # thetable.field_names = ["Equipment Type", "Name", "Serial", "IPv4 Address", "Username", "Password"]

    # if not target_switch:
    if discover_nodes:
        thetable.field_names = ["Equipment Type", "Name", "Model", "Serial", "IPv4 Address", "Username", "Password"]
        thetable.sortby = "Name"

        # # Populate Node Details
        for node in nodes:
            # thetable.add_row([str(type(node).__name__), node.host, node.SystemsJSONCache['SerialNumber'], node.ipv4Address, node.username, node.password])
            # thetable.add_row([str(type(node).__name__), node.host,node.SystemsJSONCache['SKU'], node.SystemsJSONCache['SerialNumber'], node.ipv4Address, node.username, node.password])
            if not hasattr(node, 'servertype'):
                thetable.add_row(
                    [str(type(node).__name__), node.host, node.SystemsJSONCache['SKU'],
                    node.SystemsJSONCache['SerialNumber'],
                    node.ipv4Address, node.username, node.password])
    # Populate Switch Details
    sw_table = prettytable.PrettyTable()
    sw_table.field_names = ["Equipment Type", "Name", "IPv4 Address", "Username", "Password", "Model"]
    if UCPNet:
        sw_table.sortby = "Name"
        for switch in UCPNet.switches_cache:
            # print(switch.interfaceDetails,"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

            sw_table.add_row([str(type(switch).__name__), switch.name, switch.hostIPv4Address, switch.username,
                              switch.password, switch.model])

    # Populate ESXi Details for DS nodes 
    if thecluster:
        for instance in thecluster.esxiinstances:
            # thetable.add_row([str(type(instance).__name__), instance.node.host, instance.node.SystemsJSONCache['SerialNumber'], instance.ipv4Interfaces[0]["IPv4 Address"], instance.user, instance.password])
            thetable.add_row([str(type(node).__name__), node.host, node.SystemsJSONCache['SKU'],
                              node.SystemsJSONCache['SerialNumber'], instance.ipv4Interfaces[0]["IPv4 Address"],
                              instance.user, instance.password])
    hatable = prettytable.PrettyTable()
    hatable.field_names = ['IPv6Address', 'iLO Username', 'iLO Password', 'Model', 'SerialNumber','ESXi User','ESXi Password']

    # if not target_switch:
    if discover_nodes:
        try:
            with open(CSV_FILE_PATH, newline='') as csvfile:
                reader = csv.DictReader(csvfile, fieldnames=[
                                    'ipaddress', 'username', 'password','Model','SerialNumber'])
                next(reader)
                servers = list(reader)
                for server in servers:
                    host = server['ipaddress'][1:-1]
                    user = server['username']
                    password = server['password']
                    model = server['Model']
                    s_no = server['SerialNumber']
                    esxi_user = "NA"
                    esxi_pass = "NA"
                    if(detectESXi and host in HA_ESXi_details):
                        esxi_user="root"
                        esxi_pass = HA_ESXi_details.get(host)
                    elif(detectESXi == False):
                        print("Detect ESxi is False")  
                    hatable.add_row([host,user,password,model,s_no,esxi_user,esxi_pass])
                    
        except Exception as e:
            pass

    logger.info(f"\n{'=' * 50} HA Nodes Data Table {'=' * 50}\n{hatable}")
    # logger.info(hatable)
    logger.info(f"\n{'=' * 48} Quanta Nodes Data Table {'=' * 49}\n{thetable}")
    # logger.info(thetable)
    logger.info(f"\n{'=' * 50} Switches Data Table {'=' * 50}\n{sw_table}")
    # logger.info(sw_table)


if __name__ == "__main__":
    count = 0
    main()

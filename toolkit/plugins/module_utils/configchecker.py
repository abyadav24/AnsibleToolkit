from pexpect.popen_spawn import PopenSpawn
#from datetime import datetime
import datetime
import requests
import urllib3
urllib3.disable_warnings()
import multiprocessing
import concurrent.futures
import itertools
import quantaskylake
from esxi import ESXi
import time
import ipaddress
import badtime
import glob
import os
import autodiscover
import re
import sys
import json
import minios
import cisconexus
import networkconfig
import helper
from prettytable import PrettyTable
import copy

import loginit
import logging
logger = logging.getLogger("root")

def danceLEDs(orderednodes, dance = True):
    while True:
        if dance:
            for node in orderednodes:
                node.idon()
                time.sleep(1)
        for node in orderednodes:
            node.idoff()
            if dance:
                time.sleep(1)
        if not dance:
            break

def main():



    connectiontabletxt = 'connectiontable.txt'
    helper.removeAllVMCLI()
    badtime.hitachi()
    logger.info('\nWelcome to UCP Config Checker! \n\nI have to ask a few questions to get started.\n')

    # Read the JSON File
    filename = "networkconfig.json"
    with open(filename) as json_file:
        networkconfigjson = json.load(json_file)

    # Ask the user which rack number they are working on
    racknum = helper.askRackNumber()

    # Ask the user how many nodes are in this rack
    nodesnum = helper.askNodeQuantity()

    # Ask the user how many mgmt nodes are in this rack
    mgmtnum = helper.askMgmtQuantity()

    badtime.seperate()

    input("I'm going to detect the rack-design by detecting the type of switches in this rack. Hit enter to continue.")

    # Detect the switches and detect the design
    while True:
        switches = autodiscover.discoverSwitches(autodiscover.getIPv6Neighbors(), ['admin'], ['Passw0rd!'])
        logger.info("I discovered the following switches:")
        for switch in switches:
            logger.info(switch.name + ' ' + switch.host)
        UCPCINet = networkconfig.networkstack(racknum, switches, networkconfigjson)
        UCPCINet.detectOrder()
        if UCPCINet.design is None:
            input("I wasn't able to detect the design of this rack. Please hit enter to try again.")
        else:
            break

    time.sleep(15)

    badtime.seperate()

    # Detect the number of nodes
    logger.info("Starting Node Detection")
    while True:
        # Get Quanta Nodes
        nodes = autodiscover.discoverNodes(autodiscover.getIPv6Neighbors(), ['admin'], ['cmb9.admin'])

        logger.info('\nGetting IPv4 Addresses via IPv6 Link-Local Addresses')
        for node in nodes:
            node.getIPv4Address()
        logger.info(' ')

        # Let the user know about the detected nodes
        if len(nodes) < 1:
            input('Uffff.... I wasn\'t able to detect any nodes man. Sorry about that. Hit enter to try again.')
        elif len(nodes) != int(nodesnum):
            input('Uh oh, I have detected a ' + str(len(
                nodes)) + ' node(s) in the rack, instead of ' + nodesnum + '.\nPlease make sure all the BMC connections are connected or disconnected on the same flat network. Hit enter to try again.')
        else:
            logger.info('Perfect! I have detected ' + str(len(nodes)) + '!!!')
            break

    # CHECK ALL 3048 CONNECTIONS

    badtime.seperate()

    input("Let's start checking the mgmt cable connections. Hit enter to continue.")

    '''

    # Detect the order of the switches
    logger.info("Checking switch mgmt cable connections\n")
    while True:
        UCPCINet.detectOrder(forcecheck=True)
        if UCPCINet.checkOrder():
            logger.info("All switch mgmt ports are connected correctly. Please wait\n")
            break
        else:
            logger.info("The switch's management connections are not connected to correct ports. Please re-run toolkit to re-check switch order. Otherwise, hit enter to continue.")
            answer = input('Hit enter to continue or type exit to exit: ')
            if 'exit' in answer:
                return None
            else:
                break
            # return None
    '''

    # Detect the order of the nodes

    # Get the management switch instance
    try:
        mgmtswitch = UCPCINet.getMGMTSwitch()
    except:
        raise("Management switch is missing. This is not suppose to happen.")

    # Check the node location to ethernet port location
    logger.info("Checking BMC cable connections. Please wait")

    # Update mgmtswitch mactable initially
    mgmtswitch.getMACTable()

    while True:
        completed = True

        # Get location of nodes
        nodes_dict = {}
        for node in nodes:
            try:
                if "Cisco" in UCPCINet.design:
                    node_location = int(mgmtswitch.whereisMAC(node.mgmtMAC).replace("Eth1/",""))
                else:
                    node_location = int(mgmtswitch.whereisMAC(node.mgmtMAC).replace("Et", ""))
            except:
                logger.info(node.host + " was located from a non-ethernet interface")
                continue
            nodes_dict.update({node_location:node})

        # Print table of nodes
        node_table = PrettyTable(["MGMT_Port_Location","Node_Model", "Node_IPv4_Address","Node_Serial"])
        node_table.sortby = "MGMT_Port_Location"
        for location, node in nodes_dict.items():
            node_table.add_row([location, node.model, node.ipv4Address, node.SystemsJSONCache.get("SerialNumber", "N/A")])
        logger.info("Detected order of nodes based off MGMT switch connections")
        logger.info(node_table)

        # Make ordered nodes list
        orderednodes=[]
        for location, node in sorted(nodes_dict.items()):
            orderednodes.append(node)

        if completed:
            logger.info("I'm going to turn on the LEDs in the detected order from first to last node detected.")
            process = multiprocessing.Process(target=danceLEDs, args=(orderednodes, True))
            process.start()
            response = input("Are the node's identification LEDs turning on from the bottom compute node to top compute node and from the top mgmt node to bottom mgmt node? ")
            if 'y' in response or 'Y' in response:
                input("Perfect! Hit enter to continue")
                nodes = orderednodes
                process.terminate()
                process.join()
                danceLEDs(nodes, False)
                break
            else:
                process.terminate()
                process.join()
                input("Please connect the BMC connections in order (I.E. Server at U1 connects to Port #1 on mgmt switch, U13 - Port #13 ,etc) Hit enter to continue.")
                logger.info("Retrying order check")
                # Update mgmtswitch mactable
                mgmtswitch.getMACTable(True)

            # input("Successfully connected all the BMC connections to the MGMT Switch")
        else:
            input("I've detected some problems. Hit enter to retry check")
            logger.info("Please wait")

    # Load the miniOS
    # Start MiniOS Logic
    badtime.seperate()
    logger.info("Starting PCI Device Cable Connection Validation\n")

    contain_G2 = False
    for node in nodes:
        if node.gen == 2:
            contain_G2 = True
            break

    if contain_G2:
        print("Detected G2 node. Performing BMC IPMI COLD RESET. Please allow 5 minutes to complete.")
        for node in nodes:
            if node.gen == 2:
                node.resetBMC()
        time.sleep(330)

    # Make sure Redfish BIOS config is populated
    helper.redfishValidate(nodes)
    
    logger.info('\nStarting VMCLI Instances')
    vmcli_nodes = helper.massStartVMCLI(nodes, minios.getminiosiso())

    logger.info('\nSetting MiniOS BIOS Default')
    processes = []
    for node in nodes:
        processes.append(multiprocessing.Process(target=node.setMiniOSDefaults))
    # Start threads
    for process in processes:
        process.start()
    # Wait for threads
    for process in processes:
        process.join()

    logger.info('\nPowering on the nodes to start MiniOS.')
    for node in nodes:
        node.poweron()
        # Slowly power-on nodes to not overload circuit
        time.sleep(2)

    # logger.info("\nCreating MiniOS Instances")
    # copied_nodes = copy.deepcopy(nodes)
    # minioses = []
    # for node in copied_nodes:
    #     minioses.append(minios.minios(node))
    #
    # logger.info("\nLogging into all MiniOS Instances")
    # for minios_instance in minioses:
    #     minios_instance.login()

    logger.info("\nCreating MiniOS Instances")
    minioses = []
    for node in nodes:
        minios_instance = minios.minios(node)
        minios_instance.date = None
        minioses.append(minios_instance)

    logger.info("\nAttempting to login into all MiniOS Instances")

    minioses_logged_in = []
    minios_login_fail = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(minios.minios_login_wrapper, minios_instance) for minios_instance in minioses]
        for future in concurrent.futures.as_completed(futures):
            minios_instance = future.result()
            if not minios_instance.loggedin:
                logger.info(
                    '*** ' + minios_instance.node.host + " -> MiniOS login FAILED. Removing this node from the list.")
                minios_login_fail = True
                minios_instance.node.stopVMCLIapp()
            else:
                minioses_logged_in.append(minios_instance)

    time.sleep(10)

    if minios_login_fail:
        response = input(
            'MiniOS login failed on some nodes. Do you still want to continue with successful nodes? (y/n): ')
        if 'n' in response:
            helper.removeAllVMCLI()
            if contain_G2:
                print("Detected G2 node. Performing BMC IPMI COLD RESET. Please allow 5 minutes to complete.")
                for node in nodes:
                    if node.gen == 2:
                        node.resetBMC()
                time.sleep(330)
            logger.info('\nExiting... :D\n\n')
            exit(0)
    else:
        logger.info('\n**All MiniOS instance logged in !! :D\n\n')

    minioses = minioses_logged_in

    logger.info("\nDiscovering All PCI Devices in all MiniOS Instances")
    temp_minioses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(minios.pcidiscoverwrapper, minios_instance) for minios_instance in minioses]
        for future in concurrent.futures.as_completed(futures):
            temp_minioses.append(future.result())
    minioses = temp_minioses

    # Reorder the minioses based off node order
    temp_minioses = []
    for node in nodes:
        for minios_instance in minioses:
            if node.host == minios_instance.node.host:
                temp_minioses.append(minios_instance)
    minioses = temp_minioses

    for minios_instance in minioses:
        minios_instance.printPCIDevices()

    check = True
    while check:
        logger.info("Asking nodes to send multicast packet storm")
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            futures = [executor.submit(minios_instance.sendpingstorm) for minios_instance in minioses]
            for future in concurrent.futures.as_completed(futures):
                pass
        logger.info("Updating Ethernet Connections Table")
        t = PrettyTable(["MGMT_Port_Node_Location", "Node_Model", "PCI_Model", "PCI_Location", "Port", "Port_MAC", "Switch", "Switch_Port"])
        # t.sortby = "3048_Port_Node_Location"
        logger.info("Refreshing MAC Tables")
        UCPCINet.updateMACTable()
        for minios_instance in minioses:
            mgmtswitch, node_location = UCPCINet.whereisMAC(minios_instance.node.mgmtMAC)
            if "Cisco" in UCPCINet.design:
                node_location = node_location.replace("Eth1/","")
            else:
                node_location = node_location.replace("Et", "")
            for PCILoc, PCIDevice in sorted(minios_instance.PCIDevices.items()):
                if isinstance(PCIDevice,minios.NIC):
                    for MAC in PCIDevice.MACs:
                        switchname, port = UCPCINet.whereisMAC(MAC)
                        # If switchname is none, go to next MAC
                        if switchname is None:
                            pass
                        if '3' in PCILoc[0]:
                            PCIEnglLoc = "OCP"
                        elif '1c:' in PCILoc or '86:' in PCILoc:
                            PCIEnglLoc = "PCIe"
                        else:
                            PCIEnglLoc = PCILoc
                        t.add_row([node_location, minios_instance.node.model, PCIDevice.name, PCIEnglLoc, int(PCIDevice.MACs.index(MAC) + 1), MAC, switchname, port])
        logger.info(t)
        response = input("Please validate the cabling with the Excel Sheet Cabling. Want me to recheck the cable connections? ")
        if 'y' in response.lower():
            continue
        else:
            check = False

    check = True
    while check:
        logger.info("Updating WWN Connections Table")
        wwn_t = PrettyTable(["MGMT_Port_Node_Location", "Node_Model", "PCI_Model", "PCI_Location", "Port", "Port_WWN","Switch", "Switch_Port"])
        # wwn_t.sortby = "3048_Port_Node_Location"
        logger.info("Refreshing WWN tables")
        UCPCINet.updateWWNTable()
        for minios_instance in minioses:
            mgmtswitch, node_location = UCPCINet.whereisMAC(minios_instance.node.mgmtMAC)
            if "Cisco" in UCPCINet.design:
                node_location = node_location.replace("Eth1/", "")
            else:
                node_location = node_location.replace("Et", "")
            for PCILoc, PCIDevice in sorted(minios_instance.PCIDevices.items()):
                if isinstance(PCIDevice,minios.HBA):
                    for WWN in PCIDevice.WWNs:
                        switchname, port = UCPCINet.whereisWWN(WWN)
                        if switchname is None:
                            pass
                        wwn_t.add_row([node_location, minios_instance.node.model, PCIDevice.name, PCILoc, int(PCIDevice.WWNs.index(WWN)), WWN, switchname, port])
        logger.info(wwn_t)
        response = input("Please validate the cabling with the Excel Sheet Cabling. Want me to recheck the cable connections? ")
        if 'y' in response.lower():
            continue
        else:
            check = False

    logger.info('\nSetting UCP CI BIOS Default')
    processes = []
    for node in nodes:
        processes.append(multiprocessing.Process(target=node.setUCPCIDefaults))
    # Start threads
    for process in processes:
        process.start()
    # Wait for threads
    for process in processes:
        process.join()

    # Write Table of Connections to File
    txtobject = open(connectiontabletxt, 'w')
    txtobject.write('Node Table:\n')
    txtobject.write(node_table.get_string())
    txtobject.write('\n\nEthernet Cabling Table:\n')
    txtobject.write(t.get_string())
    txtobject.write('\n\nWWN Cabling Table:\n')
    txtobject.write(wwn_t.get_string())

    # Power off the nodes
    logger.info('\nPowering off the nodes to stop MiniOS.')
    for node in nodes:
        node.poweroff()

    helper.removeAllVMCLI()
    logger.info("I have outputted the Node, MAC and WWN tables to the connectiontable.txt within the scripts folder. Enjoy!")

    if contain_G2:
        print("Detected G2 node. Performing BMC IPMI COLD RESET. Please allow 5 minutes to complete.")
        for node in nodes:
            if node.gen == 2:
                node.resetBMC()
        time.sleep(330)

    badtime.okay()

if __name__ == "__main__":
    count = 0
    main()
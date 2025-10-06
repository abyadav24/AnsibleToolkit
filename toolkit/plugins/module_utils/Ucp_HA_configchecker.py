import sys
from typing import Any
import redfish
import os
from prettytable import PrettyTable
from pexpect.popen_spawn import PopenSpawn
from datetime import datetime
import requests
import urllib3
urllib3.disable_warnings()
from esxi import ESXi
import time
import badtime
import os
import autodiscover
import json
import networkconfig
import helper
import logging
logger = logging.getLogger("root")
import csv
#sys.path.insert(1,'C:\\UCPToolkit7.1\\UCPCI-HC_MediaKit_V7.1_2023\\WinPython-64bit-3.6.3.0Zero\\scripts\\HA8XX_scripts')


exec_path = os.getcwd()
os.chdir(exec_path)
# Add the executable path to the PATH environment variable
os.environ['PATH'] += os.pathsep + exec_path

executable_path = os.path.join(os.getcwd(), "python-ilorest-library-master", "src", "redfish")
sys.path.insert(1, executable_path)

CSV_FILE_PATH = 'HA8XX_scripts/servers.csv'
nodes = []

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

class HA_operations:
    def __init__(self):
        if nodes!=[]:
            self.nodes = nodes
            print("nodes exist")
        else:
            self.nodes = nodes
            print("empty nodes ")

    def createSession(self, custom_url):
        print(f"creating session for node {self.ilo_host} ")
        base_url = f"https://{self.ilo_host}"
        login_account = self.Username
        login_password = self.Password
        self.custom_url = custom_url

        # Create a REDFISH object
        print(f"url -->>>>> {base_url}")
        REDFISH_OBJ = redfish.RedfishClient(base_url=base_url, username=login_account,
                                            password=login_password, default_prefix='/redfish/v1')


        # Login into the server and create a session
        try:
            REDFISH_OBJ.login(auth="session")
            print("Session creation successful!")
        except redfish.rest.exceptions.JSONDecodeError:
            print("Error in Creating Session.")
            return


        # Do a GET on a given path
        try:
            print(f"calling URL {self.ilo_host}{self.custom_url}")
            response = REDFISH_OBJ.get(self.custom_url)
        except redfish.rest.exceptions.JSONDecodeError:
            print(f"Error in calling custom api {self.custom_url}")
            REDFISH_OBJ.logout()
            return

        # Print out the response
        sys.stdout.write("%s\n" % response)

        # Logout of the current session
        REDFISH_OBJ.logout()
        return response

    def Discover_HA_Nodes(self):
        print("Please hold on while we Discover HA nodes...")
        time.sleep(3)
        try:
            with open(CSV_FILE_PATH, 'r') as f:
                reads = csv.reader(f)
                next(reads)  # Skip the header row
                for read in reads:
                    node = {}
                    node["IPV6"] = read[0]
                    node["Username"] = read[1]
                    node["Password"] = read[2]
                    node["Model"] = read[3]
                    node["SerialNumber"] = read[4]
                    nodes.append(node)
        except FileNotFoundError as e:
            print("Server.csv File not found, pleae recheck if file exist ad rerun again..:", e)
        except Exception as e:
            print("An error occurred while reading server.csv file contents :", e)


        for count , item in enumerate(nodes):
            print(f"{count+1} : {item}")
        return nodes

    def getEthernetAdapters(self):
        for node in self.nodes:
            print(f"Getting node details : {node}")
            self.ilo_host = node["IPV6"]
            self.Username = node["Username"]
            self.Password = node["Password"]
            self.ethernet_url = "/redfish/v1/Managers/1/EthernetInterfaces"
            try:
                response = self.createSession(self.ethernet_url)
                if response and response.status == 200:
                    # Extract members from the API response
                    members_eth = response.dict.get("Members", [])
                    member_eth_ids = [member.get("@odata.id", "") for member in members_eth]
                    ntw_card= self.processEthernetMembers(member_eth_ids)
                node["management_cards_details"]=ntw_card
            except Exception as e:
                print(f"An error occurred while processing node Ethernet Adapters: {node}\nError: {e}")

    def processEthernetMembers(self, member_eth_ids):
        ntw_card = []
        for member_id_url in member_eth_ids:
            ntw_card_details = {}
            print(f"\n processing details of member {member_id_url}")
            try:
                response = self.createSession(member_id_url)
                if response and response.status == 200:
                    # Process the response for each member
                    ipv6_addresses = response.dict.get("IPv6Addresses", [])
                    ipv4_addresses = response.dict.get("IPv4Addresses", [])
                    IPv6Addresses = [addr.get("Address") for addr in ipv6_addresses]
                    IPv4Addresses = [addr.get("Address") for addr in ipv4_addresses]
                    if(response.dict.get("Name", "") == "Manager Dedicated Network Interface"):
                        ntw_card_details = {
                            "LinkStatus": response.dict.get("LinkStatus", ""),
                            "MACAddress": response.dict.get("MACAddress", ""),
                            "PermanentMACAddress": response.dict.get("PermanentMACAddress", ""),
                            "HostName": response.dict.get("HostName", ""),
                            "IPv6Addresses": IPv6Addresses,
                            "IPv4Addresses": IPv4Addresses,
                            "Name": response.dict.get("Name", "")
                        }
                else:
                    print(f"Failed to create session for member: {member_id_url}")
                if ntw_card_details:
                    ntw_card.append(ntw_card_details)
            except Exception as e:
                print(f"An error occurred while processing Ethernet Member {member_id_url}\nError: {e}")
        return ntw_card


    def processFCMembers(self, member_fc_ids):
        fc_card = []
        for member_id in member_fc_ids:
            try:
                print(f"processing FC member : {member_id}")
                response = self.createSession(member_id)
                #response = response.dict.get()
                if response and response.status == 200:
                    print(f"response 200 for {member_id}")
                    self.fc_card_details = {}
                    # Extracting Controllers details
                    controllers = response.dict.get("Controllers", [])
                    if controllers:
                        controller = controllers[0]
                        firmware_version = controller.get("FirmwarePackageVersion")
                        self.fc_card_details["FirmwarePackageVersion"] = firmware_version

                    # Extract NetworkDeviceFunctions, NetworkPorts, and Ports from Controllers
                    links = controller.get("Links", {})
                    #etwork_device_functions = links.get("NetworkDeviceFunctions", [])
                    #network_device_function_ids = [func.get("@odata.id") for func in network_device_functions]
                    #self.fc_card_details["NetworkDeviceFunctions"] = network_device_function_ids

                    #Updating Dictionary with port details


                    # Extract NetworkPorts and Ports from Controllers
                    network_ports = links.get("NetworkPorts", [])
                    network_port_ids = [port.get("@odata.id") for port in network_ports]
                    self.fc_card_details["NetworkPorts"] = network_port_ids

                    ports = links.get("Ports", [])
                    port_ids = [port.get("@odata.id") for port in ports]
                    self.fc_card_details["Ports"] = port_ids

                    # Extract LocationType and ServiceLabel from Location
                    location = controller.get("Location", {})
                    part_location = location.get("PartLocation", {})
                    location_type = part_location.get("LocationType")
                    service_label = part_location.get("ServiceLabel")
                    self.fc_card_details["LocationType"] = location_type
                    self.fc_card_details["ServiceLabel"] = service_label

                    # Extract Model, Name, SerialNumber, and SKU from response
                    self.fc_card_details["Model"] = response.dict.get("Model")
                    self.fc_card_details["Name"] = response.dict.get("Name")
                    self.fc_card_details["SerialNumber"] = response.dict.get("SerialNumber")
                    self.fc_card_details["SKU"] = response.dict.get("SKU")
                    fc_card_details=self.fc_card_details
                    print(f"fc_card_details  : {self.fc_card_details}")
                    ports = self.processFCMemberPorts()
                    self.fc_card_details["ports_data"] = ports
                else:
                    print(f"Failed to process member: {member_id}")
                if fc_card_details:
                    print(f"FC cards with ports data {fc_card_details}")
                    fc_card.append(self.fc_card_details)
            except Exception as e:
                print(f"An error occurred while processing FC Member {member_id}\nError: {e}")
        return fc_card


    def getFCCardDetails(self):
        try:
            for node in self.nodes:
                self.ilo_host = node["IPV6"]
                self.Username = node["Username"]
                self.Password = node["Password"]
                self.fc_url = "/redfish/v1/Chassis/1/NetworkAdapters"
                response = self.createSession(self.fc_url)
                if response and response.status == 200:
                    members_fc = response.dict.get("Members", [])
                    member_fc_ids = [member.get("@odata.id", "") for member in members_fc]
                    fc_cards= self.processFCMembers(member_fc_ids)
                else:
                    print("Failed to retrieve FC card details.")
                node["FC_card_details"]=fc_cards


            nodes_data = json.dumps(self.nodes, indent=4)
            return self.nodes
        except Exception as e:
            print(f"An error occurred while getting FC card details: {e}")
            return None

    def processFCMemberPorts(self):
        ports_details = []
        print("\n working on to fetch the NetworkDeviceFunctions ")
        ports_fc_cards = self.fc_card_details.get("Ports", [])
        ports_ethernet_cards = self.fc_card_details.get("NetworkPorts", [])
        try:
            if(ports_fc_cards):
                for port_id_url in ports_fc_cards:
                    port_data = {}
                    response = self.createSession(port_id_url)
                    if response and response.status == 200:
                        port_json = response.dict
                        # Extract the required items
                        port_data["AssociatedMACAddresses"] = port_json["Ethernet"]["AssociatedMACAddresses"]
                        port_data["SignalDetected"] = port_json["SignalDetected"]
                        port_data["PortId"] = port_json["PortId"]
                        port_data["LinkNetworkTechnology"] = port_json["LinkNetworkTechnology"]
                        # Append the port_data dictionary to ports_details
                        ports_details.append(port_data)
                    else:
                        print(f"Failed to process NetworkDeviceFunction: {port_id_url}")
        except Exception as e:
                print(f"An error occurred while processing NetworkDeviceFunctions")
        else:
            try:
                for port_id_url in ports_ethernet_cards:
                    port_data = {}
                    response = self.createSession(port_id_url)
                    if response and response.status == 200:
                        port_json = response.dict
                        # Extract the required items
                        port_data["AssociatedMACAddresses"] = port_json["AssociatedNetworkAddresses"][0]
                        port_data["SignalDetected"] = port_json["LinkStatus"]
                        port_data["PortId"] = port_json["PhysicalPortNumber"]
                        port_data["LinkNetworkTechnology"] = port_json["ActiveLinkTechnology"]
                        # Append the port_data dictionary to ports_details
                        ports_details.append(port_data)
                    else:
                        print(f"Failed to process NetworkDeviceFunction: {port_id_url}")
            except Exception as e:
                print(f"An error occurred while processing NetworkDeviceFunctions Else Block...")
        return ports_details


def main():
    connectiontabletxt = 'connectiontable_HA.txt'
    helper.removeAllVMCLI()
    badtime.hitachi()
    logger.info('\nWelcome to UCP Config Checker HA nodes ! \n\nI have to ask a few questions to get started.\n')

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

    #create an object of HA operations class
    objc = HA_operations()

    #this returns list of nodes reading from server.csv
    nodes = objc.Discover_HA_Nodes()

    #calling getEthernetAdapters() for discovered nodes and returns nodes by appending the ethernet adaptor values.
    nodes = objc.getEthernetAdapters()

    nodes = objc.getFCCardDetails()

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

    badtime.seperate()

    # CHECK ALL 3048 CONNECTIONS

    badtime.seperate()

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

    input("Enter to continue to locate management switch details and connections....")

    completed = False

    # Get location of nodes
    nodes_dict = {}
    mac=""
    for node in nodes:
        mac=""
        mac_address = node["management_cards_details"][0]["MACAddress"]
        formatted_mac_address = mac_address.split(":")
        for count, item in enumerate(formatted_mac_address):
            if(count%2!=0 or count ==0):
                mac=mac+str(item)
            else:
                mac=mac+"."+item
        mac=mac.lower()
        #mgmtswitch, node_location = UCPCINet.whereisMAC(mac)

        try:
            if "Cisco" in UCPCINet.design:
                node_location = int(mgmtswitch.whereisMAC(mac.replace(".", "")).replace("Eth1/",""))

            else:
                node_location = int(mgmtswitch.whereisMAC(mac.replace(".", "")).replace("Et", ""))
        except:

            logger.info(node["IPV6"] + " was located from a non-ethernet interface")
            continue
        nodes_dict.update({node_location:node})
    # Print table of nodes
    node_table = PrettyTable(["MGMT_Port_Location","Node_Model", "Node_IPv6_Address","Node_Serial"])
    node_table.sortby = "MGMT_Port_Location"
    for location, node in nodes_dict.items():
        node_table.add_row([location, node["Model"], node["IPV6"], node["SerialNumber"]])
    logger.info("Detected order of nodes based off MGMT switch connections")
    logger.info(node_table)

    # Make ordered nodes list
    orderednodes=[]
    for location, node in sorted(nodes_dict.items()):
        print(f"location : {location}" +f'  node : {node}')
        orderednodes.append(node)

    badtime.seperate()
    logger.info("Starting PCI Device Cable Connection Validation\n")


    logger.info("Updating Ethernet Connections Table")
    t = PrettyTable(["MGMT_Port_Node_Location", "Node_Model","Node_ipv6","PCI_Model","PCI_Firmware", "PCI_Location", "Port", "Port_MAC", "Switch", "Switch_Port"])
    wwn_t = PrettyTable(["MGMT_Port_Node_Location", "Node_Model","Node_Ipv6","PCI_Model","PCI_Firmware", "PCI_Location", "Port", "Port_WWN","Switch", "Switch_Port"])
    # t.sortby = "3048_Port_Node_Location"
    logger.info("Refreshing MAC Tables")
    UCPCINet.updateMACTable()
    mac=""
    mac_adr=""
    UCPCINet.updateWWNTable()
    for node in nodes:
        mac=""
        mac_adr=""
        node_ipv6=node["IPV6"]
        mac_address = node["management_cards_details"][0]["MACAddress"]
        formatted_mac_address = mac_address.split(":")
        for count, item in enumerate(formatted_mac_address):
            if(count%2!=0 or count ==0):
                mac=mac+str(item)
            else:
                mac=mac+"."+item
        mac=mac.lower()

        try:
            mgmtswitch, node_location = UCPCINet.whereisMAC(mac.replace(".", ""))
            if "Cisco" in UCPCINet.design:
                if node_location:
                    node_location = node_location.replace("Eth1/","")
            elif node_location:
                node_location = node_location.replace("Et", "")
                print(f"node_location in fc ----------------------{node_location}")
        except Exception as e:
            print(f"An error occurred while Accessing Details of Management card on Management Switch..")
            continue

        for fc_card in node['FC_card_details']:
            card_name = fc_card['Name']
            card_firmware = fc_card["FirmwarePackageVersion"].split(" ")[0]
            card_slot=fc_card["ServiceLabel"]
            """
            if card_slot and card_slot.strip():
                card_slot_data = card_slot.split(" ",1)
                pci_location = card_slot_data[0]
                card_port = card_slot_data[1]
            """

            mac_adr=""
            card_type=""
            for port_data in fc_card['ports_data']:
                mac_fc=""
                mac=""
                mac_adr=""
                card_type = port_data["LinkNetworkTechnology"]
                port_no = port_data["PortId"]
                try:
                    if(card_type == "Ethernet"):
                        mac =  port_data['AssociatedMACAddresses']
                        mac_fc = "".join(mac)
                        formatted_mac_fc = mac_fc.split(":")
                        for count, item in enumerate(formatted_mac_fc):
                            if(count%2!=0 or count ==0):
                                mac_adr=mac_adr+str(item)
                            else:
                                mac_adr=mac_adr+"."+item
                        mac_adr=mac_adr.lower()
                    else:
                        mac=port_data['AssociatedMACAddresses']
                        mac_adr = "".join(mac)
                        mac_adr=mac_adr.lower()
                except Exception as e:
                    print(f"An error occurred while Accessing Details of Ethernet/FC card on respective Switch..")
                    continue
                try:
                    switchname, port = UCPCINet.whereisMAC(mac_adr)

                    if(card_type == "Ethernet"):
                        switchname, port = UCPCINet.whereisMAC(mac_adr)
                        t.add_row([node_location, node["Model"],node_ipv6, card_name ,card_firmware, card_slot, port_no, mac_adr, switchname, port])
                    else:
                        switchname, port = UCPCINet.whereisWWN(mac_adr)
                        wwn_t.add_row([node_location, node["Model"],node_ipv6, card_name,card_firmware, card_slot, port_no, mac_adr, switchname, port])
                except Exception as e:
                    print(f"An error occurred while writing to the Preety Table..")
                    continue


    print("Management data table : \n")
    logger.info(node_table)

    print("Ethernet table data : \n")
    logger.info(t)

    print("wwn table data : \n")
    logger.info(wwn_t)

if __name__ == "__main__":
    count = 0

    main()


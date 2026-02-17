import switches
from netmiko import ConnectHandler
import time
import ipaddress
import re

class aristaeos(switches.switch):
    def __init__(self, host, username, password):
        switches.switch.__init__(self, host, username, password)
        self.deviceType = "arista_eos"
        self.mgmtInterface = "Management1"
        self.interfaceList = []
        self.interfaceDetails = {}
        self.VLANList = []
        self.MACTable = {}
        self.runningconfig = ""
        self.getDetails()
        self.getInterfaces()
        # self.getVLANs()

    def runcommand(self, command):
        try:
            net_connect = ConnectHandler(device_type=self.deviceType, ip=self.host, username=self.username, password=self.password)
            net_connect.enable()
            output = net_connect.send_command(command)
            net_connect.disconnect()
            return output
        except:
            return ''

    def runconfig(self, commands):
        count = 0
        while count < 5:
            count += 1
            try:
                net_connect = ConnectHandler(device_type=self.deviceType, ip=self.host, username=self.username, password=self.password)
                net_connect.enable()
                output = net_connect.send_config_set(commands)
                print(self.host + ' Running the following commands:')
                print(output)
                net_connect.disconnect()
                return output
            except:
                time.sleep(60)
                continue
        return ''

    def getDetails(self):
        self.getName()
        self.getMGMTMAC()

    def getName(self):
        output = self.runcommand('show hostname | grep Hostname:')
        self.name = output.split(' ', 1)[-1]
        return self.name

    def setName(self, switchname):
        config_commands = ["hostname " + switchname]
        self.runconfig(config_commands)
        self.name = switchname
        return self.name

    '''
    def enableAPI(self):
        config_commands = ["management api http-commands", "protocol http", "no shutdown"]
        self.runconfig(config_commands)
    '''

    def enableAPI(self):
        config_commands = ["management api http-commands", "protocol http", "no shutdown", "management ssh", "authentication mode password", "no shutdown"]
        self.runconfig(config_commands)

    def updateUserPass(self, username, password):
        if username is not "admin":
            print(self.host + " doesn't support changing password for " + username)
            return False
        config_commands = ["username " + username + " secret " + password]
        self.runconfig(config_commands)
        self.password = password
        return True


    def getIPv4MGMT(self):
        # Get the latest runningconfig
        output = self.getRunningConfig()

        # Get the IP address
        try:
            self.hostIPv4Address = self.interfaceDetails["interface " + self.mgmtInterface]["ip-address"]
        except:
            pass

        # Get the Gateway Address
        for line in output.splitlines():
            if 'ip route 0.0.0.0/0 ' in line:
                self.hostIPv4Gateway = line.split()[-1]

        return self.hostIPv4Address, self.hostIPv4Gateway

    def setIPv4MGMT(self, ipv4Address, ipv4Subnet = '', ipv4Gateway = ''):
        # If the address doesn't contain the subnet, add it.
        if '/' not in ipv4Address:
            ipv4Address = ipv4Address + '/' + ipv4Subnet
        # Validate ipv4 Settings
        try:
            mgmtinterface = ipaddress.IPv4Interface(ipv4Address)
            gateway = ipaddress.IPv4Address(ipv4Gateway)
        except:
            print(self.host + ' Invalid MGMT IPv4 Address Input')
            return False

        # Get latest mgmt address and gateway
        self.getIPv4MGMT()

        # Delete old management address and routes
        config_commands = ['interface ' + self.mgmtInterface,
                           'no ip address ' + self.hostIPv4Address,
                           'exit',
                           'no ip route 0.0.0.0/0 ' + self.hostIPv4Gateway]
        self.runconfig(config_commands)

        # Set new mgmt address and gateway
        config_commands = ['interface ' + self.mgmtInterface,
                           'ip address ' + str(mgmtinterface),
                           'exit',
                           'ip route 0.0.0.0/0 ' + str(gateway)]
        self.runconfig(config_commands)

        # Store new address and gateway in class
        self.getIPv4MGMT()

        # Doublecheck if setting was set
        # DO LATER

        return True

    def getMGMTMAC(self):
        output = self.runcommand('show interface ' + self.mgmtInterface + ' | grep address')
        try:
            self.mgmtMAC = output.split("address")[1].split()[1].replace('.','')
            return self.mgmtMAC
        except:
            return None

    def setMLAGPeering(self, mlagdomainid = 1, peerlinkportchannel = '', peerlinkinterfaces = [], peerlinkvlan = '', peerlinklocaladdress = '', peerlinkpeeraddress = ''):
        # Start config commands list
        config_commands = []

        # Delete old MLAG
        self.runconfig(["no mlag configuration"])

        # Create the Peer-Link Port-Channel
        self.setPortChannelInterface(peerlinkportchannel, peerlinkinterfaces, [peerlinkvlan], "mlag peerlink", "peer-link")

        # Delete all L3 VLAN interface
        self.runconfig("no interface vlan 1-4094")

        # Set the new L3 VLAN interface
        config_commands = config_commands + ["interface vlan " + str(peerlinkvlan),
                                             "ip address " + peerlinklocaladdress,
                                             "no autostate",
                                             "no shutdown",
                                             "exit",
                                             "no spanning-tree vlan " + str(peerlinkvlan)]

        # Set the new MLAG Configuration
        config_commands = config_commands + ["mlag configuration",
                                             "local-interface vlan " + str(peerlinkvlan),
                                             "peer-address " + peerlinkpeeraddress.split('/')[0],
                                             "peer-link port-channel " + str(peerlinkportchannel),
                                             "domain " + str(mlagdomainid),
                                             "heartbeat-interval 2500",
                                             "reload-delay 150",
                                             "no shutdown"]
        self.runconfig(config_commands)

    # Get the running config of the switch and populate the interface details dictionary
    def getRunningConfig(self):
        output = self.runcommand('show running-config')
        self.runningconfig = output
        # Split the output to get the interface details
        lines = output.splitlines()
        # Empty out interface dictionary
        self.interfaceDetails = {}
        # Start parsing through output
        interfacekey = None
        interfacedict = {}
        for line in lines:
            # If string starts with interface, set temp key and dict
            if line.startswith('interface '):
                interfacekey = line
                interfacedict = {}
                continue

            # If new line is reached and theres an interface, dump temp data to interfacedetails
            if (interfacekey is not None) and (len(interfacedict) >= 0) and ("!" in line):
                self.interfaceDetails.update({interfacekey: interfacedict})
                interfacekey = None
                interfacedict = None
                continue

            # If interfacekey is not None, look for specific details
            if interfacekey is not None:
                # If the line contains switchport mode, store access/trunk value
                if "  switchport mode" in line:
                    interfacedict.update({"switchport-mode": line.split()[-1]})
                    continue
                # If the line contains switchport access vlan, store the vlan and make sure switchport mode is access
                elif "  switchport access vlan" in line:
                    interfacedict.update({"switchport-mode": "access"})
                    interfacedict.update({"vlans": [int(line.split()[-1])]})
                    continue
                # If the line contains switchport trunk allowed vlan, store vlans as list
                elif "  switchport trunk allowed vlan" in line:
                    vlanstring = line.split()[-1]
                    tempvlans = vlanstring.split(',')
                    vlans = []
                    for tempvlan in tempvlans:
                        if '-' in tempvlan:
                            startvlan, endvlan = tempvlan.split('-')
                            for vlan in range(int(startvlan), int(endvlan), 1):
                                vlans.append(vlan)
                        else:
                            try:
                                vlans.append(int(tempvlan))
                            except:
                                vlans.append(tempvlan)
                    interfacedict.update({"vlans": vlans})
                    continue
                elif "  mlag" in line:
                    interfacedict.update({"mlag": str(line.split()[-1])})
                    continue
                elif "  description" in line:
                    interfacedict.update({"description": line.split()[-1]})
                    continue
                elif "  channel-group" in line:
                    try:
                        interfacedict.update({"channel-group": line.split()[1]})
                        interfacedict.update({"channel-group-mode": line.split()[3]})
                    except:
                        continue
                elif "  ip address" in line:
                    interfacedict.update({"ip-address": line.split()[-1]})
                    continue
        return self.runningconfig

    def saveRunningConfig(self):
        command = "copy running-config startup-config"
        output = self.runcommand(command)
        if "successfully" in output:
            return True
        else:
            return False

    def resetAllInterfaces(self):
        # Get latest interfaces
        temp_interfaces = self.getInterfaces()
        # Express Setting on all interfaces
        ethernet_interfaces = []
        interfaces = []
        for interface in temp_interfaces:
            if "Ethernet" in interface:
                ethernet_interfaces.append(interface)
            else:
                interfaces.append(interface)
        # Attempt to make all ethernet interfaces as one group. If it fails, default to all interfaces
        try:
            intname = "interface Ethernet"
            begnum = ethernet_interfaces[0].split("Ethernet")[-1]
            endnum = ethernet_interfaces[-1].split("Ethernet")[-1]
            intname = intname + begnum + "-" + endnum
            interfaces.append(intname)
        except:
            interfaces = temp_interfaces

        # Start reseting procedure
        self._resetInterfaces(interfaces)
        return True

    def _resetInterfaces(self, interfaces):
        config_commands = []
        # Arista switches need MLAGs removed to delete all port-channels
        config_commands.append("no mlag configuration")
        # Remove all port-channel interfaces and delete channel-group, switchport, and descriptions of all interfaces
        for interface in interfaces:
            if 'interface Port-Channel' in interface:
                config_commands.append("no " + interface)
            elif 'interface Ethernet' in interface:
                config_commands = config_commands + [interface, 'no channel-group', 'no switchport',
                                                     'no switchport mode', 'no switchport access vlan',
                                                     'no switchport trunk group', 'no switchport trunk native vlan',
                                                     'no switchport trunk allowed vlan',
                                                     'no description', 'no mtu']
        # Run the commands
        self.runconfig(config_commands)

    def getInterfaces(self):
        self.interfaceList = []
        output = self.runcommand("show running-config")
        output = output.splitlines()
        # Get all interfaces
        for line in output:
            # if 'interface ' in line and 'port-channel' not in line:
            if ('interface Ethernet' in line) or ('interface Port-Channel' in line):
                self.interfaceList.append(line.strip())
        return self.interfaceList

    def getMACTable(self, force = False):
        if force:
            output = self.runcommand("clear mac address-table dynamic")
            time.sleep(10)
        self.MACTable = {}
        output = self.runcommand("show mac address-table")
        output = output.splitlines()
        for line in output:
            if '.' in line:
                # Remove the special character in the front
                line = line[1:]
                # Split the line
                splited = line.split()
                try:
                    mac = splited[1].replace(".","").lower()
                    vlan = splited[0]
                    port = splited[3]
                except:
                    # If splited can't be accessed, go to next line
                    continue
                self.MACTable.update({mac:{"vlan": vlan, "port": port}})

        return self.MACTable

    def whereisMAC(self, MAC, forcecheck = False):
        if len(self.MACTable) < 1 or forcecheck:
            self.getMACTable()
        MAC = str(MAC)
        # Strip random chars
        MAC = re.sub('[:.-]', '', MAC)
        # MAC = '.'.join(MAC[i:i+4] for i in range(0,12,4))
        MAC = MAC.lower()
        try:
            return self.MACTable[MAC]["port"]
        except:
            return None

    def setInterfaceVLANs(self, interfaces, VLANs = []):
        self._setInterfaceVLANs(interfaces, VLANs, True)

    # Sub command for setting interface
    def _setInterfaceVLANs(self, interfaces = [], VLANs = [], deleteOldConfig = True):
        # Force add all VLANs
        config_commands = []
        # vlangroup = "MainVLANs"
        for vlan in VLANs:
            config_commands.append("vlan " + str(vlan))
            # config_commands.append("trunk group " + vlangroup)
            config_commands.append("no trunk group")

        for interface in interfaces:
            # Add interface word if its not in interface
            if "interface " not in interface:
                interface = "interface " + interface

            # Force delete config interface
            if deleteOldConfig:
                config_commands = config_commands + [interface, "no channel-group", "no switchport"]
            else:
                config_commands.append(interface)

            # If the VLANs is not empty, add switchport delegation
            if len(VLANs) > 0:
                config_commands.append("switchport")

            # If there is only one VLAN, set as access port
            if len(VLANs) == 1:
                config_commands = config_commands + ["switchport mode access", "switchport access vlan " + str(VLANs[0])]

            # If there is two or more VLANs, set as trunk port
            elif len(VLANs) > 1:
                config_commands.append("switchport mode trunk")
                # config_commands.append("switchport trunk group " + vlangroup)
                # Trunk Group will break proper switch functionality within Arista for non-peerlink connections
                vlanstring = ""
                for vlan in VLANs:
                    vlanstring = vlanstring + str(vlan) + ","
                vlanstring = vlanstring[:-1]
                config_commands.append("switchport trunk allowed vlan " + vlanstring)
                # Add 1st vlan as native vlan
                config_commands.append("switchport trunk native vlan " + str(VLANs[0]))
            config_commands.append("no shutdown")
        self.runconfig(config_commands)

    def setMTU(self, interfaces = [], MTU = "1500"):
        # Get latest runningconfig
        self.getRunningConfig()
        # If interfaces is empty, use all interfaces
        if len(interfaces) < 1:
            interfaces = self.interfaceList
        # Force set MTU to all interfaces
        config_commands = []
        # Filter Interfaces to only those with switchport settings
        switchinterfaces = []
        for intname, intdetails in self.interfaceDetails.items():
            if ("switchport-mode" in intdetails) and (intname in interfaces):
                switchinterfaces.append(intname)

        # Set MTU settings
        for interface in switchinterfaces:
            # Add interface word if its not in interface
            if "interface " not in interface:
                interface = "interface " + interface
            config_commands = config_commands + [interface, "mtu " + str(MTU)]
        self.runconfig(config_commands)



    def setPortChannelInterface(self, portchannel_num, interfaces, VLANs = [], description = None, ident = None):
        # Populate MLAG id with portchannel_num if id is empty and if its not a mgmt switch
        if (ident is None) and (self.type != "mgmt"):
            ident = int(portchannel_num)

        # Make sure number is a string
        portchannel_num = str(portchannel_num)

        # Remove the word interface from list
        temp_interfaces = []
        for interface in interfaces:
            if 'interface ' in interface:
                temp_interfaces.append(interface.split("interface ")[-1])
            else:
                temp_interfaces.append(interface)
        interfaces = temp_interfaces

        # Tell user what we are doing
        msg = self.host + " Creating interface port-channel " + portchannel_num + " with "
        for interface in interfaces:
            msg = msg + interface + ","
        msg = msg.rstrip(",") + " and with VLAN(s) "
        for vlan in VLANs:
            msg = msg + str(vlan) + ","
        msg = msg.rstrip(",")
        print(msg)

        # Force add all VLANs and group them to MainVLANs
        config_commands = []

        if ident == "peer-link":
            vlangroup = "peer-link"
        else:
            vlangroup = "MainVLANs"

        for vlan in VLANs:
            config_commands.append("vlan " + str(vlan))
            if ident == "peer-link":
                config_commands.append("trunk group " + vlangroup)
            else:
                config_commands.append("no trunk group")

        # Remove port-channel with existing number
        config_commands.append("no interface port-channel " + portchannel_num)

        # Shutdown and remove switchport and channel-group configs on all interfaces to prevent loops
        for interface in interfaces:
            config_commands = config_commands + ['interface ' + interface, "shutdown", "no channel-group", "no switchport"]

        # Add all VLANs and descriptions to port-channel and interfaces
        for interface in list(["port-channel " + portchannel_num] + interfaces):
            config_commands.append("interface " + interface)

            # Set speed to auto to everything
            # config_commands.append("speed auto")

            # Add the description if any
            if description is not None:
                config_commands.append("description " + description)

            if len(VLANs) >= 0:
                config_commands.append("switchport")
            # If there is only one VLAN and its not a peer-link, set as access port
            if (len(VLANs) == 1) and (ident != 'peer-link'):
                config_commands = config_commands + ["switchport mode access",
                                                     "switchport access vlan " + str(VLANs[0])]

            # If there is two or more VLANs or if the link a peer-link, set as trunk port
            elif len(VLANs) > 1 or ident == 'peer-link':
                config_commands.append("switchport mode trunk")
                if ident == 'peer-link':
                    config_commands.append("switchport trunk group " + vlangroup)

            # If there is a MLAG (except Peer-Link) and we are in a port-channel interface, add the mlag setting
            if (ident is not None) and ("port-channel" in interface):
                if (ident != "peer-link"):
                    config_commands.append("mlag " + str(ident))

        # Add channel-group settings to each interface
        for interface in interfaces:
            config_commands = config_commands + ["interface " + interface, "channel-group " + portchannel_num + " mode active"]

        # Power on interfaces
        for interface in list(["port-channel " + portchannel_num] + interfaces):
            config_commands = config_commands + ["interface " + interface, "no shutdown"]

        # Run the config
        self.runconfig(config_commands)

    def setSerdes(self, interfaces, speed):
        print(self.host + " This host doesn't support serdes settings.")

class DCS7010(aristaeos):
    def __init__(self, host, username, password):
        aristaeos.__init__(self, host, username, password)
        self.model = "DCS-7010T-48-R"
        self.Usize = 1
        self.type = "mgmt"

    def setInterfaceVLANs(self, interface, VLANs = []):
        interface = "interface Et1-48"
        VLANs=[VLANs[0]]
        self._setInterfaceVLANs([interface], VLANs, deleteOldConfig=False)

    def resetAllInterfaces(self):
        # Get latest interfaces
        temp_interfaces = self.getInterfaces()
        # Preserve all port-channels and remove eth1/1-48 from list
        interfaces = []
        for interface in temp_interfaces:
            if 'interface Port-Channel' in interface:
                interfaces.append(interface)
        interfaces = interfaces + ['interface Ethernet49', 'interface Ethernet50', 'interface Ethernet51'
                                   ]
        # Start resetting procedure
        self._resetInterfaces(interfaces)
        return True

class DCS7050SX3(aristaeos):
    def __init__(self, host, username, password):
        aristaeos.__init__(self, host, username, password)
        self.model = "DCS-7050SX3-48YC8-R"
        self.Usize = 1
        self.type = "leaf"

    def setSerdes(self, interfaces, speed):
        serdesList = set([])
        if "10g" == speed or "25g" == speed:
            pass
        else:
            return False
        # Determine the serdes list
        for interface in interfaces:
            # Only get SFP+ Interfaces
            if '/' not in interface:
                try:
                    intnum = interface.split("Ethernet")[-1]
                    # Adding three to have 1-4 output 1, 5-8 output 2, etc
                    intnum = int(intnum) + 3
                    serde = int(intnum / 4)
                    serdesList.add(serde)
                except:
                    continue
        # Configure the serdes interfaces
        config_commands = []
        for serde in serdesList:
            serde = str(serde)
            # Disable any old config
            config_commands = config_commands + ["no hardware speed-group " + serde + " serdes ", "y"]
            # Enable serdes
            config_commands = config_commands + ["hardware speed-group " + serde + " serdes " + speed, "y"]

        self.runconfig(config_commands)

class DCS7050CX3(aristaeos):
    def __init__(self, host, username, password):
        aristaeos.__init__(self, host, username, password)
        self.model = "DCS-7050CX3-32S-R"
        self.Usize = 1
        self.type = "spine"
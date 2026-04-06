from netmiko import ConnectHandler
import time
import re
import switches
import ipaddress

# SubModule Logging
import logging
logger = logging.getLogger("root")

class cisconexus(switches.switch):
    def __init__(self, host, username, password):
        switches.switch.__init__(self, host, username, password)
        self.deviceType = "cisco_nxos_ssh"
        self.mgmtInterface = "mgmt0"
        self.vpcdomainid = ''
        self.interfaceList = []
        self.interfaceDetails = {}
        # Detail Format {"__interface_name__" : {"channel-group":1, "channel-group-mode": "active", "vpc":1, "switchport-mode":"trunk", "native-vlan":1, "vlans":[1,2,3,4]}}
        self.VLANList = []
        self.MACTable = {}
        self.runningconfig = ""
        self.getDetails()
        self.getInterfaces()
        self.getVLANs()
        # self.getRunningConfig()

    # Gets the basic details of the node
    def getDetails(self):
        self.getName()
        self.getMGMTMAC()

    def getName(self):
        output = self.runcommand('show switchname')
        self.name = output.strip()
        return self.name

    def setName(self, switchname):
        config_commands = ["hostname " + switchname]
        self.runconfig(config_commands)
        self.name = switchname
        return self.name

    def enableAPI(self):
        config_commands = ["feature nxapi", "nxapi sandbox"]
        self.runconfig(config_commands)

    def updateUserPass(self, username, password):
        if username is not "admin":
            print(self.host + " doesn't support changing password for " + username)
            return False
        config_commands = ["username " + username + " password " + password]
        self.runconfig(config_commands)
        self.password = password
        return True

    def getIPv4MGMT(self):
        # Get the latest runningconfig
        runningconfig = self.getRunningConfig()

        # Get the IP address and gateway
        IPv4MGMTAddress = ''
        IPv4Gateway = ''
        for line in runningconfig.splitlines():
            if '  ip address' in line:
                IPv4MGMTAddress = line.split()[-1]
            elif '  ip route' in line:
                IPv4Gateway = line.split()[-1]

        self.hostIPv4Address = IPv4MGMTAddress
        self.hostIPv4Gateway = IPv4Gateway
        return IPv4MGMTAddress, IPv4Gateway

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
                           'vrf context management',
                           'no ip route 0.0.0.0/0 ' + self.hostIPv4Gateway]
        self.runconfig(config_commands)

        # Set new mgmt address and gateway
        config_commands = ['interface ' + self.mgmtInterface,
                           'ip address ' + str(mgmtinterface),
                           'exit',
                           'vrf context management',
                           'ip route 0.0.0.0/0 ' + str(gateway)]
        self.runconfig(config_commands)

        # Store new address and gateway in class
        self.getIPv4MGMT()

        # Doublecheck if setting was set
        # DO LATER

        return True

    def getMGMTMAC(self):
        output = self.runcommand('show interface mgmt 0 | grep address:')
        try:
            self.mgmtMAC = output.split("address:")[1].split()[0].replace('.','')
            return self.mgmtMAC
        except:
            return None

    def getVPC(self):
        output = self.getRunningConfig()
        vpcdomainid = ''
        for line in output.splitlines():
            if 'vpc domain ' in line:
                vpcdomainid = line.split()[-1]
                break

        self.vpcdomainid = vpcdomainid
        return vpcdomainid

    def setVPC(self, vpcdomainid = 1 , priority = 10, ipv4AddressOfOtherSwitch = '' , peerlinkportchannel = '', peerlinkinterfaces = []):
        # Start config commands list
        config_commands = []

        # Get the latest vpc domainid
        oldid = self.getVPC()

        # Make sure the host address is available
        # self.getIPv4MGMT()

        # If an ID exists, delete old VPC
        if len(oldid) > 0:
            output = self.runconfig("no vpc domain " + oldid)
            if "delete in progress" in output:
                time.sleep(60)

        # Setup the new VPC Domain Settings
        config_commands = config_commands + ['vpc domain ' + str(vpcdomainid),
                                             'yes',
                                             'peer-switch',
                                             'role priority ' + str(priority),
                                             # hostIPv4Address may have the subnet CIDR. We attempt to remove that
                                             'peer-keepalive destination ' + str(ipv4AddressOfOtherSwitch).split('/')[0] + ' source ' + self.hostIPv4Address.split('/')[0] + ' vrf management',
                                             'delay restore 240',
                                             'peer-gateway',
                                             'ipv6 nd synchronize',
                                             'ip arp synchronize',
                                             'auto-recovery',]
        self.runconfig(config_commands)

        # Set the new vpc domainid
        self.getVPC()

        # Set the port-channel and interfaces for peerlink
        self.setPortChannelInterface(portchannel_num=peerlinkportchannel, interfaces=peerlinkinterfaces, description='vpc peer-link', VLANs=[], ident="peer-link")

        # Check if VPC changed
        # Do later
        return self.vpcdomainid

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
            if (interfacekey is not None) and (len(interfacedict) >= 0) and len(line) < 1:
                self.interfaceDetails.update({interfacekey:interfacedict})
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
                            startvlan,endvlan = tempvlan.split('-')
                            for vlan in range(int(startvlan),int(endvlan),1):
                                vlans.append(vlan)
                        else:
                            try:
                                vlans.append(int(tempvlan))
                            except:
                                vlans.append(tempvlan)
                    interfacedict.update({"vlans" : vlans})
                    continue
                elif "  vpc" in line:
                    interfacedict.update({"vpc": str(line.split()[-1])})
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



        return self.runningconfig

    def saveRunningConfig(self):
        command = "copy running-config startup-config"
        output = self.runcommand(command)
        if "Copy complete" in output:
            return True
        else:
            return False

    def resetAllInterfaces(self):
        # Get latest interfaces
        interfaces = self.getInterfaces()
        # Start reseting procedure
        self._resetInterfaces(interfaces)
        return True

    def _resetInterfaces(self, interfaces):
        config_commands = []
        # Remove all port-channel interfaces and delete channel-group, switchport, and descriptions of all interfaces
        for interface in interfaces:
            if 'interface port-channel' in interface:
                config_commands.append("no " + interface)
            elif 'interface Ethernet' in interface:
                config_commands = config_commands + [interface, 'no channel-group', 'no switchport', 'no description']
        # Run the commands
        self.runconfig(config_commands)

    def getInterfaces(self):
        self.interfaceList = []
        output = self.runcommand("show running-config interface")
        output = output.splitlines()
        # Get all interfaces
        for line in output:
            # if 'interface ' in line and 'port-channel' not in line:
            if ('interface Ethernet' in line) or ('interface port-channel' in line):
                self.interfaceList.append(line.strip())
        return self.interfaceList

    def getVLANs(self):
        self.VLANList = []
        output = self.runcommand("show running-config vlan")
        output = output.splitlines()
        # Get all VLANs
        for line in output:
            if 'vlan ' in line:
                # Remove vlan word
                line = line.replace("vlan ", "")
                # Split by commas
                line = line.split(",")
                # Get VLANs from the line
                for vlan in line:
                    # If a - exists, add VLAN range
                    if '-' in vlan:
                        start, end = vlan.split("-")
                        for vlan in range(int(start),int(end)+1):
                            self.VLANList.append(str(vlan))
                    else:
                        self.VLANList.append(str(vlan))
        self.VLANList = list(set(self.VLANList))
        return self.VLANList

    def setFeature(self, name):
        config_commands = ['feature ' + name]
        self.runconfig(config_commands)

    def blinkInterface(self, interface, status = True):
        config_commands = [interface]
        if status:
            config_commands.append('beacon')
            msg = self.host + ' Turning on Blinking LED on ' + interface
        else:
            config_commands.append('no beacon')
            msg = self.host + ' Turning off Blinking LED on ' + interface
        self.runconfig(config_commands)
        print(msg)

    def powerOFFInterface(self, interface):
        config_commands = [interface, "shutdown"]
        self.runconfig(config_commands)

    def powerONInterface(self, interface):
        config_commands = [interface, "no shutdown"]
        self.runconfig(config_commands)

    def clearMACTable(self):
        output = self.runcommand("clear mac address-table dynamic")

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
                    port = splited[-1]
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

    # Note: Just returns first item!
    def whatisinPORT(self, port, forcecheck = False):
        port = str(port)
        if 'Eth' not in port:
            port = "Eth1/" + port
        if len(self.MACTable) < 1 or forcecheck:
            self.getMACTable()
        for key, value in self.MACTable.items():
            try:
                if value['port'] == port:
                    return key
            except:
                continue
        return None

    # Main command for most Cisco Switches
    def setInterfaceVLANs(self, interfaces, VLANs = []):
        self._setInterfaceVLANs(interfaces, VLANs, True)

    # Sub command for setting interface
    def _setInterfaceVLANs(self, interfaces = [], VLANs = [], deleteOldConfig = True):
        # Force add all VLANs
        config_commands = []
        for vlan in VLANs:
            config_commands.append("vlan " + str(vlan))

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
                vlan_str = "switchport trunk allowed vlan "
                for vlan in VLANs:
                    vlan_str = vlan_str + str(vlan) + ","
                config_commands.append(vlan_str.rstrip(","))
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
        config_commands = ["system jumbomtu " + str(MTU)]
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
        # Populate VPC id with portchannel_num if id is empty
        if ident is None:
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

        # Force add all VLANs
        config_commands = []
        for vlan in VLANs:
            config_commands.append("vlan " + str(vlan))

        # Remove port-channel with existing number
        config_commands.append("no interface port-channel " + portchannel_num)

        # Shutdown and remove switchport and channel-group configs on all interfaces to prevent loops
        for interface in interfaces:
            config_commands = config_commands + ['interface ' + interface, "shutdown", "no channel-group", "no switchport"]

        # Add all VLANs and descriptions to port-channel and interfaces
        for interface in list(["port-channel " + portchannel_num] + interfaces):
            config_commands.append("interface " + interface)

            # Set speed to auto to everything
            config_commands.append("speed auto")

            # Add the description if any
            if description is not None:
                config_commands.append("description " + description)

            if len(VLANs) >= 0:
                config_commands.append("switchport")
            # If there is only one VLAN, set as access port
            if len(VLANs) == 1:
                config_commands = config_commands + ["switchport mode access",
                                                     "switchport access vlan " + str(VLANs[0])]
            # If there is two or more VLANs or if the link a peer-link, set as trunk port
            elif len(VLANs) > 1 or ident == 'peer-link':
                config_commands.append("switchport mode trunk")
                # If vpc is a peer-link, do not add the VLANs. Aka allow all.
                if ident != 'peer-link':
                    vlan_str = "switchport trunk allowed vlan "
                    for vlan in VLANs:
                        vlan_str = vlan_str + str(vlan) + ","

                    config_commands.append(vlan_str.rstrip(","))

            # If there is a VPC and we are in a port-channel interface, add the VPC setting
            if (ident is not None) and ("port-channel" in interface):
                config_commands.append("vpc " + str(ident))

        # Add channel-group settings to each interface
        for interface in interfaces:
            config_commands = config_commands + ["interface " + interface, "channel-group " + portchannel_num + " mode active"]

        # Power on interfaces
        for interface in list(["port-channel " + portchannel_num] + interfaces):
            config_commands = config_commands + ["interface " + interface, "no shutdown"]

        # Run the config
        self.runconfig(config_commands)

class Nexus92348(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "C92348GC-X"
        self.Usize = 1
        self.type = "mgmt"

    # Note: To prevent 92348 from losing connectivety to all out-of-band mangement conenctions, this command will work only work on first 48 ethernet ports. This command will only allow access mode on switch.
    def setInterfaceVLANs(self, interface, VLANs = []):
        interface = "interface eth1/1-48"
        VLANs=[VLANs[0]]
        self._setInterfaceVLANs([interface], VLANs, deleteOldConfig=False)

    # Note: To prevent 92348 from losing connectivety to all out-of-band mangement conenctions, this command will work only work on first 48 ethernet ports. This command will only allow access mode on switch.
    def resetAllInterfaces(self):
        # Get latest interfaces
        temp_interfaces = self.getInterfaces()
        # Preserve all port-channels and remove eth1/1-48 from list
        interfaces = []
        for interface in temp_interfaces:
            if 'interface port-channel' in interface:
                interfaces.append(interface)
        interfaces = interfaces + ['interface Ethernet1/49', 'interface Ethernet1/50', 'interface Ethernet1/51', 'interface Ethernet1/52']
        # Start resetting procedure
        self._resetInterfaces(interfaces)
        return True

class Nexus93180YCFX(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "C93180YC-FX"
        self.Usize = 1
        self.type = "leaf"


class Nexus93180YCFX3(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "C93180YC-FX3"
        self.Usize = 1
        self.type = "leaf"

class Nexus9332C(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "9332C"
        self.Usize = 1
        self.type = "spine"
        
class Nexus93600CD(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "93600-CD"
        self.Usize = 1
        self.type = "spine"
        
class Nexus93600CDGX(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "C93600CD-GX"
        self.Usize = 1
        self.type = "spine"

class Nexus9316D(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "C9316D-GX"
        self.Usize = 1
        self.type = "spine"

        
    '''
class Nexus3048(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "N3K-3048"
        self.Usize = 1
        self.type = "mgmt"

    # Note: To prevent 3048 from losing connectivety to all out-of-band mangement conenctions, this command will work only work on first 48 ethernet ports. This command will only allow access mode on switch.
    def setInterfaceVLANs(self, interface, VLANs = []):
        interface = "interface eth1/1-48"
        VLANs=[VLANs[0]]
        self._setInterfaceVLANs([interface], VLANs, deleteOldConfig=False)

    # Note: To prevent 3048 from losing connectivety to all out-of-band mangement conenctions, this command will work only work on first 48 ethernet ports. This command will only allow access mode on switch.
    def resetAllInterfaces(self):
        # Get latest interfaces
        temp_interfaces = self.getInterfaces()
        # Preserve all port-channels and remove eth1/1-48 from list
        interfaces = []
        for interface in temp_interfaces:
            if 'interface port-channel' in interface:
                interfaces.append(interface)
        interfaces = interfaces + ['interface Ethernet1/49', 'interface Ethernet1/50', 'interface Ethernet1/51', 'interface Ethernet1/52']
        # Start resetting procedure
        self._resetInterfaces(interfaces)
        return True

class Nexus93180YCEX(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "93180YC-EX"
        self.Usize = 1
        self.type = "leaf"

class Nexus93180LCEX(cisconexus):
    def __init__(self, host, username, password):
        cisconexus.__init__(self, host, username, password)
        self.model = "93180LC-EX"
        self.Usize = 1
        self.type = "spine"
    '''

'''
test = cisconexus('fe80::a23d:6fff:fefe:2b40%13', 'admin', 'Passw0rd!')
print('Loaded')
test.getName()

# test.getVLANs()
test.setPortChannelInterface(99, ["interface ethernet1/51", "interface ethernet1/52"], [48,49,50])
test.setInterfaceVLANs("interface ethernet1/51")
test.blinkInterface(test.interfaceList[0], True)
time.sleep(5)
test.blinkInterface(test.interfaceList[0], False)
'''
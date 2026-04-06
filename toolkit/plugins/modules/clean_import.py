# Clean import section for real switch classes
import sys
import os

# Add module_utils to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'module_utils'))

# Global logger - will be set during main() execution
logger = None

# Import real switch classes
try:
    # Create minimal switches base class if missing
    try:
        import switches
    except ImportError:
        import types
        switches = types.ModuleType('switches')
        
        class switch:
            def __init__(self, host, username='admin', password='admin', enable_password='', device_type='cisco_nexus'):
                self.host = host
                self.username = username
                self.password = password
                self.enable_password = enable_password
                self.device_type = device_type
                self.hostIPv4Address = host
                self.name = f"Switch-{host}"
                self.model = "Unknown"
                self.type = "Unknown"
                self.interfaceList = []
                self.interfaceDetails = {}
        
        switches.switch = switch
        sys.modules['switches'] = switches

    # Import real switch modules
    import cisconexus
    import aristaeos

    # Switch class mapping
    CISCO_SWITCH_CLASSES = {
        'Nexus92348': cisconexus.Nexus92348,
        'Nexus93180YCFX': cisconexus.Nexus93180YCFX,  
        'Nexus93180YCFX3': cisconexus.Nexus93180YCFX3,
        'Nexus9332C': cisconexus.Nexus9332C,
        'Nexus93600CD': cisconexus.Nexus93600CD,
        'Nexus93600CDGX': cisconexus.Nexus93600CDGX,
        'Nexus9316D': cisconexus.Nexus9316D
    }
    
    ARISTA_SWITCH_CLASSES = {
        'DCS7010': aristaeos.DCS7010,
        'DCS7050SX3': aristaeos.DCS7050SX3,
        'DCS7050CX3': aristaeos.DCS7050CX3
    }
    
    REAL_SWITCHES_AVAILABLE = True

except ImportError as e:
    # Fallback mock classes
    REAL_SWITCHES_AVAILABLE = False
    CISCO_SWITCH_CLASSES = {}
    ARISTA_SWITCH_CLASSES = {}
    import_error_msg = str(e)
    
    class cisco_switch:
        def __init__(self, host, username, password):
            self.host = host
            self.username = username
            self.password = password
            self.model = "Unknown"
            self.type = "Unknown"
            self.name = f"Switch-{host}"
            self.hostIPv4Address = host
            self.interfaceList = [f"Eth1/{i}" for i in range(1, 49)]
            self.interfaceDetails = {}
            
        def enableAPI(self):
            print(f"{self.name}: Enabling HTTP API")
            return True
            
        def updateUserPass(self, username, password):
            print(f"{self.name}: Updating password for user {username}")
            return True
            
        def setName(self, name):
            print(f"{self.name}: Setting hostname to {name}")
            self.name = name
            return True
            
        def setIPv4MGMT(self, ip, subnet, gateway):
            print(f"{self.name}: Setting management IP {ip}/{subnet} gateway {gateway}")
            return True
            
        def getIPv4MGMT(self):
            print(f"{self.name}: Getting management IP address")
            return self.hostIPv4Address
            
        def resetAllInterfaces(self):
            print(f"{self.name}: Resetting all interface configurations")
            return True
            
        def setFeature(self, feature):
            print(f"{self.name}: Enabling feature {feature}")
            return True
            
        def setVPC(self, vpcdomainid, priority, ipv4AddressOfOtherSwitch, peerlinkportchannel, peerlinkinterfaces):
            print(f"{self.name}: Setting up VPC domain {vpcdomainid} with peer {ipv4AddressOfOtherSwitch}")
            return True
            
        def setMLAGPeering(self, mlagDomainID, peerportChannel, interfaces, peerVLAN, localipv4address, peeripv4address):
            print(f"{self.name}: Setting up MLAG domain {mlagDomainID}")
            return True
            
        def setPortChannelInterface(self, portchannel_num, interfaces, description, VLANs):
            print(f"{self.name}: Creating port-channel {portchannel_num} with {len(interfaces)} interfaces")
            return True
            
        def setInterfaceVLANs(self, interfaces, vlans):
            print(f"{self.name}: Setting VLANs {vlans} on {len(interfaces)} interfaces")
            return True
            
        def setMTU(self, MTU):
            print(f"{self.name}: Setting MTU to {MTU}")
            return True
            
        def saveRunningConfig(self):
            print(f"{self.name}: Saving running configuration")
            return True
            
        def getMACTable(self, force=False):
            print(f"{self.name}: Getting MAC address table")
            return True
            
        def whereisMAC(self, mac):
            print(f"{self.name}: Looking for MAC {mac}")
            return f"Eth1/1"
            
        def getRunningConfig(self):
            print(f"{self.name}: Getting running configuration")
            self.interfaceDetails = {}
            return True
            
    class arista_switch:
        def __init__(self, host, username, password):
            self.host = host
            self.username = username
            self.password = password
            self.model = "Unknown"
            self.type = "Unknown"
            self.name = f"Switch-{host}"
            self.hostIPv4Address = host
            self.interfaceList = [f"Ethernet{i}" for i in range(1, 49)]
            self.interfaceDetails = {}
            
        def enableAPI(self):
            print(f"{self.name}: Enabling HTTP API")
            return True
            
        def updateUserPass(self, username, password):
            print(f"{self.name}: Updating password for user {username}")
            return True
            
        def setName(self, name):
            print(f"{self.name}: Setting hostname to {name}")
            self.name = name
            return True
            
        def setIPv4MGMT(self, ip, subnet, gateway):
            print(f"{self.name}: Setting management IP {ip}/{subnet} gateway {gateway}")
            return True
            
        def getIPv4MGMT(self):
            print(f"{self.name}: Getting management IP address")
            return self.hostIPv4Address
            
        def resetAllInterfaces(self):
            print(f"{self.name}: Resetting all interface configurations")
            return True
            
        def setFeature(self, feature):
            print(f"{self.name}: Enabling feature {feature}")
            return True
            
        def setVPC(self, vpcdomainid, priority, ipv4AddressOfOtherSwitch, peerlinkportchannel, peerlinkinterfaces):
            print(f"{self.name}: Setting up VPC domain {vpcdomainid} with peer {ipv4AddressOfOtherSwitch}")
            return True
            
        def setMLAGPeering(self, mlagDomainID, peerportChannel, interfaces, peerVLAN, localipv4address, peeripv4address):
            print(f"{self.name}: Setting up MLAG domain {mlagDomainID}")
            return True
            
        def setPortChannelInterface(self, portchannel_num, interfaces, description, VLANs):
            print(f"{self.name}: Creating port-channel {portchannel_num} with {len(interfaces)} interfaces")
            return True
            
        def setInterfaceVLANs(self, interfaces, vlans):
            print(f"{self.name}: Setting VLANs {vlans} on {len(interfaces)} interfaces")
            return True
            
        def setMTU(self, MTU):
            print(f"{self.name}: Setting MTU to {MTU}")
            return True
            
        def saveRunningConfig(self):
            print(f"{self.name}: Saving running configuration")
            return True
            
        def getMACTable(self, force=False):
            print(f"{self.name}: Getting MAC address table")
            return True
            
        def whereisMAC(self, mac):
            print(f"{self.name}: Looking for MAC {mac}")
            return f"Ethernet1"
            
        def getRunningConfig(self):
            print(f"{self.name}: Getting running configuration")
            self.interfaceDetails = {}
            return True

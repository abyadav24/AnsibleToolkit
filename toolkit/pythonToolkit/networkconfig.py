import datetime
import os
import autodiscover
import badtime
import helper
import aristaeos
import cisconexus
import brocadefc
import json
import time
import operator
import lawcompliance
import toolkit_config
import loginit
import logging
logger = logging.getLogger("root")

TESTING = False  # Set this to False for production. When TESTING, switch config won't be saved to startup config

CISCO_SWITCH_LIST = ["93180YC", "9332C", "92348", "93600CD", "C9316D-GX"]
LACP_LLDP_SWITCH_LIST = ["93180YC", "9332C", "92348", "93600CD", "C9316D-GX"]
VCP_SWITCH_LIST = ["93180YC", "9332C", "93600CD", "C9316D-GX"]

class networkstack(object):
    def __init__(self, racknum, switches = [], networkconfigjson = None, design = None):
        self.racknum = str(racknum)

        # All Possible UCP CI/HC/RS Designs
        # TO DO: MUST UPDATE BELOW DESIGNS!!!
        self.designs = {
            "Simple-Rack_Cisco" : {
                "Nexus93180YCFX" : 2,
                "Nexus92348" : 1,
            },
            "Simple-FC-Rack_Cisco": {
                "Nexus93180YCFX" : 2,
                "Nexus92348" : 1,
                "G620" : 2
            },
            "Expand-Rack_Cisco": {
                "Nexus9332C" : 2,
                "Nexus93180YCFX" : 2,
                "Nexus92348" : 1,
            },
            "Expand-FC-Rack_Cisco": {
                "Nexus9332C": 2,
                "Nexus93180YCFX": 2,
                "Nexus92348": 1,
                "G620": 2
            },
            "Simple-Rack_Arista": {
                "DCS7050SX3": 2,
                "DCS7010": 1,
            },
            "Simple-FC-Rack_Arista": {
                "DCS7050SX3": 2,
                "DCS7010": 1,
                "G620": 2
            },
            "Expand-Rack_Arista": {
                "DCS7050CX3": 2,
                "DCS7050SX3": 2,
                "DCS7010": 1,
            },
            "Expand-FC-Rack_Arista": {
                "DCS7050CX3": 2,
                "DCS7050SX3": 2,
                "DCS7010": 1,
                "G620": 2
            },
            "Cisco_Multi_R1_G620": {
                'Nexus93180YCFX3': 2,
                'G620': 2,
                'Nexus92348': 1,
                "Nexus93600CDGX": 2
            },
            "Cisco_Multi_R1_G720": {
                'Nexus93180YCFX3': 2,
                'G720': 2,
                'Nexus92348': 1,
                "Nexus93600CDGX": 2
            },
            "Cisco_Multi_R2-R4_G620": {
                'Nexus93180YCFX3': 2,
                'G620': 2,
                'Nexus92348': 1
            },
            "Cisco_Multi_R2-R4_G720": {
                'Nexus93180YCFX3': 2,
                'G720': 2,
                'Nexus92348': 1
            },
            "Cisco_Single": {
                'Nexus93180YCFX3': 2,
                'G620': 2,
                'Nexus92348': 1
            },
            "100G-To-The-Host_Multi_R1_G620": {
                'Nexus9316D': 2,
                'G620': 2,
                'Nexus92348': 1,
                "Nexus93600CDGX": 2
            },
            "100G-To-The-Host_Multi_R1_G720": {
                'Nexus9316D': 2,
                'G720': 2,
                'Nexus92348': 1,
                "Nexus93600CDGX": 2
            },
            "100G-To-The-Host_Multi_R2-R4_G620": {
                'G620': 2,
                'Nexus92348': 1,
                "Nexus93600CDGX": 2
            },
            "100G-To-The-Host_Multi_R2-R4_G720": {
                'G720': 2,
                'Nexus92348': 1,
                "Nexus93600CDGX": 2
            },
            "100G-To-The-Host_Single": {
                'Nexus92348': 1,
                "Nexus93600CDGX": 2  
            },
            "100G-To-The-Host_Multi_100G-TCP-NVMe_R1": {
                'Nexus9316D': 2,
                'Nexus92348': 1,
                "Nexus93600CDGX": 2
            },
            "100G-To-The-Host_Multi_100G-TCP-NVMe_R2-R4": {
                'Nexus92348': 1,
                "Nexus93600CDGX": 2
            },
            "Toolkit_Lab": {
                'Nexus93180YCFX3': 1,
                'G620': 2,
                'Nexus92348': 1,
                "Nexus93600CDGX": 2,
                #"G720": 1,  
                'Nexus9316D': 2,

            }
        }

        # Interface Locations of switches on 92348
        self.placements = {
            "Nexus9332C" : ("1/37", "1/38"),
            "Nexus93180YCFX" : ("1/39", "1/40"),
            "Nexus93600CD" : ("1/37", "1/38"),
            "Nexus93180YCFX3" : ("1/39", "1/40"),
            "G620" : ("1/41", "1/42"),
            "Nexus92348" : ("1/45", " ")
        }

        # Getting ready for Nexus93180YCFX3
        # self.placements = {HA
        #     "Nexus9332C": ("1/37", "1/38"),
        #     "Nexus93180YCFX3": ("1/39", "1/40"),
        #     "G620": ("1/41", "1/42"),
        #     "Nexus92348": ("1/45", " ")
        # }

        # Default port-channel ethernet ports
        self.portchannelinterfaces = {
            "default" : {
                "spine" : {
                    "peer": {"start": -14, "end": -6},
                    "customerQSFP" : {"start": -6, "end": None},
                    "leaf": {},
                },
                "leaf" : {
                    "peer": {"start": -2, "end": None},
                    "spine": {"start": -6, "end": -4},
                    # Default on documentation
                    "mgmt1": {"start": -14, "end": -13},
                    # Default on rack and stack single network
                    "mgmt2": {"start": -7, "end": -6},
                    # Default for designs with Spine Switch
                    "customerQSFP": {"start": -6, "end": -2},
                    # Default for all designs
                    "customerSFP": {"start": -22, "end": -14}
                },
                "mgmt" : {
                    "leaf": {"start": -4, "end": -2}
                }
            },
            "default_Cisco": {
                "spine": {
                    "peer": {"start": -16, "end": -8},
                    "customerQSFP": {"start": -8, "end": -4},
                    "leaf": {},
                },
                "leaf": {
                    "peer": {"start": -2, "end": None},
                    "spine": {"start": -6, "end": -4},
                    # Default on documentation
                    #"mgmt1": {"start": -14, "end": -13},
                    "mgmt1": {"start": -7, "end": -6},
                    # Default on rack and stack single network
                    # "mgmt2": {"start": -7, "end": -6},
                    # Default for designs with Spine Switch
                    "customerQSFP": {"start": -6, "end": -2},
                    # Default for all designs
                    "customerSFP": {"start": -22, "end": -14}
                },
                "mgmt": {
                    #"leaf": {"start": -4, "end": -2}
                    #Cisco 92348 specific info below
                    "leaf": {"start": -6, "end": -4}
                }
            },
            "default_Arista": {
                "spine": {
                    "peer": {"start": -14, "end": -6},
                    "customerQSFP": {"start": -6, "end": -2},
                    "leaf": {},
                },
                "leaf": {
                    "peer": {"start": -4, "end": -2},
                    "spine": {"start": -8, "end": -6},
                    # Default on documentation
                    "mgmt1": {"start": -16, "end": -15},
                    # Default on rack and stack single network
                    # "mgmt2": {"start": -7, "end": -6},
                    # Default for designs with Spine Switch
                    "customerQSFP": {"start": -8, "end": -4},
                    # Default for all designs
                    "customerSFP": {"start": -24, "end": -16}
                },
                "mgmt": {
                    "leaf": {"start": -4, "end": -2}
                }
            },
            "100G-To-The-Host_Multi": {
                "spine": {
                    "peer": {"start": -4, "end": None},
                    "customerQSFP": {"start": -8, "end": -4},
                    "leaf": {},
                },
                "leaf": {
                    "spine": {"start": -4, "end": -2},
                    "peer": {"start": -2, "end": None},
                    # Default on documentation
                    # "mgmt1": {"start": -14, "end": -13},
                    # Default for designs with Spine Switch
                    "customerQSFP": {"start": -6, "end": -2},
                    # Default for all designs
                    "customerSFP": {"start": -22, "end": -14}
                },
                "mgmt": {}
            },
            "100G-To-The-Host_Single": {
                "spine": {},
                "leaf": {
                    "peer": {"start": -2, "end": None},
                    "customerQSFP": {"start": -8, "end": -4},
                },
                "mgmt": {}
            },
            "engr" : {
                "spine": {
                    "peer": {"start": -8, "end": -4},
                    "customerQSFP": {"start": -4, "end": None},
                    "leaf": {},
                },
                "leaf": {
                    "peer": {"start": -2, "end": None},
                    "spine": {"start": -6, "end": -4},
                    "mgmt1": {"start": -8, "end": -7},
                    # "mgmt2": {"start": -7, "end": -6},
                    # "customerQSFP": {"start": -6, "end": -2},
                    "customerSFP": {"start": -7, "end": -6}
                },
                "mgmt": {
                    "leaf": {"start": -4, "end": -2}
                }
            }
        }

        # NOTE: Arista Only
        self.defaultMLAGsettings = {
            "peer-vlan" : 4094,
            "peer-port-channel" : 1,
            "switches" :
                [{"primary": {"address": "10.255.255.1/30"}, "secondary": {"address": "10.255.255.2/30"}},
                 {"primary": {"address": "10.255.255.5/30"}, "secondary": {"address": "10.255.255.6/30"}},
                 {"primary": {"address": "10.255.255.9/30"}, "secondary": {"address": "10.255.255.10/30"}},
                 {"primary": {"address": "10.255.255.13/30"}, "secondary": {"address": "10.255.255.14/30"}},
                 {"primary": {"address": "10.255.255.17/30"}, "secondary": {"address": "10.255.255.18/30"}},
                 {"primary": {"address": "10.255.255.21/30"}, "secondary": {"address": "10.255.255.22/30"}},
                 {"primary": {"address": "10.255.255.25/30"}, "secondary": {"address": "10.255.255.26/30"}},
                 {"primary": {"address": "10.255.255.29/30"}, "secondary": {"address": "10.255.255.30/30"}}]
        }
        self.mlagCount = 0

        self.previoustypes = []
        self.networkconfigjson = {}
        self.rackjson = {}
        self.portchanneljson = {}
        self.mainvlans = []
        self.mtu = "1500"
        self.loadNetworkConfigJSON(networkconfigjson)

        self.design = None
        self.switches = {}
        self.switches_cache = switches
        if design is None:
            self.detectDesign(switches)
        else:
            self.design = design
        # self.detectOrder(switches)

        self.nodes = {}

    # Detect Design
    def detectDesign(self, switches = None):
        # If switches aren't inputed, use cached switches
        if switches is None:
            switches = self.switches_cache
        # Create Rack Prename
        prename = "R" + str(self.racknum) + "-"
        # Start Char
        intchar = ord("A")-1+2*(int(self.racknum)-1)
        # Create Blank Dictionary to start counting
        typecount = {}
        for switch in switches:
            switchtype = type(switch).__name__
            # Attempt to add one to the count and add blank key to switchname dictionary
            try:
                typecount.update({switchtype: int(typecount[switchtype])+1})
            # If switch doesn't exist, add key with count 1
            except:
                typecount.update({switchtype: 1})

            # Make Switch Name
            try:
                if ("92348" in switchtype) or ("7010" in switchtype):
                    switchname = prename + switch.model + "-" + chr(ord("A")-1 + int(self.racknum)-1 + typecount[switchtype])
                else:
                    switchname = prename + switch.model + "-" + chr(intchar + typecount[switchtype])
            except:
                # If switchname can't populate, skip switch
                continue

            # Attempt to Populate Interface Location
            try:
                location = self.placements[switchtype][typecount[switchtype]-1]
            except:
                # If location can't populate, skip switch
                location = None
            tempdict = {
                switchname : {
                    "instance" : None,
                    "location" : location
                }
            }
            self.switches.update(tempdict)

        design = None

        logger.info(f"*** Created Design: {typecount}")
        # Detect which design this is based off the count of switches
        for designname, designcount in self.designs.items():
            if typecount == designcount:
                # 100G-To-The-Host_Single and 100G-To-The-Host_Multi_100G-TCP-NVMe_R2-R4 is same design. We need to use Rack# to identify the correct design.
                if self.racknum != 1:
                    if designname == "100G-To-The-Host_Single":
                        # logger.info(f"*** Created Design: {designname} , Rack# = {self.racknum} -> SKIP")
                        continue
                logger.info("\n*** Detected the following rack: " + designname + "  ***\n")
                design = designname
                break

        # If designs aren't found, please erase all
        if design is None:
            self.switches = {}

        if not design:
            logger.info("*** Selected Design not found on the Tookit design templete. Please contact Admin/Developer to add the respective design")
            exit()

        # For 100G-To-The-Host configuration, need to change 93600 type from spine to leaf
        if "100G-To-The-Host" in design:
            for switch in switches:
                if "93600" in switch.model:
                    switch.type = "leaf"
                    logger.info('*** 100G-To-The-Host config found. C93600CD-GX: Changing switch type from Spine to ' + switch.type)


        # Load the correct portchannel interfaces
        if "Arista" in design:
            self.loadPortChannelJSON("default_Arista")
        elif "Cisco" in design:
            self.loadPortChannelJSON("default_Cisco")
        elif "100G-To-The-Host_Multi" in design:
            self.loadPortChannelJSON("100G-To-The-Host_Multi")
        elif "100G-To-The-Host_Single" in design:
            self.loadPortChannelJSON("100G-To-The-Host_Single")
        self.design = design

        return design

    # Detect order of switches
    def detectOrder(self, switches = None, forcecheck = False):
        # If switches aren't inputed, use cached switches
        if switches is None:
            switches = self.switches_cache

        logger.info("*** Detecting the order of switches")
        # Create Rack Prename
        prename = "R" + str(self.racknum) + "-"

        # Look for MGMT Switch
        mgmtswitch = None
        for switch in switches:
            # if '3048' in type(switch).__name__:
            if switch.type == "mgmt":
                mgmtswitch = switch
                # Store switch as MGMT switch
                for key, value in self.switches.items():
                    if ('92348' in key) or ('7010' in key):
                        self.switches[key]["instance"] = switch
                        break
                break
            if TESTING and self.design == "Test-Leaf_Cisco":
                if switch.type == "leaf":
                    for key, value in self.switches.items():
                        if '93180' in key:
                            self.switches[key]["instance"] = switch
                            break

        # If mgmtswitch can't be found, exit
        if mgmtswitch is None:
            return None

        # Update mgmtswitch cache
        mgmtswitch.getMACTable()

        # Tie the switches to the location of switch BMC MAC
        '''
        for switch in switches:
            location = mgmtswitch.whereisMAC(switch.mgmtMAC)
            for key, value in self.switches.items():
                try:
                    if value['location'] in location:
                        logger.info("Found " + key + " at " + value['location'])
                        self.switches[key]["instance"] = switch
                        break
                except:
                    continue
        '''
        # Put the switches in a sorted location
        temp_switchlistdict = []
        for switch in switches:
            try:
                location = mgmtswitch.whereisMAC(switch.mgmtMAC)
            except:
                location = "Missing!"
            #print("Found " + switch.model + ' at ' + location)
            temp_switchlistdict.append({"instance": switch,"location": location})
        # https://stackoverflow.com/questions/72899/how-do-i-sort-a-list-of-dictionaries-by-a-value-of-the-dictionary


        #temp_switchlistdict = sorted(temp_switchlistdict, key=lambda k: k["location"])
        #temp fix added for abobe line
        def custom_sort(item):
            location = item.get("location")
            return "" if location is None else location

        temp_switchlistdict = sorted(temp_switchlistdict, key=custom_sort)


        # Assign to correct switches based off lower location
        for switchdict in temp_switchlistdict:
            for key, value in self.switches.items():
                try:
                    if (switchdict["instance"].model in key) and (value['instance'] is None):
                        self.switches[key]["instance"] = switchdict["instance"]
                        self.switches[key]["location"] = switchdict["location"].split("Eth")[-1]
                        break
                except:
                    continue


    def checkOrder(self):
        correct = True
        # Let the user know if some switches aren't located in the correct ports
        for key, value in self.switches.items():
            try:
                if value["instance"] is None:
                    logger.info(key + "'s mgmt connection is not in the correct port location. It's supposed to be connected Ethernet" + value["location"] + " on the mgmt switch.")
                    correct = False
            except:
                continue

        return correct

    def getMGMTSwitch(self):
        for key, value in self.switches.items():
            '''
            if '92348' in key:
                return value["instance"]
            '''
            if value["instance"].type == "mgmt":
                return value["instance"]
        raise("Can't find management switch")

    def getPrimarySpineSwitch(self):
        for key, value in self.switches.items():
            if ('93600CD' in key) or ('7050CX3' in key) or ('9332C' in key):
                return value["instance"]
        return None

    def getSecondarySpineSwitch(self):
        count = 0
        for key, value in self.switches.items():
            if ('93600CD' in key) or ('7050CX3' in key) or ('9332C' in key):
                if count == 0:
                    count += 1
                else:
                    return value["instance"]
        return None

    def getPrimaryLeafSwitch(self):
        for key, value in self.switches.items():
            if ('C93180YC-FX3' in key) or ('C93180YC-FX' in key):
                return value["instance"]
        return None

    def getSecondaryLeafSwitch(self):
        count = 0
        for key, value in self.switches.items():
            if ('C93180YC-FX3' in key) or ('C93180YC-FX' in key):
                if count == 0:
                    count += 1
                else:
                    return value["instance"]
        return None

    def getPrimaryStorageSwitch(self):
        for key, value in self.switches.items():
            if 'G620' in key:
                return value["instance"]
        return None

    def getSecondaryStorageSwitch(self):
        count = 0
        for key, value in self.switches.items():
            if 'G620' in key:
                if count == 0:
                    count += 1
                else:
                    return value["instance"]
        return None

    def updateMACTable(self, force=False):
        for switchname, data in self.switches.items():
            switch_instance = data["instance"]
            if isinstance(switch_instance, cisconexus.cisconexus) or isinstance(switch_instance, aristaeos.aristaeos):
                switch_instance.getMACTable(force)

    def updateWWNTable(self, force=False):
        for switchname, data in self.switches.items():
            switch_instance = data["instance"]
            if isinstance(switch_instance, brocadefc.brocadefc):
                switch_instance.getWWNTable(force)

    def whereisMAC(self, MAC):
        MAC = MAC.lower()
        for switchname, data in self.switches.items():
            switch_instance = data["instance"]
            if isinstance(switch_instance, cisconexus.Nexus92348) or isinstance(switch_instance, cisconexus.Nexus93180YCFX) or isinstance(switch_instance, cisconexus.Nexus93180YCFX3) or isinstance(switch_instance, aristaeos.DCS7010) or isinstance(switch_instance, aristaeos.DCS7050SX3):
                port = switch_instance.whereisMAC(MAC)
                # Use Cisco Numbering
                if "Cisco" in self.design:
                    if port is None or "Po" in port or 'Peer-Link' in port or int(port.replace("Eth1/","")) > 48:
                        continue
                    else:
                        return switch_instance.name, port
                # Use Arista Numbering
                else:
                    if port is None or "Po" in port or 'Peer-Link' in port or int(port.replace("Et","")) > 48:
                        continue
                    else:
                        return switch_instance.name, port
        return None, None

    def whereisWWN(self, WWN):
        for switchname, data in self.switches.items():
            switch_instance = data["instance"]
            if isinstance(switch_instance, brocadefc.brocadefc):
                port = switch_instance.whereisWWN(WWN)
                if port is None:
                    continue
                else:
                    return switch_instance.name, port
        return None, None

    def loadNetworkConfigJSON(self, input):
        self.networkconfigjson = input
        self.rackjson = self.networkconfigjson["rack"][self.racknum]
        # self.portchanneljson = self.portchannelinterfaces["default"]
        self.loadPortChannelJSON("default")
        # Get the mgmt VLAN and put it as the first VLAN on the mainVLANs list
        self.mainvlans.append(self.networkconfigjson["mgmtvlan"])
        self.mainvlans = self.mainvlans + self.networkconfigjson["vlans"]
        # Get the MTU settings from JSON
        self.mtu = self.networkconfigjson["mtu"]

    def loadPortChannelJSON(self, key):
        self.portchanneljson = self.portchannelinterfaces[key]
        return self.portchanneljson

    def enableAPI(self):
        logger.info("\nEnabling HTTP API on all switches\n")
        for switchname, switchdata in self.switches.items():
            switchdata["instance"].enableAPI()

    def configurePassword(self, password=None):
        logger.info("\nConfiguring all passwords on all switches\n")
        for switchname, switchdata in self.switches.items():
            if password is None:
                cpassword = lawcompliance.passwordencode(switchdata["instance"].host, autodiscover.getPassword())
            else:
                cpassword = password
            logger.info(switchdata["instance"].host + " Updating admin account password to " + cpassword)
            if TESTING:
                logger.debug(switchdata["instance"].host + " Skip Change Password.... TESTING=True")
            else:
                switchdata["instance"].updateUserPass("admin", cpassword)
        self.saveAllConfigs()


    def configureAllMgmtInterfaces(self):
        logger.info("\nConfiguring all management interfaces on all switches\n")
        switchnum = 1
        #previoustype = None
        for switchname, switchdata in self.switches.items():
            # Get switch type
            type = switchdata["instance"].type
            # Get switchnumber based off previous switch type
            if self.previoustypes is None:
                self.previoustypes.append(type)
            elif type in self.previoustypes:
                switchnum = 2
            else:
                switchnum = 1
                self.previoustypes.append(type)
            # Attempt to get data for switch type from networkconfig.json:rack
            try:
                data = self.rackjson[type]
                ipaddr = data["ipaddr" + str(switchnum)]
            except:
                continue

            if TESTING:
                logger.debug(f"Skip setting mgmt IP - {switchname}, {ipaddr}, gtw: {self.networkconfigjson['gateway']}")
                return None

            # Attempt to program the switch IP and switchname
            try:
                switchdata["instance"].setName(switchname)
                switchdata["instance"].setIPv4MGMT(ipaddr, self.networkconfigjson["subnet"], self.networkconfigjson["gateway"])
            except:
                continue

    def resetAllInterfaces(self):
        logger.info("\nResetting all interface configurations on all switches\n")
        for switchname, switchdata in self.switches.items():
            # Reset the interfaces if the switch is a spine, leave, or mgmt switch
            # https://stackoverflow.com/questions/3389574/check-if-multiple-strings-exist-in-another-string
            if any(x in switchdata["instance"].type for x in ["spine", "leaf", "mgmt"]):
                logger.info("Resetting all interface configs on " + switchname)
                switchdata["instance"].resetAllInterfaces()

    def configureVendorPeering(self):
        logger.info("\nConfiguring the vendor's multi-chassis switch technology\n")
        if 'Cisco' in self.design or '100G-To-The-Host' in self.design:
            # Get the latest IPv4 Addresses of the switches
            for switchname, switchdata in self.switches.items():
                if any(x in switchdata["instance"].model for x in CISCO_SWITCH_LIST):
                    switchdata["instance"].getIPv4MGMT()

            # (CISCO ONLY) Set the lldp, vpc and lacp features
            for switchname, switchdata in self.switches.items():
                # Set the lacp and vpc features if these are cisco leaf and spine switches
                # https://stackoverflow.com/questions/3389574/check-if-multiple-strings-exist-in-another-string
                if any(x in switchdata["instance"].model for x in LACP_LLDP_SWITCH_LIST):
                    logger.info("Enabling lacp, and lldp features on " + switchname)
                    switchdata["instance"].setFeature('lacp')
                    switchdata["instance"].setFeature('lldp')
                if any(x in switchdata["instance"].model for x in VCP_SWITCH_LIST):
                    logger.info("Enabling vcp features on " + switchname)
                    switchdata["instance"].setFeature('vpc')

            # (CISCO ONLY) Set the vpc peer-link on the last two interfaces
            priority = 10
            for switchname, switchdata in self.switches.items():
                switchinstance = switchdata["instance"]
                # Set the lacp and vpc features if these are cisco leaf and spine switches
                # https://stackoverflow.com/questions/3389574/check-if-multiple-strings-exist-in-another-string
                if any(x in switchinstance.model for x in VCP_SWITCH_LIST):
                    # Get last two interfaces on switch
                    interfaces = switchinstance.interfaceList[self.portchanneljson[switchinstance.type]["peer"]["start"]:
                                                              self.portchanneljson[switchinstance.type]["peer"]["end"]]

                    # Get the other switch that is the same model but different switch
                    otherswitchinstance = None
                    for otherswitchname, otherswitchdata in self.switches.items():
                        if (switchinstance.model == otherswitchdata["instance"].model) and (
                                switchinstance is not otherswitchdata["instance"]):
                            otherswitchinstance = otherswitchdata["instance"]
                    logger.info("Setting up peer-link on " + switchinstance.name + " with " + otherswitchinstance.name)
                    vpcid = self.rackjson[switchinstance.type]["id"]
                    switchinstance.setVPC(vpcdomainid=vpcid, priority=priority,
                                          ipv4AddressOfOtherSwitch=otherswitchinstance.hostIPv4Address,
                                          peerlinkportchannel=1, peerlinkinterfaces=interfaces)
                    priority += 1
        elif 'Arista' in self.design:
            # Using Ticktock design to determine the primary and secondary switches
            ticktock = True

            # Set the mlag count by using the racknum. If racknum is less then 2, set mlagcount to 0 so leaf/spine and switch can use the first two mlag addresses. Otherwise, set mlagcount as racknum
            if int(self.racknum) < 2:
                self.mlagCount = 0
            else:
                self.mlagCount = int(self.racknum)

            for switchname, switchdata in self.switches.items():
                switchinstance = switchdata["instance"]
                # Check if the switch is a Spine or Leaf switch
                if (switchinstance.type == "spine") or (switchinstance.type == "leaf"):
                    # Get last two interfaces on switch
                    interfaces = switchinstance.interfaceList[
                                 self.portchanneljson[switchinstance.type]["peer"]["start"]:
                                 self.portchanneljson[switchinstance.type]["peer"]["end"]]
                    # Get the global settings
                    mlagDomainID = self.rackjson[switchinstance.type]["id"]
                    peerportChannel = self.defaultMLAGsettings["peer-port-channel"]
                    peerVLAN = self.defaultMLAGsettings["peer-vlan"]
                    # If ticktock is False, program with Primary Settings
                    if ticktock:
                        ticktock = False
                        localipv4address = self.defaultMLAGsettings["switches"][self.mlagCount]["primary"]["address"]
                        peeripv4address = self.defaultMLAGsettings["switches"][self.mlagCount]["secondary"]["address"]
                    # Otherwise, program with Secondary Settings
                    else:
                        ticktock = True
                        localipv4address = self.defaultMLAGsettings["switches"][self.mlagCount]["secondary"]["address"]
                        peeripv4address = self.defaultMLAGsettings["switches"][self.mlagCount]["primary"]["address"]

                        # Add Count
                        self.mlagCount += 1

                    # Set the MLAG Peering settings
                    switchinstance.setMLAGPeering(mlagDomainID, peerportChannel, interfaces, peerVLAN, localipv4address, peeripv4address)

    def configureInternalPortchannels(self):
        logger.info("Configuring all port-channels from/to spine, leaf, and mgmt switches")
        # Program Spine <-> Leaf Trunk from SPINE Switch Perspective
        try:
            for switchname, switchdata in self.switches.items():
                switchinstance = switchdata["instance"]
                # If the switch is a spine switch, configure all ports for VPC/MLAG connections to all racks
                if switchinstance.type == 'spine':
                    # Get only the ethernet interfaces
                    # https://stackoverflow.com/questions/2152898/filtering-a-list-of-strings-based-on-contents
                    ethinterfaces = [k for k in switchinstance.interfaceList if 'Eth' in k]
                    # Program each port-channel for each leaf pair
                    # For Cisco, program at every two ports. For some reason, the 93180LC switch have the bottom ports disabled. Otherwise program at every 4 ports
                    if "Cisco" in self.design:
                        multport = 4
                    elif "100G-To-The-Host" in self.design:
                        multport = 2
                    else:
                        multport = 4
                    for rack, rackdata in self.networkconfigjson["rack"].items():
                        start = multport * (int(rack) - 1)
                        portchannelinterfaces = ethinterfaces[start:(start + multport)]
                        ident = rackdata["leaf"]["id"]
                        switchinstance.setPortChannelInterface(portchannel_num=ident, interfaces=portchannelinterfaces,
                                                               description="Spine <-> Leaf Rack#" + str(rack),
                                                               VLANs=self.mainvlans)
        except:
            pass

        # Program Spine <-> Leaf Trunk (If needed on rack 1. Required on racks 2-4.) from LEAF Switch Perspective
        # Use leaf (VPC/MLAG) ID as Portchannel/VPC/MLAG ID for both spine/leaf switches
        ident = self.rackjson["leaf"]["id"]
        for switchname, switchdata in self.switches.items():
            switchinstance = switchdata["instance"]
            # If the switch is a leaf switch, work on the 3rd and 4th from last interfaces.
            if switchinstance.type == 'leaf' and "Single" not in self.design:
                interfaces = switchinstance.interfaceList[self.portchanneljson[switchinstance.type]["spine"]["start"]:
                                                          self.portchanneljson[switchinstance.type]["spine"]["end"]]
                switchinstance.setPortChannelInterface(portchannel_num=ident, interfaces=interfaces,
                                                       description="Leaf <-> Spine",
                                                       VLANs=self.mainvlans)

        # Program Leaf <-> Mgmt Trunk on Leaf Switch
        # Use mgmt (VPC/MLAG) ID as Portchannel/VPC/MLAG ID for both mgmt/leaf switches
        ident = self.rackjson["mgmt"]["id"]
        for switchname, switchdata in self.switches.items():
            switchinstance = switchdata["instance"]
            if switchinstance.type == 'leaf':
                interfaces = []
                for key, value in self.portchanneljson[switchinstance.type].items():
                    if "mgmt" in key:
                        interfaces = interfaces + switchinstance.interfaceList[
                                                  self.portchanneljson[switchinstance.type][key]["start"]:
                                                  self.portchanneljson[switchinstance.type][key]["end"]]
                switchinstance.setPortChannelInterface(portchannel_num=ident, interfaces=interfaces,
                                                       description="Leaf <-> MGMT",
                                                       VLANs=self.mainvlans)
                '''
                # If the switch is specifically a 7050SX3 switch, please set Serdes setting to 10G for the interfaces
                if switchinstance.model == "DCS-7050SX3-48YC8-R":
                    switchinstance.setSerdes(interfaces, "10g")
                '''

        # 100G-To-The-Host config does not have Leaf <-> MGMT port channel
        print("**Design = " + self.design)
        if "100G-To-The-Host" not in self.design:
            # Program Leaf <-> Mgmt Trunk on MGMT Switch
            ident = self.rackjson["mgmt"]["id"]
            for switchname, switchdata in self.switches.items():
                switchinstance = switchdata["instance"]
                # Use mgmt (VPC) ID as Portchannel/VPC/MLAG ID for both mgmt/leaf switches
                if switchinstance.type == 'mgmt':
                    # Get the last two SFP+ interfaces for the mgmt switch
                    interfaces = switchinstance.interfaceList[self.portchanneljson[switchinstance.type]["leaf"]["start"]:
                                                              self.portchanneljson[switchinstance.type]["leaf"]["end"]]
                else:
                    # If the switch is none of the types above, skip it
                    continue
                switchinstance.setPortChannelInterface(portchannel_num=ident, interfaces=interfaces,
                                                       description="Leaf <-> MGMT",
                                                       VLANs=self.mainvlans)

    def configureCustomerPortchannel(self):
        logger.info("\nConfiguring customer uplinks\n")
        ident = self.networkconfigjson["customerid"]
        spine = self.getPrimarySpineSwitch()
        for switchname, switchdata in self.switches.items():
            switchinstance = switchdata["instance"]
            # Configure uplink on spine switch if it exists. Otherwise, configure uplink on leaf switch if and only if the racknum is 1
            if (switchinstance.type == 'spine') or (switchinstance.type == "leaf" and self.racknum == str(1) and spine is None):
                interfaces = []
                for key, value in self.portchanneljson[switchinstance.type].items():
                    if "customer" in key:
                        interfaces = interfaces + switchinstance.interfaceList[
                                                  self.portchanneljson[switchinstance.type][key]["start"]:
                                                  self.portchanneljson[switchinstance.type][key]["end"]]
                switchinstance.setPortChannelInterface(portchannel_num=ident, interfaces=interfaces,
                                                       description="Customer Uplink",
                                                       VLANs=self.mainvlans)
            else:
                continue

    def configureAllInterfaceVLANs(self):
        logger.info("\nConfiguring VLANs on all interfaces that are not grouped\n")
        for switchname, switchdata in self.switches.items():
            switchinstance = switchdata["instance"]
            # Configure all non-portchannel interfaces with VLANs
            if (switchinstance.type == 'spine') or (switchinstance.type == "leaf") or (switchinstance.type == "mgmt"):
                # Get the latest config
                switchinstance.getRunningConfig()
                interfaces = []
                # Get all the interfaces that isn't part of port-channel
                for interface, data in switchinstance.interfaceDetails.items():
                    if ("channel-group" not in data) and ("port-channel" not in interface) and ("mgmt" not in interface) and ("Management" not in interface) and ("Vlan" not in interface) and ("Port-Channel" not in interface):
                        interfaces.append(interface)
                switchinstance.setInterfaceVLANs(interfaces, self.mainvlans)

    def configureMTU(self):
        logger.info("\nConfigure all switchports to MTU = " + str(self.mtu) + "\n")
        for switchname, switchdata in self.switches.items():
            switchinstance = switchdata["instance"]
            switchinstance.setMTU(MTU = self.mtu)

    def saveAllConfigs(self):
        logger.info("\nSaving all the configs\n")

        if TESTING:
            logger.debug("\nTESTING=True: Skip switch save config. \n")
        else:
            for switchname, switchdata in self.switches.items():
                switchinstance = switchdata["instance"]
                count = 0
                while count < 5:
                    logger.info("Saving running-config on " + switchname)
                    if switchinstance.saveRunningConfig():
                        break
                    else:
                        count += 1
                        logger.info("Failed to save running-config on " + switchname + "has failed. Trying again.")
                        continue

    def getDetails(self):
        logger.info("Getting IPv4 Details of Switches",self.switches)
        for switchname, switchdata in self.switches.items():
            switchinstance = switchdata["instance"]
            switchinstance.getIPv4MGMT()


def main():
    badtime.hitachi()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_file_name = "networkconfig"+datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + '.log'
    log_file_name = os.path.join(os.getcwd(),'logs',log_file_name)
    console_handler = logging.StreamHandler()

    file_handler = logging.FileHandler(log_file_name)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.info("Welcome to the UCP Network Config Tool!\n\n I need to ask a few questions to continue.\n")

    # Let the user know we are reading the networkconfig.json file for network config details
    logger.info("This script uses networkconfig.json file to configure the rack. Please edit the json file to meet the customer's requirements (If needed).\n"
                "If customizations aren't needed, please just continue.\n")
    input("Hit enter to continue")

    # Read the JSON File
    filename = "networkconfig.json"
    with open(filename) as json_file:
        networkconfigjson = json.load(json_file)

    # # Main VLANs
    # mainvlans = []
    # mainvlans.append(networkconfigjson["mgmtvlan"])
    # mainvlans = mainvlans + networkconfigjson["vlans"]
    #
    # # Validate JSON File
    # logger.debug(json.dumps(networkconfigjson, indent=4))
    # keys1 = ["linkid", "customerid", "mgmtvlan", "vlans", "rack"]
    # keys2 = ["1", "2", "3", "4"]
    # keys3 = ["spine", "leaf", "mgmt", "fc"]
    # keys4 = ["id", "ipaddr"]
    # # Please do this later

    # Ask the user which rack number they are working on
    racknum = helper.askRackNumber()

    # # Attempt to get rack details
    # try:
    #     rackjson = networkconfigjson['rack'][str(racknum)]
    # except:
    #     logger.info("Rack #" + str(racknum) + " doesn't exist in the networkconfig.json file. Please make sure you enter the correct rack number.")
    #     return False
    # WARN USER ABOUT DISRUPTIVE ACTION
    logger.info("WARNING: The actions of this script will disrupt the network!\n")
    keyword = input("Please enter 'coolbeans' if you understand the risks and to continue: ")
    if keyword != 'coolbeans':
        logger.info("\nIncorrect pass phrase. Please restart script.")
        return False

    # Discover the switches
    switches = autodiscover.discoverSwitches(autodiscover.getIPv6Neighbors(), ['admin'], ['Passw0rd!'])
    logger.info("\n*** I discovered the following switches:")
    for switch in switches:
        logger.info(switch.model + ' ' + switch.host)

    # # Warn user that spine switches do not belong in rack #2,3,4
    # if int(racknum) > 1:
    #     for switch in switches:
    #         if switch.type == "spine":
    #             logger.info("\nI detected some spine switches in the rack. Rack#" + racknum + " cannot contain spine switches. Spine switches belong in Rack#1. Please correct this error.\nExiting")
    #             return False

    UCPCINet = networkstack(racknum, switches, networkconfigjson)
    UCPCINet.detectOrder()

    logger.info("\n*** This rack is the following design: " + UCPCINet.design + "  ***\n")

    input("Hit enter to continue")

    # For CA Law Compliance
    UCPCINet.configurePassword()
    UCPCINet.configureAllMgmtInterfaces()
    # For Advisor Team - Request Made by Sathish Shanmugam
    UCPCINet.enableAPI()
    UCPCINet.resetAllInterfaces()
    UCPCINet.configureVendorPeering()
    UCPCINet.configureInternalPortchannels()
    UCPCINet.configureCustomerPortchannel()
    UCPCINet.configureAllInterfaceVLANs()
    # For Field - Request Made by Cody McCuistion
    UCPCINet.configureMTU()
    UCPCINet.saveAllConfigs()

    badtime.okay()
    logger.info(f"Saved log file {log_file_name}")
    logger.info("=================================== Switch Configuration is finished ===========================================")
    return True


if __name__ == "__main__":
    main()
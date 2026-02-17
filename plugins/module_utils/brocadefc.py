from netmiko import ConnectHandler
import time
import switches
import re
import ipaddress

class brocadefc(switches.switch):
    def __init__(self, host, username, password):
        switches.switch.__init__(self, host, username, password)
        self.deviceType = "brocade_nos"
        self.interfaceList = []
        self.interfaceDetails = {}
        self.getDetails()
        self.WWNKey = 'WWNs'
        self.type = "fc"

    def runcommand(self, command, timeout=60):
        try:
            net_connect = ConnectHandler(device_type=self.deviceType, ip=self.host, username=self.username, password=self.password, timeout=timeout)
            output = net_connect.send_command(command)
            net_connect.disconnect()
            return output
        except:
            return ''

    def getDetails(self):
        output = self.runcommand('switchname')
        self.name = output.strip()

        while True:
            output = self.runcommand('ethif --show eth0 | grep Address')
            try:
                mgmtMAC = output.split('Address:')[1].strip().replace(':', '').lower()
                break
            except:
                print(self.host + " Retrying mgmtMAC check")
                continue
        self.mgmtMAC = mgmtMAC
        # self.getInterfaces()
        # return self.name

    def getInterfaces(self):
        self.interfaceDetails = {}
        output = self.runcommand('switchshow')
        output = output.replace('\t', '')
        lines  = output.splitlines()
        prev_line = ''
        header_line = ''
        headers = []
        main_dict ={}
        for line in lines:
            if '===============================================' in line:
                header_line = prev_line
                headers = header_line.split()
            elif len(headers) > 0:
                temp_dict = {}
                values = line.split(maxsplit=len(headers)-1)
                for header, value in zip(headers, values):
                    temp_dict.update({header:value})
                try:
                    main_dict.update({temp_dict['Address']:temp_dict})
                except:
                    pass
            prev_line = line
        # Save the interface details
        self.interfaceDetails = main_dict

        # Create list of ports
        self.interfaceList = []
        for address, interface in main_dict.items():
            self.interfaceList.append(interface['Port'])

    def getWWNTable(self, force=False):
        self.getInterfaces()

        output = self.runcommand("nsshow | grep 'N '")
        lines = output.splitlines()
        # pattern = re.compile("(([0-9a-f]{2}[:]){7}([0-9a-f]{2}))")

        # Clear out old WWNs
        for address, interface in self.interfaceDetails.items():
            self.interfaceDetails[address][self.WWNKey] = []

        # Populate the WWNs
        for line in lines:
            address = line.split()[1].replace(';','')
            wwn_match_tuples = re.findall("(([0-9a-f]{2}[:]){7}([0-9a-f]{2}))", line)
            wwns = []
            for match in wwn_match_tuples:
                wwns.append(match[0])
            try:
                self.interfaceDetails[address][self.WWNKey] = wwns
            except:
                pass
        # print(output)
        return self.interfaceDetails

    def whereisWWN(self, WWN, forcecheck = False):
        if forcecheck:
            self.getWWNTable()
        for address, address_class in self.interfaceDetails.items():
            try:
                if WWN in address_class[self.WWNKey]:
                    return address_class["Port"]
            except:
                continue
        return None

    def updateUserPass(self, username, password):
        if username is not "admin":
            print(self.host + " doesn't support changing password for " + username)
            return False
        config_commands = ["passwdcfg --set -history 0", "passwd -old " + re.escape(self.password) + " -new " + re.escape(password)]
        for command in config_commands:
            self.runcommand(command)
        self.password = password
        return True

    def setName(self, name):
        cmd = "switchname " + str(name)
        output = self.runcommand(cmd, 10)
        if "Done" in output:
            self.name = name
            return True
        else:
            return False

    def setIPv4MGMT(self, ipaddr, subnet, gateway):
        # Generate the command
        cmd = "ipaddrset -ipv4 -add -ethip " + ipaddr + " -ethmask " + subnet + " -gwyip " + gateway + " -dhcp OFF"
        output = self.runcommand(cmd, 10)
        if output == '':
            return True
        else:
            return False

    def resetAllInterfaces(self):
        print("Not supported")

    def getIPv4MGMT(self):
        cmd = "ipaddrshow"
        output = self.runcommand(cmd, timeout=10)
        output = output.splitlines()
        for line in output:
            splited = line.split(": ")
            if "Ethernet IP Address" in line:
                self.hostIPv4Address = splited[1]
            elif "Gateway IP Address" in line:
                self.hostIPv4Gateway = splited[1]
            elif "Ethernet Subnet mask" in line:
                temp = ipaddress.IPv4Network((0,splited[1]))
                self.hostIPv4Address += "/" + str(temp.prefixlen)
        return self.hostIPv4Address

class G620(brocadefc):
    def __init__(self, host, username, password):
        brocadefc.__init__(self, host, username, password)
        self.model = "G620"
        self.Usize = 2

class G720(brocadefc):
    def __init__(self, host, username, password):
        brocadefc.__init__(self, host, username, password)
        self.model = "G720"
        self.Usize = 2

# test = G620("fe80::c6f5:7cff:feba:1f68%11", "admin", "Passw0rd!")

# print(test)
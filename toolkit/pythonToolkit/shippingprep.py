import csv
from datetime import datetime
import badtime
import esxi
import helper
import autodiscover
import networkconfig
import json
import lawcompliance
import vsphere
from autodiscover import CSV_FILE_PATH, getPassword
import loginit
import logging
import subprocess
import prettytable
from esxi import ESXi
import quantaskylake
from quantaskylake import QuantaSkylake

logger = logging.getLogger("root")

ILO_REST_PATH = 'HA8XX_scripts/ilorest/ilorest'

class ILORestLoginContextManager:
    def __init__(self,host,username,password) -> None:
        self.host = host
        self.username = username
        self.password = password

    def __enter__(self):
        cmd=  f'{ILO_REST_PATH} login {self.host} -u {self.username} -p {self.password}'
        subprocess.call(cmd)
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        subprocess.call(f'{ILO_REST_PATH} logout')
    
    def run(self,cmd):
        subprocess.call(f"{ILO_REST_PATH} {cmd}")


def reset_ha_servers_password(host,username,password,newpassword):
    """Reset the HA servers password based on the selections"""
    with ILORestLoginContextManager(host,username,password) as ilo:
        ilo.run(f'iloaccounts changepass 2 {newpassword}')
    logger.info(f"password changed for the host{host}")


def main():
    # Store Current Time
    starttime = datetime.now()
    helper.removeAllVMCLI()

    # Print welcome screen
    badtime.hitachi()
    badtime.version()

    # Let user know that we are reflashing the BMC to reinstate cmb9.admin and forcepassword change requirement
    logger.info("This shipping prep script will tell all Server BMC to force password change upon reboot and set the appropriate passwords to the switches/ESXi hosts. \n\nPlease make sure all equipment is powered on before continuing.\n")
    input("Hit enter to continue")

    # Ask the user which rack number they are working on
    racknum = helper.askRackNumber()

    # Ask the user how many nodes that rack has
    # nodesnum = helper.askNodeQuantity()

    # Ask the user if there are any switches
    checkswitches = helper.askForSwitches()
    target_switch = helper.askForTargetSwitch()

    # Ask the user if the equipment is being shipped soon
    answer = input("Do you want to set the password to \"Unique\" or \"Default\"? : ")
    if answer.lower() == 'default':
        resetPassword = True
        logger.info("Setting all passwords to default")
    else:
        resetPassword = False
        logger.info("Setting all passwords to unique")

   
    nodes = autodiscover.discoverNodes(autodiscover.getIPv6Neighbors(), ['admin'], ['cmb9.admin'])
    if nodes:
        logger.info('\nGetting IPv4 Addresses via IPv6 Link-Local Addresses')
    else:
        logger.warning("No any Node found continuing to discover other components")
    for node in nodes:
        node.getIPv4Address()
    logger.info(' ')


    # nodes = []

    if checkswitches:
        # Attempt to get rack details
        try:
            # Read the JSON File
            filename = "networkconfig.json"
            with open(filename) as json_file:
                networkconfigjson = json.load(json_file)
            rackjson = networkconfigjson['rack'][str(racknum)]
        except:
            logger.info("Rack #" + str(racknum) + " doesn't exist in the networkconfig.json file. Please make sure you enter the correct rack number.")
            return False
        # Discover the switches
        switches = autodiscover.discoverSwitches(autodiscover.getIPv6Neighbors(), ['admin'], ['Passw0rd!'])
        UCPNet = networkconfig.networkstack(racknum, switches, networkconfigjson)
        UCPNet.detectOrder()
    else:
        UCPNet = None


    logger.info("Starting Password Change for Server's BMC")
    # Change the Node Passwords
    for node in nodes:
        if resetPassword:
            node.updateUserPass("admin", "cmb9.admin")
        else:
            node.updateUserPass("admin", lawcompliance.passwordencode(node.host, autodiscover.getPassword()))

    logger.info("Reseting the password for HA Servers")

    try:
        with open(CSV_FILE_PATH, newline='') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=[
                                    'ipaddress', 'username', 'password'])
            next(reader)
            servers = list(reader)
            
            for server in servers:
                # print(server)
                if resetPassword:
                    reset_ha_servers_password(server['ipaddress'],server['username'],server['password'], "cmb9.admin")
                else:
                    new_password = lawcompliance.passwordencode(server['ipaddress'][1:-1], autodiscover.getPassword())
                    reset_ha_servers_password(server['ipaddress'],server['username'],server['password'], new_password)

    except Exception as e:
        logger.info(f"Error occured for HA Nodes password reset. ")
    
    try:
        logger.info("Read password and update last password  in server.csv list...")
        with open(CSV_FILE_PATH, mode='r', newline='') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=['IPv6', 'Username', 'Password','Model','SerialNumber'])
            next(reader)
            servers = list(reader)

        for server in servers:
            if resetPassword:
                server['Password'] = "cmb9.admin"
            else:
                new_password = lawcompliance.passwordencode(server['IPv6'][1:-1], autodiscover.getPassword())
                logger.info(new_password)
                server['Password'] = new_password
                logger.info(server)
        with open(CSV_FILE_PATH, mode='w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['IPv6', 'Username', 'Password','Model','SerialNumber'])
            writer.writeheader()
            writer.writerows(servers)       
        logger.info("Password changed successfully and updated in server.csv")

    except Exception as e:
        logger.info(f"Error occured while updating password in server.csv for HA nodes. please check if HA nodes exist in Rack. ")

        

    # Change the Switch Passwords
    if UCPNet is not None:
        logger.info("Starting Password Change for all switch equipment")
        if resetPassword:
            UCPNet.configurePassword("Passw0rd!")
        else:
            UCPNet.configurePassword()

    ############################################pretty Table coloumn##########################################################
    # Print out the username and passwords
    thetable = prettytable.PrettyTable()
    # thetable.field_names = ["Equipment Type", "Name", "Serial", "IPv4 Address", "Username", "Password"]
    if not target_switch:
        thetable.field_names = ["Equipment Type", "Name", "Model", "Serial", "IPv4 Address", "Username", "Password"]
        thetable.sortby = "Name"

        # # Populate Node Details
        for node in nodes:
            # thetable.add_row([str(type(node).__name__), node.host, node.SystemsJSONCache['SerialNumber'], node.ipv4Address, node.username, node.password])
            # thetable.add_row([str(type(node).__name__), node.host,node.SystemsJSONCache['SKU'], node.SystemsJSONCache['SerialNumber'], node.ipv4Address, node.username, node.password])
            if not hasattr(node, 'servertype'):
                thetable.add_row(
                    [str(type(node).__name__), node.host, node.SystemsJSONCache['SKU'], node.SystemsJSONCache['SerialNumber'],
                    node.ipv4Address, node.username, node.password])
    # Populate Switch Details
    sw_table = prettytable.PrettyTable()
    sw_table.field_names = ["Equipment Type", "Name","IPv4 Address", "Username", "Password","Model"]
    if UCPNet:
        sw_table.sortby = "Name"
        for switch in UCPNet.switches_cache:
            # print(switch.interfaceDetails,"+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            
            sw_table.add_row([str(type(switch).__name__), switch.name, switch.hostIPv4Address, switch.username,
                              switch.password,switch.model])
            
    hatable = prettytable.PrettyTable()
    hatable.field_names = ['IPv6Address','Username','Password','Model','SerialNumber']
    if not target_switch:
        try:
            with open(CSV_FILE_PATH, 'r') as f:
                reads = csv.reader(f)
                next(reads)
                for read in reads:
                    hatable.add_row(read)
        except Exception as e:
            pass
   
    logger.info(f"\n{'='*50} HA Nodes Data Table {'='*50}\n{hatable}")
    # logger.info(hatable)
    logger.info(f"\n{'='*48} Quanta Nodes Data Table {'='*49}\n{thetable}")
    # logger.info(thetable)
    logger.info(f"\n{'='*50} Switches Data Table {'='*50}\n{sw_table}")
    # logger.info(sw_table)

    logger.info("Password change completed.")
    logger.info("For updated password of HA nodes, please refer to server.csv file.")

    ##########################################################################################################################


    # Save for later
    answer = input("\nShall I attempt to detect ESXi instances and change the password as well? (y/n) :")
    #answer = "n"
    if "y" in answer or "Y" in answer:
        logger.info("Attempting to detect OS nodes")
    else:
        logger.info("All done!")
        return True

    
    logger.info("Starting Password Change for all ESXi Instances on DS Nodes...")
    nodes = [node for node in nodes if not hasattr(node, 'servertype')]
    
    if nodes:
        #print(f"node to reset : {nodes}")
        # Create vSphere Cluster object
        thecluster = vsphere.cluster()
        # Detect the ESXi instances within nodes
        thecluster.detectESXi(nodes)
        # Update the password to meet new password requirements
        if resetPassword:
            thecluster.updateUserPass(password="Passw0rd!")
        else:
            thecluster.updateUserPass()
    else:
        logger.info("No DS nodes available to reset ESXi password...")

    print("\n \n ")
    input("Hit Enter to continue for Password Change for all ESXi Instances on HA Nodes...")

    #ESXI password reset for HA node 
    from quantaskylake import QuantaSkylake
    from esxi import ESXi

    try:
        hatableESXiPassword = prettytable.PrettyTable()
        hatableESXiPassword.field_names = ['IPv6Address','Username','iLOPassword','Model','SerialNumber','ESXiPassword']
        logger.info("Starting Password Change for all ESXi Instances on HA nodes.")
        with open(CSV_FILE_PATH, newline='') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=[
                                    'ipaddress', 'username', 'password','Model','SerialNumber'])
            next(reader)
            servers = list(reader)
            for server in servers:
                # print(server)
                node_address = server['ipaddress'][1:-1]
                logger.info(f"Attempting Esxi Password change for  : {node_address}")
                user = server['username']
                password = server['password']
                esxiuser = "root"
                node = QuantaSkylake(node_address, user, password)
                    #creating ESXi Object 
                passwords = [password, lawcompliance.passwordencode(node.host, getPassword('esxi')), 'Passw0rd!',
                         'Hitachi2019!']
                instance = esxi.ESXi(node, 'root', '')
                for password in passwords:
                    
                    #print(f"initial login  check : {instance.loggedin}")
                    logger.info(node.host + " Attempting to log into ESXi with \"root\" and \"" + password + "\"")
                    instance.password = password
                    try:
                        instance.login()
                        if(instance.loggedin == True):
                            esxipassword = password
                            #backup password policy file 
                            logger.info("Taking backup :  /etc/pam.d/passwd -> /etc/pam.d/passwd.bak")
                            cmdbackup = "cp /etc/pam.d/passwd /etc/pam.d/passwd.bak"
                            instance.apprun(cmdbackup)
                            #command to set password policy from 5 to 0
                            cmd = "sed -i 's/remember=5/remember=0/' /etc/pam.d/passwd"
                            out1 = instance.apprun(cmd)
                            logger.info(f"output policy set to 0 : {out1}")
                            instance.logout()
                            break
                    except Exception as E:
                        logger.info(f"exception occured : {E}")
                        #print(E)
                    


                #quanta_node = QuantaSkylake(node_address, user, esxipassword)
                #creating ESXi Object 
                #node2 = ESXi(node,esxiuser,esxipassword)
                logger.info(f"logging into ESXi for node : {node_address}")
                instance.login()
                error = []
                try:
                    if resetPassword:
                        new_password = "Passw0rd!"
                    else:
                        new_password = lawcompliance.passwordencode(server['ipaddress'][1:-1], autodiscover.getPassword('esxi'))
                    logger.info(f"setting new password on node {node_address} : {new_password}")
                    cmd1 = "esxcli system account set -i root -p "+new_password+" -c "+new_password
                    output = instance.apprun(cmd1)
                    #command to set password policy from 5 to 0
                    logger.info("updated password policy to 5")
                    cmd2 = "sed -i 's/remember=0/remember=5/' /etc/pam.d/passwd"
                    out2 = instance.apprun(cmd2)
                    logger.info(f"output policy set to 5 : {out2}")
                    instance.logout()
                    logger.info(output)
                    if("A general system error occurred:" not in output):
                        logger.info("Password reset completed...")
                        hatableESXiPassword.add_row([node_address, user, password, server['Model'], server['SerialNumber'], new_password])
                    else:
                        logger.info("Password reset failed!")
                except Exception as E:
                    logger.info(f"Error occured during pasword reset for HA Node: {node_address}, error : {E} ")
                    continue


            ######################## pretty table code 
        
            logger.info(f"\n{'='*50} HA Nodes Root ESXi Password Table {'='*50}\n{hatableESXiPassword}")
            logger.info("Password change completed.")
            logger.info("For updated password of HA nodes, please refer to server.csv file.")
            ########################


                #if resetPassword:
                #    reset_ha_servers_password(server['ipaddress'],server['username'],server['password'], "cmb9.admin")
                #else:
                #    new_password = lawcompliance.passwordencode(server['ipaddress'][1:-1], autodiscover.getPassword())
                #    reset_ha_servers_password(server['ipaddress'],server['username'],server['password'], new_password)
    except Exception as e:
        logger.info(f"Password Reset for HA nodes did not complete successfully, please recheck servers.csv has valid entries and rerun. ")
        
    


    logger.info("All done!")

if __name__ == "__main__":
    main()

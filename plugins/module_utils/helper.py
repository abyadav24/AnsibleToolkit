import time
import sys
from pexpect.popen_spawn import PopenSpawn
import ipaddress
import multiprocessing
import os
import copy
import concurrent.futures
from quantaskylake import QuantaSkylake
from datetime import datetime

# SubModule Logging
import logging
logger = logging.getLogger("root")

PROMPT_DICT = {"Y":True,"YES":True, "N":False, "NO":False}

def redfishValidate(nodes):
    # Power on the nodes to have BIOS talk to BMC Chip
    for node in nodes:
        node.poweron()
        time.sleep(2)

    # Start the parallel check
    nodes = copy.deepcopy(nodes)
    returnnodes = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(_redfishValidate, node) for node in nodes]
        for future in concurrent.futures.as_completed(futures):
            returnnodes.append(future.result())

    '''
    for node in nodes:
        # Double check if the node has BIOS Version. If not, wait until node is powered on to get versions.
        count = 0
        logger.info(node.host + ' Starting BIOS Check')
        while count < 40:
            data = node.getSystemsJSON()
            count = count + 1
            try:
                # In Quanta Firmware Mode, BiosVersion key doesn't exist.
                biosversion = data['BiosVersion']
                biosSettings = data['Bios']
                # Look for Bios Registries
                # bioskey = data['Bios']
            except:
                if count == 10:
                    logger.info(node.host + ' may have incorrect BIOS Version Key. Power cycling node.')
                    node.poweroff()
                    time.sleep(10)
                    node.poweron()
                else:
                    logger.info(node.host + ' Missing BiosVersion. Checking again in a minute.')
                time.sleep(60)
                continue

            if len(biosversion) < 1:
            # if len(bioskey) < 1:
                logger.info(node.host + ' BiosVersion is still blank. Checking again in a minute.')
                time.sleep(60)
                continue
            else:
                break

        if count > 19:
            logger.info(node.host + ' WARNING!!! THIS NODE ISN\'T RESPONDING!!! (Also skipping this node.)')
            input("Hit enter to continue")
    '''
    # time.sleep(120)

    # Power off the nodes
    for node in nodes:
        node.poweroff()

    return True

def _redfishValidate(node):
    # Double check if the node has BIOS Version. If not, wait until node is powered on to get versions.
    count = 0
    logger.info(node.host + ' Starting BIOS Check')
    while count < 40:
        data = node.getSystemsJSON()
        count = count + 1
        try:
            # In Quanta Firmware Mode, BiosVersion key doesn't exist.
            biosversion = data['BiosVersion']
            biosSettings = data['Bios']
            # Look for Bios Registries
            # bioskey = data['Bios']
        except:
            if count == 15:
                logger.info(node.host + ' may have incorrect BIOS Version Key. Power cycling node and resetting the BMC.')
                node.poweroff()
                time.sleep(10)
                node.resetBMC()
                time.sleep(240)
                node.poweron()
            else:
                logger.info(node.host + ' Missing BiosVersion. Checking again in a minute.')
            time.sleep(60)
            continue

        if len(biosversion) < 1:
            # if len(bioskey) < 1:
            logger.info(node.host + ' BiosVersion is still blank. Checking again in a minute.')
            time.sleep(60)
            continue
        else:
            break
    if count > 19:
        logger.info(node.host + ' WARNING!!! THIS NODE ISN\'T RESPONDING!!! (Also skipping this node.)')
    return node

def removeAllVMCLI():
    if 'win' in sys.platform:
        '''
        logger.info('Removing all VMCLI instances')
        session = PopenSpawn('sc queryex type= service state= all')
        output = session.read()
        output = output.decode('utf-8')
        output = output.splitlines()
        results = []
        for line in output:
            if 'DISPLAY_NAME: VMCLI_fe80' in line:
                results.append(line.split('DISPLAY_NAME: ')[1])

        for result in results:
            session = PopenSpawn('sc stop ' + result)
            output = session.read()
            output = output.decode('utf-8')
            # logger.info(result + ' ' + output)

        for result in results:
            session = PopenSpawn('sc delete ' + result)
            output = session.read()
            output = output.decode('utf-8')
            # logger.info(result + ' ' + output)
        '''
        logger.info('Removing all VMCLI Instances')
        os.system('taskkill /f /im VMCLI.exe')

def askNodeQuantity():
    while True:
        # Ask for number of nodes
        nodesnum = input('How many nodes (Compute and Management) you working with in this rack? ')

        # Check if its a number
        try:
            val = int(nodesnum)
            if val < 1:
                logger.info('No nodes? Hit enter to exit.')
                input()
                exit(1)
            elif val == 1:
                logger.info('Working with one node.')
            elif val >= 42:
                logger.info(nodesnum + ' node(s) is too many. Please try again.')
                input()
                exit(1)
            else:
                logger.info('Perfect! Let\'s configure ' + nodesnum + ' nodes.')
            logger.info('')
            break
        except ValueError:
            logger.info(str(nodesnum) + ' isn\'t a number. Try again!\n')
    return nodesnum

def askMgmtQuantity():
    while True:
        # Ask for number of management nodes
        mgmtnodesnum = input('How many management nodes you working with in this rack? ')
        try:
            val = int(mgmtnodesnum)
            if val < 1:
                logger.info('No management servers selected')
                # logger.info('No management servers selected')
                logger.info('')
                break
            elif val == 1:
                logger.info('Working with one node')
                logger.info('')
                break
            elif val >= 5:
                input('Too many nodes have been declared. Restart the toolkit and try again.')
            else:
                logger.info('We have ' + mgmtnodesnum + ' nodes in this rack.')
                logger.info('')
                break
        except ValueError:
            logger.info(str(mgmtnodesnum) + ' isn\'t a number!!! Try again!\n')
    return mgmtnodesnum

def askRackNumber():
    while True:
        # Ask for Rack Number
        racknum = input('Which rack number are you working on? ')

        # Check if its a number
        try:
            val = int(racknum)
            logger.info('You have chosen ' + racknum + '!!! Let\'s continue. \n')
            break
        except ValueError:
            logger.info(str(racknum) + ' isn\'t a number!!! Try again!\n')
    return racknum

def massIPv4AddressRestore(nodes):
    logger.info('Starting Mass IPv4 Address Programming')
    tuples = []
    for node in nodes:
        if 'Static' in node.ipv4Src:
            tuples.append((node.setIPv4Address,str(node.ipv4Address), node.ipv4Subnet, node.ipv4Gateway))
    pool = multiprocessing.Pool(processes=10)
    results = pool.starmap(run, tuples)
    pool.close()
    pool.join()
    logger.info('Waiting 1 minute to have everything settle.')
    time.sleep(60)

def massIPv4AddressProgram(nodes, startipaddress, subnet, gateway):
    logger.info('Starting Mass IPv4 Address Programming')
    ipcounter = ipaddress.IPv4Address(startipaddress)

    tuples = []
    for node in nodes:
        tuples.append((node.setIPv4Address, str(ipcounter), subnet, gateway))
        ipcounter = ipcounter + 1
    pool = multiprocessing.Pool(processes=10)
    results = pool.starmap(run, tuples)
    pool.close()
    pool.join()
    time.sleep(10)

def massSubnetIPv4AddressProgram(nodes, subnet, gateway):
    logger.info('Starting Mass IPv4 Address Programming')

    tuples = []
    for node in nodes:
        tuples.append((node.setIPv4SubnetAddress, subnet, gateway))
    pool = multiprocessing.Pool(processes=10)
    results = pool.starmap(run, tuples)
    pool.close()
    pool.join()
    time.sleep(10)

def run(function, *args):
    return function(*args)

def massStartVMCLI(nodes, iso):
    vmcli_nodes = copy.deepcopy(nodes)
    temp_nodes = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(startVMCLI, node, iso) for node in vmcli_nodes]
        for future in concurrent.futures.as_completed(futures):
            temp_nodes.append(future.result())

    return temp_nodes

# VMClI Helper
def startVMCLI(node, iso):
    node.startVMCLIapp(iso)
    return node

def setnodeIPv4Address(node, ipv4Address, ipv4Subnet, ipv4Gateway):
    node.setIPv4Address(ipv4Address,ipv4Subnet,ipv4Gateway)

def askForTargetSwitch():
    while True:
        # Ask for Rack Number

        ask = input('Do you only want to discover the switches  on the Rack(Yes-Y or No-N)?: ')

        # Check if its a number
        try:
            return  PROMPT_DICT[ask.capitalize()]
        except Exception as e:
            logger.info(f"Choose Between Yes(Y) and No(N)")
    # return val

def askForSwitches():
    while True:
        # Ask for Rack Number
        switchnum = input('How many switches are in the rack? ')

        # Check if its a number
        try:
            val = int(switchnum)
            if val > 0:
                logger.info('There are switches!')
                return True
            elif val == 0:
                logger.info('There are No switchs in the rack.')
                return False
            break
        except ValueError:
            logger.info(str(switchnum) + ' isn\'t a number!!! Try again!\n')
    return False

# def detectNodeOrderLoop(nodes, starttime):
#     count = 0
#     while True:
#         input('Starting from the bottom node to the top node, press the power button one by one (Wait 5 seconds between presses). Hit enter once this task has been completed.')
#         logger.info('Please wait...')
#         nodes = getButtonTimeNodes(nodes)
#         nodes = sortNodes(nodes)
#         logger.info('Button Press Sorted #' + str(count)+' ' + datetime.now().strftime('%m/%d/%Y  %H:%M:%S') + ':')
#         for node in nodes:
#             logger.info(node.host + ' ' + node.lastButtonTime.strftime('%m/%d/%Y %H:%M:%S'))
#         pressed = True
#         for node in nodes:
#             if node.lastButtonTime < starttime:
#                 pressed = False
#         if pressed == True:
#             input('Awesome! All the buttons have been pressed! Hit enter to continue.')
#             break
#         else:
#             logger.info('Uffff.... All the power buttons haven\'t been pressed yet. Please try again.\n')
#         count += 1
#     return nodes

def getButtonTimeNodes(nodes):
    # Tell nodes to get last button time
    tuples = []
    for node in nodes:
        tuples.append((node,))
    pool = multiprocessing.Pool(processes=30)
    results = pool.starmap(QuantaSkylake.getLastButtonTime, tuples)
    pool.close()
    pool.join()
    # Return updated nodes
    return results

def sortNodes(nodes):
    # Return sorted nodes by button press time
    return sorted(nodes, key=lambda node: node.lastButtonTime)

def initialize():
    return False
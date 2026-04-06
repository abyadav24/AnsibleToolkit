from datetime import datetime
import helper
import badtime
import autodiscover
import ipaddress

def main():
    # Store Current Time
    starttime = datetime.now()
    helper.removeAllVMCLI()

    # Print welcome screen
    badtime.hitachi()
    badtime.version()
    print('\nI have to ask a few questions to get started.\n')

    IPv6Devices = autodiscover.useTargetNodes()
    if len(IPv6Devices) == 0:
        # Ask the user which rack number they are working on
        racknum = helper.askRackNumber()

        # Ask the user how many nodes that rack has
        nodesnum = helper.askNodeQuantity()
    else:
        racknum = 1
        nodesnum = len(IPv6Devices)

    while True:
        # Get D52B Nodes
        nodes = autodiscover.discoverNodes(autodiscover.getIPv6Neighbors(), ['admin'], ['cmb9.admin'])

        print('\nGetting IPv4 Addresses via IPv6 Link-Local Addresses')
        for node in nodes:
            node.getIPv4Address()
        print(' ')

        # Let the user know about the detected nodes
        if len(nodes) < 1:
            input('Uffff.... I wasn\'t able to detect any nodes man. Sorry about that. Hit enter to try again.')
        elif len(nodes) != int(nodesnum):
            input('Uh oh, I have detected a ' + str(len(nodes)) + ' node(s) in the rack, instead of ' + nodesnum + '.\nPlease make sure all the BMC connections are connected or disconnected on the same flat network. Hit enter to try again.')
        else:
            input('Perfect! I have detected ' + str(len(nodes)) + '!!! Hit enter to continue!\n')
            break

    print('\nI need a few details to continue BMC IPv4 Address Programming.\n')

    while True:
        subnet = input('What is the subnet? (I.E. 255.255.255.0) ')
        try:
            subnet = ipaddress.IPv4Address(subnet)
            break
        except Exception:
            print(subnet + ' is not a valid choice. Please try again.')
            continue

    while True:
        gateway = input('What is the gateway? (Note: Enter 0.0.0.0 for blank gateway.) ')
        try:
            gateway = ipaddress.IPv4Address(gateway)
            break
        except Exception:
            print(gateway + ' is not a valid choice. Please try again.')
            continue

    helper.massSubnetIPv4AddressProgram(nodes, subnet, gateway)

    badtime.okay()

if __name__ == "__main__":
    main()
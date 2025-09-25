#!/bin/bash

# Check for Ethernet device
lspci -mm | grep -i ethernet

# Print message
echo "Extracting /cdrom/firmware/'Intel(R)_Ethernet_Network_Adapter_X710-T4L_for_OCP_3.0'/700Series_NVMUpdatePackage_v9_50_Linux.tar.gz"

# Extract the firmware
sudo tar -xf "/cdrom/firmware/Intel(R)_Ethernet_Network_Adapter_X710-T4L_for_OCP_3.0/700Series_NVMUpdatePackage_v9_50_Linux.tar.gz" -C /tmp

# Change permissions
sudo chmod -R 777 /tmp

# Get the LAN MAC address
LAN_MAC=$(sudo /tmp/700Series/Linux_x64/nvmupdate64e -i -l | grep 'LAN MAC' | head -n 1 | awk '{print $NF}')
echo $LAN_MAC

# Perform the device update
sudo "/tmp/700Series/Linux_x64/nvmupdate64e" -a "/tmp/700Series/Linux_x64/" -u -m $LAN_MAC -l -f

# Check the logs for successful update
#if grep -q "Device update successful" /tmp/update_logs.txt; then
	echo "==========================================================================="
	echo "                                                                           "
    echo "Successfully Flashed Intel(R)_Ethernet_Network_Adapter_X710-T4L_for_OCP_3.0"
#fi


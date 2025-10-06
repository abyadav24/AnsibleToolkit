import csv
import os
import subprocess
import time

executable_path = os.getcwd() +"\\HA8XX_scripts\\"

# Define path to CSV file containing server details
os.chdir(executable_path)
os.environ['PATH'] += executable_path

server_file = executable_path +"\servers.csv"
headerList=['ipaddress', 'username', 'password', 'model', 'sn']
servers=[]
# Open CSV file and read contents into a list of dictionaries
def run():

    while True:
        print("\n\nWhat solution are you working on?\n\n"
                    "1. UCP VMware.\n"
                    "2. Asure Stack HCI.\n")

        option_selected = input("Please select one : ")
        if option_selected == "1" or option_selected == "2":
            break

        print("Invalid selection. Please try again.")

    with open(server_file, 'r') as file:
        reader = csv.DictReader(file, delimiter=',', fieldnames=headerList)
        next(reader)
        print("Reading server.csv...")
        for row in reader:
            servers.append(row)
            print(row)
    # Loop through each server and execute ilorest commands
    for server in servers:
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        model = server['model']

        command1 = f"ilorest\ilorest login {ipaddress} -u {username} -p {password}"
        print(f"\nExecuting >>>> {command1}")
        subprocess.call(command1, shell=True)

        executable_path = os.getcwd()
        print(f"Path : {executable_path}")
        executable_path = executable_path + "//HA-G2-G3BiosTemplates//"

        if option_selected == "1":
            command = 'ilorest\\ilorest load -f ' + executable_path + 'HA_G2_Intel_HA810_HA820_G2.json'
            if model == "Hitachi Advanced Server HA805 G3" or model == "Hitachi Advanced Server HA815 G3" or model == "Hitachi Advanced Server HA825 G3":
                command = 'ilorest\\ilorest load -f' + executable_path + 'HA_G3_AMD_HA805_HA815_825_G3.json'
            elif model == "Hitachi Advanced Server HA810 G3" or model == "Hitachi Advanced Server HA820 G3":
                command = 'ilorest\\ilorest load -f ' + executable_path + 'HA_G3_Intel_HA810_HA820_G3.json'
            elif model == "Hitachi Advanced Server HA840 G3":
                command = 'ilorest\\ilorest load -f ' + executable_path + 'HA_G3_HA840_G3.json'
        if option_selected == "2":
            command = 'ilorest\\ilorest load -f ' + executable_path + 'HA_G2_ASHCI.bios.json'
            if model == "Hitachi Advanced Server HA805 G3" or model == "Hitachi Advanced Server HA815 G3" or model == "Hitachi Advanced Server HA825 G3":
                command = 'ilorest\\ilorest load -f'+executable_path+ 'HA_G3_ASHCI_AMD_HA805_HA815_825_G3.json'
            elif model == "Hitachi Advanced Server HA810 G3" or model == "Hitachi Advanced Server HA820 G3":
                command = 'ilorest\\ilorest load -f'+executable_path+ 'HA_G3_ASHCI.bios.json'
            elif model == "Hitachi Advanced Server HA840 G3":
                command = 'ilorest\\ilorest load -f'+executable_path+ 'HA_G3_ASHCI.bios.json'


        print(f"\n Applying BIOS Template for : {model}")
        print(f"Executing >>>> {command}")
        subprocess.call(command, shell=True)
        time.sleep(5)

        command4 = "ilorest\ilorest reboot"
        print(f"\nExecuting >>>> {command4}")
        subprocess.call(command4, shell=True)


if __name__ == "__main__":
    run()
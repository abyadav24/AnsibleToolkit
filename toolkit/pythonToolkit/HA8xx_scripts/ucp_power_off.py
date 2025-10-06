import csv
import subprocess
import os 


executable_path = os.getcwd() +"\\HA8XX_scripts\\"
# Define path to CSV file containing server details
#csv_path = "servers.csv"
os.chdir(executable_path)
# Open CSV file and read contents into a list of dictionaries
servers = []
server_file = executable_path +"\servers.csv"
headerList=['ipaddress', 'username', 'password']
with open(server_file, 'r') as file:
    reader = csv.DictReader(file, delimiter=',', fieldnames=headerList)
    next(reader)
    for row in reader:
        servers.append(row)

# Loop through each server and execute ilorest commands
for server in servers:
    print(server)
    ipaddress = server['ipaddress']
    username = server['username']
    password = server['password']
    command1 = f"ilorest\\ilorest login {ipaddress} -u {username} -p {password}"
    subprocess.call(command1, shell=True)
    command2 = "ilorest\\ilorest reboot ForceOff"
    subprocess.call(command2, shell=True)

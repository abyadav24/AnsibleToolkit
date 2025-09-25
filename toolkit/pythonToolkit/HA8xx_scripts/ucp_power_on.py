import csv
import subprocess
import os


executable_path = os.getcwd() +"\\HA8XX_scripts\\"
os.chdir(executable_path)
print(executable_path)
# Define path to CSV file containing server details


# Open CSV file and read contents into a list of dictionaries

servers = []
server_file = executable_path +"\servers.csv"
headerList=['ipaddress', 'username', 'password']
with open(server_file, 'r') as file:
    reader = csv.DictReader(file, delimiter=',', fieldnames=headerList)
    next(reader)
    for row in reader:
        servers.append(row)

executable_path = executable_path+"ilorest\\"
os.environ['PATH'] += os.pathsep + executable_path
# Loop through each server and execute ilorest commands
for server in servers:
    print(server)
    ipaddress = server['ipaddress']
    username = server['username']
    password = server['password']
    command1 = executable_path+f"ilorest login {ipaddress} -u {username} -p {password}"
    subprocess.call(command1, shell=True)
    command2 = executable_path+"ilorest reboot on"
    subprocess.call(command2, shell=True)

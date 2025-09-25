import csv
import subprocess
import os 

# Open CSV file and read servers data
executable_path = os.getcwd() +"\\HA8XX_scripts\\"
os.chdir(executable_path)

servers = []
server_file = executable_path +"\servers.csv"
headerList=['ipaddress', 'username', 'password']
with open(server_file, 'r') as file:
    reader = csv.DictReader(file, delimiter=',', fieldnames=headerList)
    next(reader)
    for row in reader:
        servers.append(row)

# Iterate through servers and add new admin account with specified password
for server in servers:
    ipaddress = server['ipaddress']
    username = server['username']
    password = server['password']
    cmd = f"ilorest\ilorest iloaccounts add admin admin cmb9.admin --role=Administrator --url {ipaddress} -u {username} -p {password}"
    print(cmd)
    subprocess.call(cmd, shell=True)

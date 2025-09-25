import csv
import subprocess
import time
import os

executable_path = os.getcwd() +"\\HA8XX_scripts\\"
os.chdir(executable_path)

# Shut down nginx server
subprocess.call("taskkill /f /im nginx.exe", shell=True)
time.sleep(3)

# Start nginx server on port 8080
print("###Starting Web Server on http port ###")
subprocess.call("start /b nginx", shell=True)

# Prompt user for ISO URL
print("Please navigate to http://[IPv6] of this jumphost in a browser for the URL for the ISO")
isourl = input("URL of ISO : ")

# Define path to CSV file containing server details
servers = []
server_file = executable_path +"\servers.csv"
# Open CSV file and read contents into a list of dictionaries
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
    command1 = f"ilorest\ilorest login {ipaddress} -u {username} -p {password}"
    subprocess.call(command1, shell=True)
    command2 = "ilorest\ilorest virtualmedia 2 --remove"
    subprocess.call(command2, shell=True)
    command3 = f"ilorest\ilorest virtualmedia 2 {isourl} --bootnextreset"
    subprocess.call(command3, shell=True)
    command4 = "ilorest\ilorest reboot"
    subprocess.call(command4, shell=True)

# Wait 10 minutes before shutting down nginx server
print("Sleeping for 30 minutes before shutting down web server")
time.sleep(1800)

# Shut down nginx server
subprocess.call("taskkill /f /im nginx.exe", shell=True)

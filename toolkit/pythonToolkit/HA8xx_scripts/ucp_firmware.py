import csv
import subprocess
import time
import os

executable_path = os.getcwd() + "\HA8XX_scripts"
csv_file = f'{executable_path}/servers.csv'
os.chdir(executable_path)
os.environ['PATH'] += executable_path
# print(executable_path)
# # Add the executable path to the PATH environment variable
os.environ['PATH'] += executable_path

def kill_nginx():
    subprocess.Popen(['taskkill', '/f', '/im', 'nginx.exe'], shell=True)

def start_nginx():
    print("###Starting Web Server on http port ###", flush=True)
    res = subprocess.Popen(['start', '/b', 'nginx'], shell=True,
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(res)


def load_csv_file():

    # Load the CSV file and assign headers to the columns
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile, fieldnames=[
                                'ipaddress', 'username', 'password'])
        next(reader)
        servers = list(reader)
    return servers
def execute_firmwareupdate(servers):
    print("Please navigate to http://[IPv6] of this jumphost in a browser for the URL for the ILO BIN")
    binurl = input("URL of ILO BIN : ")
    # binurl = 'http://10.76.33.240:8080/Hitachi_CustomIP_SUM_ILO_Created2_19_2021.signed.bin'
    # Iterate over each server and run the commands
    for server in servers:
        print(server, flush=True)
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        subprocess.run(['ilorest\\ilorest', 'login', ipaddress,
                    '-u', username, '-p', password], shell=True)
        subprocess.run(['ilorest\\ilorest', 'firmwareupdate', binurl], shell=True)

#print("Sleeping for 10 minutes before shutting down web server", flush=True)
# time.sleep(600)

# subprocess.Popen(['taskkill', '/f', '/im', 'nginx.exe'], shell=True)

def main():
    kill_nginx()
    time.sleep(5)
    start_nginx()

    servers = load_csv_file()
    execute_firmwareupdate(servers)

    print("Sleeping for 10 minutes before shutting down web server", flush=True)
    time.sleep(600)
    kill_nginx()
if __name__ == "__main__":
    main()
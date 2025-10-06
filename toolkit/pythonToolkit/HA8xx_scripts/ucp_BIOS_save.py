import os
import subprocess
import logging

logger = logging.getLogger(__name__)
executable_path = os.getcwd() + "\HA8XX_scripts"
# Define path to CSV file containing server details
os.chdir(executable_path)
os.environ['PATH'] += executable_path


def cup_bios_save():
    # Prompt user for ILO details
    ILO_IP = input("\nPlease Enter the IPv4 or [IPv6] of the ILO (For IPv6 use square brackets [IPv6]) : ")
    ILO_USER = input("Please Enter the Username of the ILO: ")
    ILO_PASSWORD = input("Please Enter the Password of the ILO: ")

    FILE = ILO_IP
    if "[" in FILE:  # check for IPv6
        Ipv6 = ILO_IP[1:-1]
        FILE = Ipv6.split(":")[-1]

    # Execute ilorest command

    command = f"ilorest\ilorest save --select Bios. --url {ILO_IP} -u {ILO_USER} -p {ILO_PASSWORD} -f {FILE}_ilorest.json"
    print("\nExecuting: " + command)
    subprocess.call(command, shell=True)


if __name__ == "__main__":
    cup_bios_save()

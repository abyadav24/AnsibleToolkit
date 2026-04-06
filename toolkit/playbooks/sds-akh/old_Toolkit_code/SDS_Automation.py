import csv
import tempfile
import os
import subprocess
import time
import logging
import sys
import logging
import sys
from esxi import ESXi 
from quantaskylake import QuantaSkylake
sys.path.append('/path/to/site-packages')
from pexpect.popen_spawn import PopenSpawn
import pexpect
import sys
import quantaskylake


executable_path = os.getcwd() +"\\HA8XX_scripts\\AutoHotkey"
sys.path.insert(1,executable_path)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a file handler
log_file_path = os.path.join(executable_path, "SDS-Automation.log")
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter and set it for the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

##############################################################################################################################################################################
#SDS Code to Setup HA nodes with SDS BareMetal configuration.

ini_files_array = []
setup_password_files_array = []
set_setting_files_array = []

def countdown_timer(seconds):
    while seconds:
        mins, secs = divmod(seconds, 60)
        timer = '{:02d}:{:02d}'.format(mins, secs)
        print(f"{timer} sec remaining", end='\r')  # Display countdown in console
           # Log countdown to file
        time.sleep(1)
        seconds -= 1

    print("Countdown complete!")

def create_change_setup_pass(ini_files_array,executable_path):
    #path to template for change setup password
    change_setup_password = f"{executable_path}\\ahk_templates\\setup_password_template.ahk"
    with open(change_setup_password, 'r') as file:
        ahk_script = file.read()

    for index, item in enumerate(ini_files_array, start=1):
        if item:
            updated_change_setup_password = ahk_script.replace('iniFilePath := ""', f'iniFilePath := "{item}"')
            updated_change_setup_password_file = os.path.join(executable_path, f"updated_change_setup_password_{index}.ahk")
            #updated_change_setup_password_file = f"updated_change_setup_password_{index}.ahk"
            with open(updated_change_setup_password_file, 'w') as file:
                file.write(updated_change_setup_password)
                setup_password_files_array.append(updated_change_setup_password_file.split("\\")[-1])

            logging.info(f"Updated AHK script for {item}:")
            logging.info(f"\nTemporary updated_change_setup_password_{index} file created.")
            time.sleep(2)
    return setup_password_files_array

def create_set_setting(ini_files_array,executable_path):
    change_setup_password = f"{executable_path}\\ahk_templates\\set_setting_template.ahk"
    with open(change_setup_password, 'r') as file:
        ahk_script = file.read()
    for index, item in enumerate(ini_files_array, start=1):
        if item:
            updated_set_setting = ahk_script.replace('iniFilePath := ""', f'iniFilePath := "{item}"')
            #updated_change_setup_password_file = os.path.join(executable_path, f"updated_change_setup_password_{index}.ahk")
            updated_set_setting_file = os.path.join(executable_path, f"updated_set_setting_{index}.ahk")
            
            #updated_set_setting_file = f"updated_set_setting_{index}.ahk"
            with open(updated_set_setting_file, 'w') as file:
                file.write(updated_set_setting)
                set_setting_files_array.append(updated_set_setting_file.split("\\")[-1])
            logging.info(f"Updated AHK script for {item}:")
            logging.info(f"\nTemporary updated_set_setting_{index} file created.")
            time.sleep(2)
    return set_setting_files_array

def create_ini_file(data, index,executable_path):
    ini_content = f"[ilo]\nhost={data['host']}\nuser={data['user']}\npw={data['pw']}\n[node]\nsetup_pw={data['setup_pw']}\nhostname={data['hostname']}\n[controlnw]\nipv4address={data['ipv4address']}\nsubnetmask={data['subnetmask']}\nmtu={data['mtu']}\nroute_count={data['route_count']}\nroute_destination1={data['route_destination']}\nroute_gateway1={data['route_gateway']}"

    #file_name = f"SN{index}.ini"
    file_name = os.path.join(executable_path, f"SN{index}.ini")
    with open(file_name, 'w') as file:
        ini_files_array.append(file_name)
        file.write(ini_content)
        logging.info(f"\nTemporary {file_name} file created.")
    logging.info(f"\n Ini files created  : {ini_files_array}")
    print(f"ini files array : \n{ini_files_array}")

def call_Ahkfiles(ini_files_array,setup_password_files_array, set_setting_files_array,executable_path):
    logging.info("Killing any existing instance of AutoHotKey if running...")
    kill_ahk_cmd = f'taskkill /F /IM {executable_path}\\AutoHotkeyU64.exe"'
    try:
        #kill_ahk_out = subprocess.run(kill_ahk_cmd, capture_output=True, text=True, shell=True)
        kill_ahk_out = subprocess.run(kill_ahk_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout_output = kill_ahk_out.stdout.decode('utf-8')
        stderr_output = kill_ahk_out.stderr.decode('utf-8')
        logging.info(f"Command Prompt Output: {stdout_output}")
        #logging.info(f"Command Prompt Output:, {kill_ahk_out.stdout}")
    except subprocess.CalledProcessError as e:
        logging.info(f"Error executing command-{kill_ahk_out}, error : {e}")

    logging.info("Proceeding to configure password and configure settings for All Nodes in a sequence.\nDo not interupt the execution, do not make any movements through mouse or keymoard...")
    ini_files_array.sort()
    setup_password_files_array.sort()
    set_setting_files_array.sort()

    ahk_exe_file = f"{executable_path}\AutoHotkeyU64.exe"
    path = f"{executable_path}\\"

    for item1, item2, item3 in zip(setup_password_files_array,set_setting_files_array, ini_files_array):

        #logging.info(f"\n \nConfiguring Password for Node : {item3.split('.')[0].split('SN')[-1]}...")
        sn_number = next((part.split("SN")[-1].split(".")[0] for part in item3.split("\\") if "SN" in part), None)
        logging.info(f"\n\nConfiguring Password for node : {sn_number}")
        setup_pass_cmd = ahk_exe_file +" "+ path+item1 +" "+ item3
        logging.info(f"\n\tpassing command  : {setup_pass_cmd}")
        cmd_output1 = subprocess.run(setup_pass_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout_output = kill_ahk_out.stdout.decode('utf-8')
        stderr_output = kill_ahk_out.stderr.decode('utf-8')
        logging.info(time.sleep(10))
    
        sn_number = next((part.split("SN")[-1].split(".")[0] for part in item3.split("\\") if "SN" in part), None)
        logging.info(f"\n\tConfiguring settings for Node : {sn_number}")
        set_setting_cmd = ahk_exe_file +" "+ path+item2 +" "+ item3
        logging.info(f"\n\tpassing command  : {set_setting_cmd}")
        
        cmd_output1 = subprocess.run(set_setting_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        logging.info("Sleeping for 20 Sec, please wait...")
        logging.info(time.sleep(20))
        try:
            
            kill_ahk_out = subprocess.run(kill_ahk_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout_output = kill_ahk_out.stdout.decode('utf-8')
            stderr_output = kill_ahk_out.stderr.decode('utf-8')
        except subprocess.CalledProcessError as e:
            logging.info("\nError executing command: {e}")

        logging.info(f"\n \n \n Configuring completed for Node: {sn_number}")


        countdown_time = 10
        #logging.info(f"\n \n \nNow proceeding to configure Node{int(item3.split('.')[0].split('SN')[-1])+1} in, {countdown_time} sec")
        logging.info("Proceeding to configure if any Next Node available...")
        countdown_timer(countdown_time)
    
    logging.info("Script Execution Completed...")

def read_baremetalserver_csv(file_name, executable_path):
    logging.info("Welcome to SDS Baremetal Configuration Automation using Toolkit and AutoHotKey !!!")
    input("\nHit enter to continue...")
    logging.info("Please make sure, SDS_BaremetalserverDetails.csv file is updated.")
    logging.info("Starting SDS_automation...")
    input("\nHit enter to continue...")
    logging.info("creating ini files using SDS_BaremetalserverDetails.csv data...")
    with open(file_name, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for index, row in enumerate(reader, start=1):
            create_ini_file(row, index,executable_path)
            time.sleep(2)

    logging.info("Creating AHK files for configuring  password.")
    setup_password_files_array = create_change_setup_pass(ini_files_array,executable_path)
    logging.info(f"created change setup password files : \n{setup_password_files_array}")
    set_setting_files_array = create_set_setting(ini_files_array,executable_path)
    logging.info(f"created set setting  files : \n{set_setting_files_array}")

    logging.info(f"Calling AHK files..")
    call_Ahkfiles(ini_files_array,setup_password_files_array, set_setting_files_array, executable_path)
    print("Done")



#################################################################################################################################################################################

#SDS Code to Setup HA nodes with SDS ESXi configuration.
vssb_setup_conif = {"1":"SDS Steup for Bare Metal",
                     "2":"SDS Setup for ESXi",
                     "3":"EXIT"
                    }


def read_esxiserver_csv(file_name):
    logging.info(f"Please make sure, SDS_ESXiserversDetails.csv file is updated and placed at below location : \n{file_name}")
    input("\nHit Enter to Continue if you have updated SDS_ESXiserverDetails.csv.\n")
    logging.info(f"Reading Data from {file_name}")
    servers = []
    with open(file_name, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for index, row in enumerate(reader, start=1):
            server = {
                "ipv6": row["ipv6"],
                "user": row["user"],
                "pw": row["pw"],
                "hostname": row["hostname"],
                "ipv4address": row["ipv4address"],
                "subnetmask": row["subnetmask"],
                "gateway": row["gateway"],
                "primaryDNS": row["primaryDNS"],
                "secondaryDNS": row["secondaryDNS"]
            }
            servers.append(server)
    return servers
        
def find_vmnic_with_link_up(output, link_status_column="Link Status"):
  """
  Parses the provided output string and returns the name of the first vmnic
  with the specified link status column value (default is "Link Status").

  Args:
    output: A string containing the output of the command.
    link_status_column: The name of the column containing the link status information (default is "Link Status").

  Returns:
    The name of the vmnic with the specified link status, or None if none is found.
  """

  lines = output.splitlines()  # Split the output into lines

  try:
    headers = lines[0].split()  # Get the header names
    link_status_index = headers.index(link_status_column)

    for line in lines[1:]:  # Skip the header line
      values = line.split()
      if values[link_status_index] == "Up":
        return values[0]  # Return the vmnic name (first element)

  except ValueError:  # Handle case where link_status_column is not found
    print(f"Error: Column '{link_status_column}' not found in output headers.")
    return None  # Or raise a more specific exception if needed

  return None  # No vmnic with specified link status found

def SDS_ESXiSetup():
    logging.info(f"Setting up servers for SDS ESXi.\n")
    logging.info(f"Reading Server details from SDS_ESXiServerdetails.csv")
    #print("\nSetting up SDS servers for ESXi ")
    #print("\nReading Server details from SDS_ESXiServerdetails.csv")

    #read all server and configuration form SDS_ESXiserverDetails.csv
    try:
        servers = read_esxiserver_csv(executable_path+"\\config\\SDS_ESXiserverDetails.csv")
    except Exception as e:
        return {"Message ": e}

    #List of ESXi Commands :
    cmd1 = "esxcli network nic list"   #list vmnic list
    cmd2 =""
    cmd3 = "esxcli network ip interface ipv4 get"   # get vmkernal on esxi
    cmd4 = ""
    cmd5 = "esxcli system hostname set --host =vssbnode1"   #sethostname
    cmd6 = ""    # set DNS server 
    cmd7 = "/etc/init.d/hostd restart"    #restart server 
    cmd8 = "/etc/init.d/vpxa restart"     #restart server
    cmd9 = "esxcli network vswitch standard add --vswitch-name=soph-comp"  #add vswitch soph-comp
    cmd10 = "esxcli network vswitch standard add --vswitch-name=soph-inter-srg"      #addd vswitch soph-inter-srg
    cmd11 = "esxcli network vswitch standard portgroup add --portgroup-name=soph-comp-group --vswitch-name=soph-comp"    #add port group 
    cmd12 = "esxcli network vswitch standard portgroup add --portgroup-name=soph-inter-srg-group --vswitch-name=soph-inter-srg"
    cmd13 = "esxcli network vswitch standard portgroup add --portgroup-name=soph-mng-group --vswitch-name=vSwitch0"
    catch_error = []
    
    #PORT GROUP : SWITCH 
    #soph-comp-group   : soph-comp
    #soph-inter-srg-group : soph-inter-srg
    #soph-mng-group : vSwitch0

    for item in servers:
        #print(f"server : \n{item}")
        node_address=item["ipv6"][1:-1]
        logging.info(f"{node_address} : Setting Up ESXi server for SDS setup.")
        user=item["user"]
        password=item["pw"]
        ipv4address = item["ipv4address"].strip()
        subnetmask = item["subnetmask"]
        gateway = item["gateway"]
        primaryDNS = item["primaryDNS"]
        secondaryDNS = item["secondaryDNS"]
        hostname = item["hostname"].strip()
        esxiuser = "root"
        esxipassword = "Passw0rd!"

        #creating QuantaSkylake Object 
        quanta_node = QuantaSkylake(node_address, user, password)

        #creating ESXi Object 
        node = ESXi(quanta_node,esxiuser,esxipassword)
        node.login()
        error = []

        
        #get connected nics list
        logging.info(f"{node_address}: Get Available Network list \n\ncommand passed : {cmd1}")
        try:
            output = node.apprun(cmd1)
            logger.info(f"output : {output}")
        except Exception as E:
            error.append(E)
        arr = output.strip().split('\n')[2:]
        for item in arr:
            item_values = [value for value in item.split(" ") if value]  # Remove empty strings
            if item_values[4] == "Up" and int(item_values[5]) > 0:
                print(f"vmnic up found : {item_values[0]}")
                vmnic=item_values[0]
                break

        #create uplink to vswitch0 Need to make this hard code dynamic
        #vmnic = "vmnic4"
        cmd2 = f"esxcli network vswitch standard uplink add -u "+vmnic+" -v vSwitch0"
        logging.info(f"{node_address}: Create an uplink to {vmnic}\n\ncommand passed : {cmd2}")
        try:
            output = node.apprun(cmd2)
            logger.info(f"output: {output}")
        except Exception as E:
            error.append(E)

        #getVM kernal
        logging.info(f"{node_address}: Get VM kernal on ESXi.\n\ncommand passed : {cmd3}")
        try:
            output = node.apprun(cmd3)
            logging.info(f"output: {output}")
            lines = output.strip().split('\n')
            # Iterate through the lines to find the line with the IPv4 Address
            for line in lines[2:]:
                if '.' in line:
                    try:
                        vmk_interface = line.split()
                        vmk = vmk_interface[0]
                        print(f"vmvernal : {vmk}")
                        break
                    except Exception as E:
                        logger.info(f"Exception occured :{E}")
                        break
        except Exception as E:
            error.append(E)

        
        #cmd4 = "esxcli network ip interface ipv4 set -i "+vmk+" -I "+ipv4address+" -N "+subnetmask+" -g "+gateway+" -t static"
        cmd4 = "esxcli network ip interface ipv4 set --interface-name="+vmk+" --ipv4="+ipv4address+" --netmask="+subnetmask+" --type=static --gateway="+gateway
        #cmd4 = "esxcli network ip interface ipv4 set –i "+vmk+" -t static –g "+gateway+" -I "+ipv4address+" -N "+subnetmask
        logging.info(f"{node_address}: Set static ipv4, subnetmask and gateway.\n\ncommand passed : {cmd4}")
        try:
            output = node.apprun(cmd4)
            logger.info(f"output: {output}")    
        except Exception as E:
            error.append(E)

        cmd40 = "esxcfg-route "+gateway
        #cmd4 = "esxcli network ip interface ipv4 set –i "+vmk+" -t static –g "+gateway+" -I "+ipv4address+" -N "+subnetmask
        logging.info(f"{node_address}: Set static ipv4, subnetmask and gateway.\n\ncommand passed : {cmd40}")
        try:
            output = node.apprun(cmd40)
            logger.info(f"output: {output}")    
        except Exception as E:
            error.append(E)
        
        
        cmd5 = "esxcli system hostname set --host="+hostname
        logging.info(f"{node_address}: Set hostname.\n\ncommand passed : {cmd5}")
        try:
            output = node.apprun(cmd5)
            logging.info(f"output: {output}") 
        except Exception as E:
            error.append(E)

        #Secondary dns need to add 
        cmd6 = "esxcli network ip dns server add --server="+primaryDNS
        cmd66 = "esxcli network ip dns server add --server="+secondaryDNS
        logging.info(f"{node_address}: Set dns server.\n\ncommand passed : {cmd6}")
        logging.info(f"{node_address}: Set dns server.\n\ncommand passed : {cmd66}")
        try:
            output = node.apprun(cmd6)
            output = node.apprun(cmd66)
            logging.info(f"output: {output}") 
        except Exception as E:
            error.append(E)

       
        logging.info(f"{node_address}: Service hostd restart.\n\ncommand passed : {cmd7}")
        try:
            output = node.apprun(cmd7)
            logging.info(f"output: {output}") 
        except Exception as E:
            error.append(E)


  
        logging.info(f"{node_address}: Service vxpa restart.\n\ncommand passed : {cmd8}")
        try:
            output = node.apprun(cmd8)
            logging.info(f"output: {output}") 
        except Exception as E:
            error.append(E)

     
        logging.info(f"{node_address}: Add vswitch standard name :soph-comp.\n\ncommand passed : {cmd9}")
        try:
            output = node.apprun(cmd9)
            logging.info(f"output: {output}") 
        except Exception as E:
            error.append(E)
       

        logging.info(f"{node_address}: Add vswitch standard name :soph-inter-srg.\n\ncommand passed : {cmd10}")
        try:
            output = node.apprun(cmd10)
            logging.info(f"output: {output}") 
        except Exception as E:
            error.append(E)
        
        logging.info(f"{node_address}: Add vswitch standard portgroup :soph-comp-group.\n\ncommand passed : {cmd11}")
        try:
            output = node.apprun(cmd11)
            logging.info(f"cmd11: {output}") 
        except Exception as E:
            error.append(E)

        logging.info(f"{node_address}: Add vswitch standard portgroup :soph-inter-srg-group.\n\ncommand passed : {cmd12}")
        try:
            output = node.apprun(cmd12)
            logging.info(f"cmd12: {output}") 
        except Exception as E:
            error.append(E)

        logging.info(f"{node_address}: Add vswitch standard portgroup :soph-mng-group.\n\ncommand passed : {cmd13}")
        try:
            output = node.apprun(cmd13)
            logging.info(f"cmd13: {output}") 
        except Exception as E:
            error.append(E)

        if(error == []):
            logging.info(f"{node_address} : SDS Node Setup Completed Successfully for node -- {node_address}.")
        else:
            catch_error.append(error)
            logging.info(f"{node_address} : SDS Node Setup Completed with error.")

    if(catch_error!=[]):
        logging.info("All SDS Nodes configutration completed with some errors.")
        return {"Mesage ":catch_error}
    else:
        logging.info("All SDS Nodes configured successfully.")
        return {"Mesage ":"success"}

#Main Function for BareMetal and ESXi SDS Server Setup.
def main():
    logging.debug(f"\n\nWelcome to Ucptoolkit SDS configuration Setup Menu.")
    while True:
        logging.info(f"\n\nPlease select the appropriate option from the menu below as per your requirement...\n")
        for key,value in vssb_setup_conif.items():
            print(str(key)+":"+value)
        selected_option = input('\nPlease select your option now... : ')

        if(selected_option not in vssb_setup_conif):
            logging.info(f"Option enter is INVALID!. Please enter the correct option.")

        elif(selected_option == '2'):
            logging.info(f"Perfect! you have selected option-  {selected_option}: { vssb_setup_conif[selected_option]}")
            input("\nHit Enter to continue...")
            sds_return = SDS_ESXiSetup()
            break

        elif(selected_option=='1'):
            logging.info(f"Perfect! you have selected option-  {selected_option}: { vssb_setup_conif[selected_option]}")
            input("\nHit Enter to continue...")
            read_baremetalserver_csv(executable_path+"\\config\\SDS_BaremetalserverDetails.csv",executable_path)
            break

main()


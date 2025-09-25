import os
import subprocess
import csv
import time
from ha_ilorestapis import HA_operations


# Set the executable path
executable_path = os.getcwd() +"//HA8XX_scripts"
#print(executable_path)
os.chdir(executable_path)
# Add the executable path to the PATH environment variable
os.environ['PATH'] += os.pathsep + executable_path
# Starting Web Server





print("### Starting Web Server on IPv6 http port 8081###")
subprocess.call('start /b nginx', shell=True)


# Variables
servers = []
print("Reading servers from server.csv file ")
with open('servers.csv', 'r') as file:
    reader = csv.DictReader(file, delimiter=',',fieldnames=[
                                'ipaddress', 'username', 'password','model'], skipinitialspace=True)
    next(reader)
    for row in reader:
        servers.append(row)


def applyBiosTemplate(selected_option):
    while True:
        Bios_Template_uRL = {}
        if(selected_option == 1):
            print("Applying Default Bios Template for HA nodes...")
            URL = input("Please navigate to http://[IPv6]:8081 of this jumphost in a browser and provide BIOS, template for Regular HA Servers: ")
            Bios_Template_uRL.append(URL)   
        elif(selected_option == str(10)):
            print("\n Provide below URLS to configure VSSB servers...")
            vssb_iso_url_G2 = input("Please navigate to http://[IPv6]:8081 of this jumphost in a browser and provide SDS SPV iso URL:")
            #vssb_iso_url_G3 = input("Please navigate to http://[IPv6]:8081 of this jumphost in a browser and provide SDS SPV iso URL:")
            kickstart_suse_url = input("Please navigate to http://[IPv6]:8081 of this jumphost in a browser and provide kickstart OS iso URL:")
            #Bios_Template_uRL["URL1"] = URL1
            #Bios_Template_uRL["URL2"] = URL2
            Bios_Template_uRL["VSSB_iso_url_G2"] = vssb_iso_url_G2
            #Bios_Template_uRL["VSSB_iso_url_G3"] = vssb_iso_url_G3
            Bios_Template_uRL["kickstart_suse_url"] = kickstart_suse_url
            break
    return Bios_Template_uRL


def setupUrls(selected_option):
    # Reading URLs
    print("Please navigate to http://[IPv6]:8081 of this jumphost in a browser for the URL for the following ISOs")
    spvurl_HAG2Node = input("Enter SPV Image URL for HA G2 nodes : ")
    spvurl_HAG3Node = input("Enter SPV Image URL for HA G3 nodes : ")
    if('9' in selected_option):
        
        kickstarturl = input("Enter Azure Stack HCI ISO image url : ")
        print("Applying BIOS Template before mounting SPV iso and Kickstart ESXi ISO : ")
        for server in servers:
            print(server)
            model = server['model']
            ipaddress = server['ipaddress']
            username = server['username']
            password = server['password']
            haapi_obj = HA_operations(ipaddress,username,password,model,"/redfish/v1/systems/1/bios/settings")
            print("Making API call to update the Product ID for HA AHCI nodes.")
            haapi_obj.createSession("/redfish/v1/systems/1/bios/settings")
            subprocess.call(f'ilorest\\ilorest login {ipaddress} -u {username} -p {password}', shell=True)
            
            executable_path = os.getcwd()
            print(f"Path : {executable_path}")
            executable_path = executable_path+"//HA-G2-G3BiosTemplates//"

            command = 'ilorest\\ilorest load -f '+executable_path+'HA_G2_ASHCI.bios.json'
            if model == "Hitachi Advanced Server HA805 G3" or model == "Hitachi Advanced Server HA815 G3" or model == "Hitachi Advanced Server HA825 G3":
                command = 'ilorest\\ilorest load -f'+executable_path+ 'HA_G3_ASHCI_AMD_HA805_HA815_825_G3.json'
            elif model == "Hitachi Advanced Server HA810 G3" or model == "Hitachi Advanced Server HA820 G3":
                command = 'ilorest\\ilorest load -f'+executable_path+ 'HA_G3_ASHCI.bios.json'
            elif model == "Hitachi Advanced Server HA840 G3":
                command = 'ilorest\\ilorest load -f'+executable_path+ 'HA_G3_ASHCI.bios.json'

            print(f"\n Applying BIOS Template for : {model}")
            print(f"Executing >>>> {command}")
            subprocess.call(command, shell=True)
            countdown(5)
            reset_cmd = "ilorest\\ilorest reboot"
            print("Reebooting server...")
            subprocess.call(reset_cmd, shell=True)


    elif('1' in selected_option):
        kickstarturl = input("Enter ESXi 8.0 ISO Image URL : ")
        print("Applying BIOS Template before mounting SPV iso and Kickstart ESXi ISO : ")

        for server in servers:
            print(server)
            model = server['model']
            ipaddress = server['ipaddress']
            username = server['username']
            password = server['password']
            subprocess.call(f'ilorest\\ilorest login {ipaddress} -u {username} -p {password}', shell=True)
            
            executable_path = os.getcwd()
            print(f"Path : {executable_path}")
            executable_path = executable_path+"//HA-G2-G3BiosTemplates//"

            command = 'ilorest\\ilorest load -f '+executable_path+'HA_G2_Intel_HA810_HA820_G2.json'
            if model == "Hitachi Advanced Server HA805 G3" or model == "Hitachi Advanced Server HA815 G3" or model == "Hitachi Advanced Server HA825 G3":
                command = 'ilorest\\ilorest load -f'+executable_path+ 'HA_G3_AMD_HA805_HA815_825_G3.json'
            elif model == "Hitachi Advanced Server HA810 G3" or model == "Hitachi Advanced Server HA820 G3":
                command = 'ilorest\\ilorest load -f '+executable_path+'HA_G3_Intel_HA810_HA820_G3.json'
            elif model == "Hitachi Advanced Server HA840 G3":
                command = 'ilorest\\ilorest load -f '+executable_path+'HA_G3_HA840_G3.json'

            print(f"\n Applying BIOS Template for : {model}")
            print(f"Executing >>>> {command}")
            subprocess.call(command, shell=True)
            countdown(5)
        
    return spvurl_HAG2Node, spvurl_HAG3Node, kickstarturl

# Countdown Timer Function
def countdown(seconds):
    for i in range(seconds):
        percent = (i+1) * 100 // seconds
        print(f'{seconds-i} seconds remaining...', end='\r')
        time.sleep(1)
    print()

# Command Execution Loop
def loop(commands, spvurl_HAG2Node, spvurl_HAG3Node):
    for server in servers:
        print(server)
        model = server['model']
        ipaddress = server['ipaddress']
        username = server['username']
        password = server['password']
        subprocess.call(f'ilorest\\ilorest login {ipaddress} -u {username} -p {password}', shell=True)

        if(spvurl_HAG2Node=="10"):
            print("This is a VSSB server setup.")
            ilo_rest_template = commands[0].split(os.path.sep)[-1]
            if("G2" in model and ilo_rest_template == "step1_ilorest.json"):
                print(f"Applying G2 Step1 Bios Template for SDS server setup : {ilo_rest_template}")
                print("Applying VSSB iso for G2 server.")
            elif("G2" in model and ilo_rest_template == "step2_ilorest.json"):
                print(f"Applying G2 Step2 Bios Template for SDS server setup : {ilo_rest_template} and deleting existing Raid.")
            elif("G3" in model):
                # Update the command for G3 servers
                print(f"Applying G3  Bios Template for SDS server setup : ilorest-G3.json")
                commands[0] = f'ilorest\\ilorest load -f {executable_path}\\AutoHotkey\\SDS-BiosTemplates\\ilorest-G3.json'

            updated_commands = commands
            
        elif(spvurl_HAG2Node == "Bios_Apply"):
            #print("Applying Bios Templates for HA servers...")
            updated_commands = commands
            

        else:
            print("\nHA server Setup..")
            print("Checking server type G2 or G3 from server.csv for node... ")
            if('G2' in model):
                spvurl_updated = spvurl_HAG2Node
                #print("Found G2 node, passing G2 spv iso image :  "+spvurl_updated)
            elif('G3' in model):
                spvurl_updated = spvurl_HAG3Node
                #print("Found G3 node, passing G3 spv iso image :  "+spvurl_updated)
            else:
                # Handle other server types here, if necessary
                print("Unknown server type, skipping... ")
                continue
            # Update the command with the correct SPV URL
            updated_commands = [s.replace("NA", spvurl_updated) for s in commands]


        for cmd in updated_commands:
            print(f"command is >>>> {cmd}")
            subprocess.call(cmd, shell=True)
            time.sleep(10)


def execute_command_with_error_handling(cmd, server_ip, step_description="", allow_failure=False):
    """Execute a command with proper error handling and return status and output"""
    try:
        print(f"Executing: {cmd} on server {server_ip}")
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output = result.stdout + result.stderr
        
        # Always show the command output for debugging
        print(f"Command output:\n{output}")
        
        if result.returncode != 0:
            if allow_failure:
                print(f"WARNING: Command failed with return code {result.returncode} (but continuing as failure is allowed)")
                print(f"Command: {cmd}")
                return True, output  # Treat as success even though it failed
            else:
                print(f"ERROR: Command failed with return code {result.returncode}")
                print(f"Command: {cmd}")
                return False, output
        else:
            print(f"SUCCESS: {step_description}")
            return True, output
    except Exception as e:
        print(f"EXCEPTION: Error executing command '{cmd}' on server {server_ip}: {e}")
        return False, str(e)


def check_ilo_version_for_server(server_ip, username, password):
    """Check iLO version for a specific server"""
    try:
        # Login to the server
        login_cmd = f'ilorest\\ilorest login {server_ip} -u {username} -p {password}'
        success, output = execute_command_with_error_handling(login_cmd, server_ip, "Login to iLO")
        if not success:
            return None, f"Failed to login to server {server_ip}"
        
        # Check iLO version
        version_cmd = f'ilorest\\ilorest rawget /redfish/v1/Managers/1 | findstr /i "Model"'
        success, output = execute_command_with_error_handling(version_cmd, server_ip, "Check iLO version")
        if not success:
            return None, f"Failed to check iLO version for server {server_ip}"
        
        if "iLO 6" in output:
            return 6, output
        elif "iLO 5" in output:
            return 5, output
        else:
            return None, f"Unknown iLO version for server {server_ip}: {output}"
            
    except Exception as e:
        return None, f"Exception checking iLO version for server {server_ip}: {e}"


def main(selected_option):
    #Main function which calls respective scripts from different sollutions.
    #Main function which calls respective scripts from different sollutions.
    if(selected_option == '10' ):
        print("SDS Servers Setup Selected...")
        BIOS_Url = applyBiosTemplate(selected_option)
        #url1 = BIOS_Url.get("URL1")
        #url2 = BIOS_Url.get("URL2")
        vssb_iso_G2 = BIOS_Url.get("VSSB_iso_url_G2")
        #vssb_iso_G3= BIOS_Url.get("VSSB_iso_url_G3")
        kickstart_suse_url = BIOS_Url.get("kickstart_suse_url")
        
        if not vssb_iso_G2 or not kickstart_suse_url:
            print("ERROR: Missing required URLs. Please provide both SDS SPV iso URL and kickstart OS iso URL.")
            return
            
        print(f"\nTotal servers: \n{servers}")
        successful_servers = []
        failed_servers = []
        
        for server in servers:
            server_success = False
            try: 
                model = server['model']
                ipaddress = server['ipaddress']
                username = server['username']
                password = server['password']
                print(f"\n{'='*80}")
                print(f"Starting SDS configuration on server: {ipaddress} ({model})")
                print(f"{'='*80}")
                
                # Check iLO version for this specific server
                ilo_version, ilo_output = check_ilo_version_for_server(ipaddress, username, password)
                if ilo_version is None:
                    print(f"ERROR: {ilo_output}")
                    failed_servers.append({"server": ipaddress, "error": ilo_output})
                    continue
                    
                print(f"Detected iLO version: {ilo_version} for server {ipaddress}")
                
                if ilo_version != 6:
                    error_msg = f"Server {ipaddress} has iLO version {ilo_version}. This script only supports iLO 6 for option 10."
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                print(f"Setting up controller and bios for iLO 6: {ipaddress}")
                
                # Step 1: Apply BIOS template and mount SPV (SKIPPED FOR TESTING)
                print("### SKIPPING STEP 1 FOR TESTING ###")
                print("Step 1 (Apply BIOS template and mount SPV) is being skipped.")
                print("Proceeding directly to Step 2...")
                
                # Uncomment the following block to re-enable Step 1:
                """
                step1_commands = [
                    f'ilorest\\ilorest load -f {executable_path}\\AutoHotkey\\SDS-BiosTemplates\\step1_ilorest.json',
                    'ilorest\\ilorest virtualmedia 2 --remove',
                    f'ilorest\\ilorest virtualmedia 2 {vssb_iso_G2} --bootnextreset',
                    'ilorest\\ilorest reboot'
                ]
                
                all_step1_success = True
                for cmd in step1_commands:
                    success, output = execute_command_with_error_handling(cmd, ipaddress, f"Step 1 - {cmd.split()[-1] if len(cmd.split()) > 1 else 'Command'}")
                    if not success:
                        all_step1_success = False
                        break
                
                if not all_step1_success:
                    error_msg = f"Step 1 failed for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                print("### Sleeping for 60 minutes to apply SPV ###")
                print("Please hit enter to continue after SPV is applied...")
                input()  # Wait for user confirmation instead of automatic timeout
                """
                
                # Step 2: Apply step2 BIOS template (SKIPPED FOR TESTING)
                print("### SKIPPING STEP 2 FOR TESTING ###")
                print("Step 2 (Apply step2 BIOS template) is being skipped.")
                print("Proceeding directly to Step 3...")
                
                # Uncomment the following block to re-enable Step 2:
                """
                cmd = f"ilorest\\ilorest load -f {executable_path}\\AutoHotkey\\SDS-BiosTemplates\\step2_ilorest.json"
                success, output = execute_command_with_error_handling(cmd, ipaddress, "Step 2 - Apply step2 BIOS template")
                if not success:
                    error_msg = f"Step 2 BIOS template failed for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                print("### Sleeping for 5 minutes after factory reset ###")
                # countdown(3)  # Uncomment if you want automatic delay
                """
                
                # Step 3: List controllers and find MR216i-p
                print(f"Step 3 - Listing controllers: {ipaddress}")
                cmd = "ilorest\\ilorest storagecontroller default"
                success, controllers_output = execute_command_with_error_handling(cmd, ipaddress, "List storage controllers")
                if not success:
                    error_msg = f"Failed to list controllers for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                controller_id = None
                for line in controllers_output.split("\n"):
                    if "MR216i-p" in line:
                        try:
                            controller_id = line.split(":")[0].strip()
                            break
                        except:
                            continue
                
                if not controller_id:
                    error_msg = f"MR216i-p controller not found for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                print(f"Found controller ID for MR216i-p: {controller_id} on server {ipaddress}")
                
                # Step 4: Factory reset controller
                print(f"Step 4 - Factory resetting controller: {controller_id} on {ipaddress}")
                cmd = f"ilorest\\ilorest factoryresetcontroller --storageid {controller_id} --reset_type preservevolumes"
                success, reset_output = execute_command_with_error_handling(cmd, ipaddress, "Factory reset controller")
                if not success:
                    error_msg = f"Factory reset controller failed for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                # Step 5: List controller volumes
                print(f"Step 5 - List controller volumes: {ipaddress}")
                cmd = f'ilorest\\ilorest storagecontroller --storageid={controller_id} --controller=0 --volumes'
                success, volumes_output = execute_command_with_error_handling(cmd, ipaddress, "List controller volumes")
                if not success:
                    error_msg = f"Failed to list controller volumes for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                # Step 6: Extract and delete volume if exists
                volume_id = None
                for line in volumes_output.splitlines():
                    line = line.strip()
                    if line.startswith("[") and "]" in line:
                        try:
                            volume_id = line.split("]")[0].strip("[")
                            break
                        except Exception as e:
                            print(f"Error parsing volume ID: {e}")
                
                if volume_id:
                    print(f"Step 6 - Delete volume: {volume_id} on {ipaddress}")
                    cmd = f'ilorest\\ilorest deletevolume --storageid={controller_id} --controller=0 {volume_id} --force'
                    success, delete_output = execute_command_with_error_handling(cmd, ipaddress, f"Delete volume {volume_id}")
                    if not success:
                        error_msg = f"Failed to delete volume {volume_id} for server {ipaddress}"
                        print(f"ERROR: {error_msg}")
                        failed_servers.append({"server": ipaddress, "error": error_msg})
                        continue
                else:
                    print("No volume ID found to delete.")
                
                # Step 7: List physical drives and create RAID1
                print(f"Step 7 - List physical drives: {ipaddress}")
                cmd = f'ilorest\\ilorest storagecontroller --storageid={controller_id} --controller=0 --physicaldrives'
                success, drives_output = execute_command_with_error_handling(cmd, ipaddress, "List physical drives")
                if not success:
                    error_msg = f"Failed to list physical drives for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue

                # Parse drive locations
                drive_locations = []
                for line in drives_output.splitlines():
                    if "[" in line and "]" in line:
                        try:
                            part = line.split("]")[0].strip()
                            location = part.strip("[").strip()
                            drive_locations.append(location)
                        except:
                            continue

                if len(drive_locations) >= 2:
                    drives_str = f"{drive_locations[0]},{drive_locations[1]}"
                    cmd = (
                        f'ilorest\\ilorest createvolume volume RAID1 {drives_str} '
                        f'--DisplayName Name1 --iOPerfModeEnabled False '
                        f'--ReadCachePolicy ReadAhead --WriteHoleProtectionPolicy Yes '
                        f'--controller=0 --storageid={controller_id}'
                    )
                    
                    print(f"Step 8 - Creating RAID1 volume with drives: {drives_str} on {ipaddress}")
                    success, create_output = execute_command_with_error_handling(cmd, ipaddress, "Create RAID1 volume")
                    if not success:
                        error_msg = f"Failed to create RAID1 volume for server {ipaddress}"
                        print(f"ERROR: {error_msg}")
                        failed_servers.append({"server": ipaddress, "error": error_msg})
                        continue
                    
                    if "Volume created successfully" in create_output:
                        print(f"RAID1 volume created successfully for {ipaddress}")
                    else:
                        print(f"Warning: Volume creation may have failed. Response: {create_output}")
                else:
                    error_msg = f"Not enough drives ({len(drive_locations)}) to create RAID1 volume for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue

                # Step 9: Mount SDS ISO and reboot
                print(f"Step 9 - Mounting SDS ISO: {ipaddress}")
                
                # First, try to remove any existing virtual media (allow failure since media may not be present)
                print("Step 9a - Removing any existing virtual media (if present)...")
                success, output = execute_command_with_error_handling(
                    "ilorest\\ilorest virtualmedia 2 --remove", 
                    ipaddress, 
                    "Remove existing virtual media",
                    allow_failure=True  # Allow this to fail if no media is present
                )
                
                # Mount the new ISO with boot next reset
                print("Step 9b - Mounting SDS ISO with boot next reset...")
                success, output = execute_command_with_error_handling(
                    f"ilorest\\ilorest virtualmedia 2 {kickstart_suse_url} --bootnextreset",
                    ipaddress, 
                    "Mount SDS ISO with boot next reset"
                )
                if not success:
                    error_msg = f"Failed to mount SDS ISO for server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                # Set one-time boot order to CD/DVD first
                print("Step 9c - Setting one-time boot source to CD/DVD...")
                success, output = execute_command_with_error_handling(
                    "ilorest\\ilorest bootorder --onetimeboot=Cd --commit",
                    ipaddress, 
                    "Set one-time boot order to CD/DVD",
                    allow_failure=True  # Allow this to fail and try alternative method
                )
                
                # Alternative method: Use rawpatch to set boot source override
                if not success:
                    print("Step 9c-alt - Using alternative method to set boot source override...")
                    success, output = execute_command_with_error_handling(
                        'ilorest\\ilorest rawpatch /redfish/v1/Systems/1/ "{\\"Boot\\": {\\"BootSourceOverrideTarget\\": \\"Cd\\", \\"BootSourceOverrideEnabled\\": \\"Once\\"}}"',
                        ipaddress, 
                        "Set boot source override via raw PATCH",
                        allow_failure=True  # Allow this to fail too
                    )
                
                # If both methods fail, try setting boot order permanently
                if not success:
                    print("Step 9c-alt2 - Setting continuous boot to CD/DVD as fallback...")
                    success, output = execute_command_with_error_handling(
                        "ilorest\\ilorest bootorder --continuousboot=Cd --commit",
                        ipaddress, 
                        "Set continuous boot to CD/DVD",
                        allow_failure=True  # Allow this to fail as well
                    )
                
                # Remove the old step 9d as it's been replaced
                # Alternative: Set temporary boot order if one-time boot fails
                # print("Step 9d - Setting temporary boot source to CD/DVD...")
                # success, output = execute_command_with_error_handling(
                #     "ilorest\\ilorest bootorder --commit --bootsourceoverride=Cd",
                #     ipaddress, 
                #     "Set temporary boot source to CD/DVD",
                #     allow_failure=True  # Allow this to fail as it's an alternative method
                # )
                
                # Force power off first to ensure clean boot
                print("Step 9d - Force power off server...")
                success, output = execute_command_with_error_handling(
                    "ilorest\\ilorest reboot ForceOff",
                    ipaddress, 
                    "Force power off server"
                )
                if not success:
                    error_msg = f"Failed to power off server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                # Wait a moment for power off to complete
                print("Waiting 10 seconds for power off to complete...")
                time.sleep(10)
                
                # Power on the server
                print("Step 9e - Powering on server...")
                success, output = execute_command_with_error_handling(
                    "ilorest\\ilorest reboot On",
                    ipaddress, 
                    "Power on server"
                )
                if not success:
                    error_msg = f"Failed to power on server {ipaddress}"
                    print(f"ERROR: {error_msg}")
                    failed_servers.append({"server": ipaddress, "error": error_msg})
                    continue
                
                # Logout (allow failure since session might timeout)
                print("Step 9f - Logging out...")
                success, output = execute_command_with_error_handling(
                    "ilorest\\ilorest logout",
                    ipaddress, 
                    "Logout from iLO",
                    allow_failure=True  # Allow logout to fail
                )

                # If we reach here, the server was configured successfully
                print(f"SUCCESS: Server {ipaddress} configuration completed successfully!")
                successful_servers.append(ipaddress)
                server_success = True

                print(f"Waiting for user confirmation before proceeding to next server...")
                input("Press Enter to continue to next server...")
                time.sleep(5)
                
            except Exception as e:
                error_msg = f"Unexpected error configuring server {ipaddress}: {e}"
                print(f"CRITICAL ERROR: {error_msg}")
                failed_servers.append({"server": ipaddress, "error": error_msg})

        # Print summary
        print(f"\n{'='*80}")
        print("SDS SERVER CONFIGURATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total servers processed: {len(servers)}")
        print(f"Successful servers: {len(successful_servers)}")
        print(f"Failed servers: {len(failed_servers)}")
        
        if successful_servers:
            print(f"\nSuccessful servers:")
            for server in successful_servers:
                print(f"  ✓ {server}")
        
        if failed_servers:
            print(f"\nFailed servers:")
            for failure in failed_servers:
                print(f"  ✗ {failure['server']}: {failure['error']}")
        
        print("\nScript completed.")
        return

        
    elif(selected_option!='10'):
        print(selected_option)
        spvurl_HAG2Node, spvurl_HAG3Node, kickstarturl =  setupUrls(selected_option)
        print(f"Urls : \n Spv G2: {spvurl_HAG2Node} \n Spv G3: {spvurl_HAG3Node} \n KisckStart Image: {kickstarturl}")

        # Create new user account (admin/cmb9.admin)
        # loop(['ilorest\\ilorest iloaccounts add admin admin PASSWORD cmb9.admin --role=Administrator'])

        # Flash custom BIOS and ILO binaries
        # loop(['ilorest\\ilorest firmwareupdate ' + biosurl])
        # print("###Waiting 1 minute for all servers to boot ILO###")
        # countdown(60)
        # loop(['ilorest\\ilorest firmwareupdate ' + ilourl])
        # print("###Waiting 2 minutes for all servers to boot ILO###")
        # countdown(120)

        # Power off all servers to force new BIOS and ILO to be loaded with POST process
        # loop(['ilorest\\ilorest reboot ForceOff'])
        # print("###Sleeping for 10 seconds###")
        # countdown(10)

        # Power on all servers
        # loop(['ilorest\\ilorest reboot on'])
        # print("###Sleeping for 5 minutes to wait for servers to power on###")
        # countdown(300)

        # Apply BIOS settings to all host and reboot with SPV
        #loop(['ilorest\\ilorest virtualmedia 2 --remove', f'ilorest\\ilorest virtualmedia 2 {spvurl} --bootnextreset', 'ilorest\\ilorest reboot'])
        # Apply BIOS settings to all host and reboot with SPV

        spvurl = "NA"
        #loop(['ilorest\\ilorest virtualmedia 2 --remove', f'ilorest\\ilorest virtualmedia 2 '+spvurl+' --bootnextreset', 'ilorest\\ilorest reboot on'], spvurl_HAG2Node, spvurl_HAG3Node)
        if(spvurl_HAG2Node or spvurl_HAG3Node):
            loop(['ilorest\\ilorest virtualmedia 2 --remove', f'ilorest\\ilorest reboot ForceOff', f'ilorest\\ilorest virtualmedia 2 '+spvurl+' --bootnextreset', 'ilorest\\ilorest reboot on'], spvurl_HAG2Node, spvurl_HAG3Node)

            print("###Sleeping for 60 minutes to apply SPV###")
            countdown(3600)
        else:
            print("spvurl_HAG2Node and spvurl_HAG3Node URLS not provided, thus skiping SPV FLashing.")


        if(kickstarturl):
            # Reboot with kickstart image
            #loop(['ilorest\\ilorest load -f ilorest.json', 'ilorest\\ilorest virtualmedia 2 --remove',  f'ilorest\\ilorest virtualmedia 2 {kickstarturl} --bootnextreset' ])
            loop(['ilorest\\ilorest virtualmedia 2 --remove', f'ilorest\\ilorest reboot ForceOff', f'ilorest\\ilorest virtualmedia 2 {kickstarturl} --bootnextreset','ilorest\\ilorest reboot on' ], spvurl_HAG2Node, spvurl_HAG3Node)
            print("###Sleeping for 40 minutes before shutting down web server###")
            countdown(2400)
        else:
            print("ESXi Image Url Not provided, thus skiping ESXi Installation.")

    # Shutting down Web Server
    subprocess.call('taskkill /f /im nginx.exe', shell=True)
    print("###Complete!!###")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        selected_option = sys.argv[1]
    else:
        selected_option = input("Enter option (10 for SDS servers, other for HA servers): ")
    main(selected_option)

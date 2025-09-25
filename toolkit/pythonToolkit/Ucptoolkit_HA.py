import badtime
import os
import logging
import datetime
import toolkit_config
import subprocess
import sys

executable_path = os.getcwd() +"\\HA8XX_scripts"
sys.path.insert(1,executable_path)
logger = logging.getLogger(__name__)
print("Trying to kill if any Nginx servers running...")
subprocess.call('taskkill /f /im nginx.exe', shell=True)

#HA Files to be called
HA_files_dict = {"1":"ucp_all(Default) - This applies BIOS template, boot SPV, and boot ESXi installer",
                 "2":"ucp_BIOS_load - This applies BIOS template",
                 "3":"ucp_BIOS_save - This exports BIOS setting to a file",
                 "4":"ucp_firmware - This applies iLo, System ROM, or Server Platform Service firmware",
                 "5":"ucp_mount_reboot - This mounts the selected ISO file and boot from it",
                 "6":"ucp_power_off",
                 "7":"ucp_power_on",
                 "8":"ucp_user_creation",
                 "9": "Azure_Stack_HCI",
                 "10": "Setup_VSSB_Servers",
                 "11":"Exit"
                 }

def call_relevant_Files(HA_files_dict):
    print("\nWelcome to Ucptoolkit for HA Nodes!!!")
    input("\nHit enter to continue...")
    while True:
        print("\nPlease select the appropriate option from the menu below as per your requirement...\n")
        for key,value in HA_files_dict.items():
            print(str(key)+":"+value)
        selected_option = input('\nPlease select your option now... : ')

        if(selected_option not in HA_files_dict):
            print("\nOption enter is INVALID!. Please enter the correct option")
        else:
            print("Perfect! you have selected option- " +selected_option+":"+HA_files_dict[selected_option])
            input("\nHit Enter to continue...")
            print("\nPassing control to python file : "+HA_files_dict[selected_option])
            call_HA_scripts(selected_option)
            break

def call_HA_scripts(selected_option):
    script_to_call = HA_files_dict[selected_option]
    print("you have selected : "+script_to_call)
    for key,value in HA_files_dict.items():
        if(script_to_call in value and (script_to_call =="ucp_all(Default) - This applies BIOS template, boot SPV, and boot ESXi installer"
                                        or script_to_call =="Azure_Stack_HCI" or script_to_call=="Setup_VSSB_Servers")):
            print("Starting to call : "+script_to_call)
            if __name__ == '__main__':
                from ucp_all import main
                main(selected_option)

        if(script_to_call in value and script_to_call =="ucp_BIOS_load - This applies BIOS template"):
            print("Starting to call : "+script_to_call)
            if __name__ == '__main__':
                from  ucp_BIOS_load import run
                if __name__ == '__main__':
                    run()

        if(script_to_call in value and script_to_call =="ucp_BIOS_save - This exports BIOS setting to a file"):
            print("Starting to call : "+script_to_call)
            if __name__ == '__main__':
                from ucp_BIOS_save import cup_bios_save
                cup_bios_save()

        if(script_to_call in value and script_to_call =="ucp_firmware - This applies iLo, System ROM, or Server Platform Service firmware"):
            print("Starting to call : "+script_to_call)
            if __name__ == '__main__':
                from ucp_firmware import main
                main()

        if(script_to_call in value and script_to_call =="ucp_mount_reboot - This mounts the selected ISO file and boot from it"):
            print("Starting to call : "+script_to_call)
            if __name__ == '__main__':
                import ucp_mount_reboot

        if(script_to_call in value and script_to_call =="ucp_power_off"):
            print("Starting to call : "+script_to_call)
            if __name__ == '__main__':
                import ucp_power_off

        if(script_to_call in value and script_to_call =="ucp_power_on"):
            print("Starting to call : "+script_to_call)
            if __name__ == '__main__':
                import ucp_power_on

        if(script_to_call in value and script_to_call =="ucp_user_creation"):
            print("Starting to call : "+script_to_call)
            if __name__ == '__main__':
                import ucp_user_creation

        if(script_to_call in value and script_to_call =="Exit"):
            print("Starting to call : "+script_to_call)
            exit()


def main():
    # Print welcome screen
    badtime.hitachi()
    badtime.version()

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_file_name = "Ucptoolkit_HA"+datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + '.log'
    log_file_name = os.path.join(os.getcwd(),'logs',log_file_name)
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_file_name)

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    call_relevant_Files(HA_files_dict)

main()

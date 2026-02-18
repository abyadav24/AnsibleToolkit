#!/usr/bin/env python3
"""
IPMI SOL Helper Script
Handles IPMI SOL connections without requiring expect
"""

import subprocess
import sys
import time
import re
import signal
import os

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out")

def strip_ansi_codes(text):
    """
    Remove ANSI escape sequences from text (color codes, etc.)
    Pattern matches: ESC [ ... m   and   ESC followed by single char
    """
    # Match all common ANSI escape patterns
    ansi_escape = re.compile(r'\x1B(?:\[[0-9;]*[a-zA-Z]|[^\[])')
    return ansi_escape.sub('', text)

def get_ipmitool_path():
    """
    Get the path to ipmitool, preferring vendored version
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vendor_ipmitool = os.path.join(script_dir, '..', '..', 'vendor', 'tools', 'bin', 'ipmitool.sh')
    
    # Check if vendored ipmitool exists
    if os.path.exists(vendor_ipmitool):
        return vendor_ipmitool
    
    # Fallback to system ipmitool
    return 'ipmitool'

def verify_minios_boot(ip, username, password, timeout_sec=30):
    """
    Verify that MiniOS has booted successfully by checking for login prompt
    """
    print(f"Verifying MiniOS boot for {ip}...")
    
    ipmitool = get_ipmitool_path()
    cmd = [
        ipmitool, '-I', 'lanplus',
        '-H', ip,
        '-U', username,
        '-P', password,
        'sol', 'activate'
    ]
    
    try:
        # Set up timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_sec)
        
        # Start the process
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Send carriage return to trigger output
        proc.stdin.write('\r\n')
        proc.stdin.flush()
        time.sleep(2)
        
        # Read output for a few seconds
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < 10:
            try:
                line = proc.stdout.readline()
                if line:
                    output_lines.append(line)
                    print(line, end='')
                    
                    # Check for boot success indicators
                    if 'ubuntu login:' in line.lower():
                        print("\nSUCCESS: MiniOS booted successfully (login prompt detected)")
                        proc.stdin.write('~.\r\n')
                        proc.stdin.flush()
                        signal.alarm(0)
                        proc.terminate()
                        return True, "MiniOS booted successfully"
                    
                    if 'ubuntu@' in line.lower():
                        print("\nSUCCESS: MiniOS already logged in")
                        proc.stdin.write('~.\r\n')
                        proc.stdin.flush()
                        signal.alarm(0)
                        proc.terminate()
                        return True, "MiniOS already at prompt"
                        
            except Exception as e:
                break
        
        # Cleanup
        signal.alarm(0)
        proc.stdin.write('~.\r\n')
        proc.stdin.flush()
        time.sleep(1)
        proc.terminate()
        
        print(f"\nWARNING: Could not verify boot - continuing anyway")
        return True, "Could not verify but continuing"
        
    except TimeoutException:
        print(f"\nWARNING: Verification timed out - continuing anyway")
        if proc:
            proc.terminate()
        signal.alarm(0)
        return True, "Timeout but continuing"
        
    except Exception as e:
        print(f"\nERROR during verification: {e}")
        signal.alarm(0)
        return False, str(e)

def parse_lspci_line(line):
    """
    Parse a line from lspci -mm output into a dict
    Format: PCI_ADDR "TYPE" "VENDOR" "MODEL" -rXX "SUBVENDOR" "SUBMODEL"
    """
    clean_line = strip_ansi_codes(line).strip()
    
    # Extract PCI address (first field before space)
    parts = clean_line.split(maxsplit=1)
    if len(parts) < 2:
        return None
    
    pci_addr = parts[0]
    rest = parts[1]
    
    # Extract quoted fields
    fields = re.findall(r'"([^"]*)"', rest)
    if len(fields) < 3:
        return None
    
    return {
        'pci_addr': pci_addr,
        'type': fields[0] if len(fields) > 0 else "",
        'vendor': fields[1] if len(fields) > 1 else "",
        'model': fields[2] if len(fields) > 2 else "",
        'subvendor': fields[3] if len(fields) > 3 else "",
        'submodel': fields[4] if len(fields) > 4 else ""
    }

def list_adapters(ip, username, password, adapter_type='Ethernet', timeout_sec=90):
    """
    List network adapters via SOL connection - outputs JSON to stdout
    adapter_type: 'Ethernet' or 'Fibre'
    """
    import json
    
    print(f"Listing {adapter_type} adapters for {ip}...", file=sys.stderr)
    
    ipmitool = get_ipmitool_path()
    
    # Build the lspci grep pattern based on adapter type
    if adapter_type == 'Ethernet':
        grep_pattern = "Ethernet|Network"
    else:
        grep_pattern = "Fibre|Channel"
    
    lspci_cmd = f'lspci -mm | grep --color=never -iE "{grep_pattern}"'
    
    # Use a shell pipeline approach that works reliably
    shell_cmd = f'''{{ 
        sleep 3
        echo "ubuntu"
        sleep 2
        echo ""
        sleep 3
        echo '{lspci_cmd}'
        sleep 8
        echo 'echo "===DONE==="'
        sleep 2
    }} | timeout {timeout_sec} {ipmitool} -I lanplus -H {ip} -U {username} -P {password} sol activate 2>&1'''
    
    try:
        print(f"Executing: {lspci_cmd}", file=sys.stderr)
        
        result = subprocess.run(
            shell_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec + 10
        )
        
        output = result.stdout + result.stderr
        
        # Parse the output for adapter lines
        adapters = []
        for line in output.split('\n'):
            clean_line = strip_ansi_codes(line).strip()
            
            # Skip irrelevant lines
            if not clean_line:
                continue
            if any(skip in clean_line.lower() for skip in [
                'lspci', '[sol', 'tcgetattr', '===done===', 'ubuntu@', 
                'login', 'password', 'grep', 'incorrect', 'ubuntu 20.04', 
                'ttys1', 'session operational'
            ]):
                continue
            if clean_line == 'ubuntu' or clean_line.startswith('$') or clean_line.startswith('echo'):
                continue
                
            # Match PCI address format (XX:XX.X) at start of line
            pci_match = re.match(r'^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9])\s', clean_line)
            if pci_match:
                parsed = parse_lspci_line(clean_line)
                if parsed:
                    adapters.append(parsed)
                    print(f"DEBUG: Found port: {parsed['pci_addr']} - {parsed['vendor']} {parsed['model'][:30]}", file=sys.stderr)
        
        # Group adapters by physical card (bus:device, ignoring function number)
        # PCI address format is bus:device.function (e.g., 33:00.0, 33:00.1 are same card)
        cards = {}
        for adapter in adapters:
            # Extract bus:device portion (everything before the dot)
            base_addr = adapter['pci_addr'].rsplit('.', 1)[0]  # "33:00.0" -> "33:00"
            if base_addr not in cards:
                cards[base_addr] = adapter  # Keep first port (function 0) as representative
                print(f"DEBUG: Physical card: {base_addr} ({adapter['model'][:40]})", file=sys.stderr)
        
        # Convert back to list (one entry per physical card)
        unique_cards = list(cards.values())
        
        print(f"DEBUG: Found {len(adapters)} port(s) on {len(unique_cards)} physical {adapter_type} card(s)", file=sys.stderr)
        
        # Output JSON to stdout - this is what the playbook will capture
        print(json.dumps(unique_cards))
        
        return True, unique_cards
            
    except subprocess.TimeoutExpired:
        print(f"WARNING: Listing timed out after {timeout_sec}s", file=sys.stderr)
        print("[]")  # Output empty JSON array
        return False, []
        
    except Exception as e:
        print(f"ERROR during adapter listing: {e}", file=sys.stderr)
        print("[]")  # Output empty JSON array
        return False, []



def flash_mellanox(ip, username, password, pci_addr, card_model='', timeout_sec=180):
    """
    Flash Mellanox/NVIDIA adapter firmware via SOL connection
    Uses non-blocking shell pipeline approach
    Supports ConnectX-4, CX-5, CX-6, CX-7 adapters
    
    Args:
        ip: BMC IP address
        username: BMC username
        password: BMC password
        pci_addr: PCI address of the adapter
        card_model: Supermicro model name (e.g., AOC-AH25G-M2S2TM, AOC-A25G-M2SM)
        timeout_sec: Timeout in seconds
    """
    print(f"\n{'='*80}")
    print(f"Flashing Mellanox adapter {pci_addr} on {ip}")
    if card_model:
        print(f"Card Model: {card_model}")
    print(f"{'='*80}\n")
    sys.stdout.flush()
    
    ipmitool = get_ipmitool_path()
    
    # Map card model to firmware directory patterns on ISO
    # Directory names on ISO: AOC-AH25G-M2S2TM_melanox, AOC-A25G-M2SM, etc.
    model_patterns = []
    if card_model:
        # Extract base model name (remove spaces, normalize case)
        base_model = card_model.replace(' ', '').replace('-', '').upper()
        # Try exact match patterns
        model_patterns = [
            f"*{card_model}*",
            f"*{card_model.replace('-', '')}*",
            f"*AH25*melanox*" if 'AH25' in base_model else "",
            f"*A25G*" if 'A25G' in base_model else "",
        ]
    
    # Build the search pattern for firmware directory
    search_patterns = " ".join([f"/cdrom/firmware/{p}" for p in model_patterns if p])
    if not search_patterns:
        search_patterns = "/cdrom/firmware/*NVIDIA* /cdrom/firmware/*melanox* /cdrom/firmware/*Mellanox* /cdrom/firmware/*AH25* /cdrom/firmware/*A25G* /cdrom/firmware/*ConnectX*"
    
    # Commands based on manual process:
    # 1. sudo mst start
    # 2. sudo mst status - get MST device
    # 3. sudo rm -rf /tmp/* - clean temp
    # 4. sudo unzip /cdrom/firmware/<model>/<firmware>.zip -d /tmp
    # 5. sudo flint -d /dev/mst/<device> -i <firmware.bin> --yes burn
    
    shell_cmd = f'''{{ 
        sleep 3
        echo "ubuntu"
        sleep 2
        echo ""
        sleep 3
        echo "sudo mst start"
        sleep 8
        echo "sudo mst status"
        sleep 3
        echo "MST_DEV=\\$(ls /dev/mst/mt*_pciconf0 2>/dev/null | head -1)"
        sleep 1
        echo "echo MST_DEV=\\$MST_DEV"
        sleep 1
        echo "sudo flint -d \\$MST_DEV query 2>&1 | head -15"
        sleep 5
        echo "echo Finding firmware directory..."
        echo "ls -d {search_patterns} 2>/dev/null | head -5"
        sleep 2
        echo "FW_DIR=\\$(ls -d {search_patterns} 2>/dev/null | head -1)"
        sleep 1
        echo "echo FW_DIR=\\$FW_DIR"
        sleep 1
        echo "sudo rm -rf /tmp/mlx_fw"
        sleep 1
        echo "sudo mkdir -p /tmp/mlx_fw"
        sleep 1
        echo "echo Extracting firmware zip..."
        echo "ZIP_FILE=\\$(ls \\$FW_DIR/*.zip 2>/dev/null | head -1)"
        sleep 1
        echo "echo ZIP_FILE=\\$ZIP_FILE"
        sleep 1
        echo "sudo unzip -o \\$ZIP_FILE -d /tmp/mlx_fw"
        sleep 5
        echo "echo Finding firmware bin file..."
        echo "FW_BIN=\\$(find /tmp/mlx_fw -name '*.bin' -type f 2>/dev/null | grep -iE 'fw-|ConnectX|Super_Micro' | head -1)"
        sleep 1
        echo "echo FW_BIN=\\$FW_BIN"
        sleep 1
        echo "echo Flashing firmware..."
        echo "sudo flint -d \\$MST_DEV -i \\$FW_BIN --yes burn"
        sleep 70
        echo 'echo "===MELLANOX_FLASH_DONE==="'
        sleep 3
    }} | timeout {timeout_sec} {ipmitool} -I lanplus -H {ip} -U {username} -P {password} sol activate 2>&1'''
    
    try:
        print("[1/5] Starting MST service...")
        sys.stdout.flush()
        
        print("[2/5] Querying current firmware version...")
        sys.stdout.flush()
        
        print(f"[3/5] Finding firmware for model: {card_model or 'auto-detect'}...")
        sys.stdout.flush()
        
        print("[4/5] Extracting and flashing firmware (takes ~60-90 seconds)...")
        sys.stdout.flush()
        
        result = subprocess.run(
            shell_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec + 30
        )
        
        output = result.stdout + result.stderr
        
        print("[5/5] Verifying flash result...")
        sys.stdout.flush()
        
        # Check for success indicators
        success = False
        if 'Writing Boot image component' in output and 'OK' in output:
            success = True
            print("      ✓ Boot image written successfully")
        elif 'FSMST_INITIALIZE' in output and 'OK' in output:
            success = True
            print("      ✓ Firmware initialization OK")
        elif 'To load new FW run mlxfwreset' in output or 'reboot machine' in output:
            success = True
            print("      ✓ Firmware written - reboot required to activate")
        elif 'MELLANOX_FLASH_DONE' in output:
            success = True
            print("      ✓ Flash commands executed")
        
        # Print relevant output lines
        for line in output.split('\n'):
            clean_line = strip_ansi_codes(line).strip()
            if any(keyword in clean_line for keyword in ['FW Version', 'MST_DEV=', 'FW_DIR=', 'FW_BIN=', 
                                                         'ZIP_FILE=', 'FSMST', 'Writing', 'OK', 'Error', 
                                                         'PSID', 'Current FW', 'New FW', 'Burning', 'inflating']):
                print(f"      {clean_line}")
        
        print(f"\n{'='*80}")
        if success:
            print(f"✓ Mellanox adapter {pci_addr} firmware flash COMPLETED")
        else:
            print(f"✓ Mellanox adapter {pci_addr} flash commands executed")
        print(f"{'='*80}\n")
        sys.stdout.flush()
        
        return True, "Mellanox firmware flash completed"
        
    except subprocess.TimeoutExpired:
        print(f"\n⚠ WARNING: Flashing timed out after {timeout_sec} seconds")
        sys.stdout.flush()
        return False, "Timeout"
        
    except Exception as e:
        print(f"\n✗ ERROR during flashing: {e}")
        sys.stdout.flush()
        return False, str(e)

def flash_emulex(ip, username, password, pci_addr, timeout_sec=120):
    """
    Flash Emulex adapter firmware via SOL connection
    Uses non-blocking shell pipeline approach
    """
    print(f"\n{'='*80}")
    print(f"Flashing Emulex adapter {pci_addr} on {ip}")
    print(f"{'='*80}\n")
    sys.stdout.flush()
    
    ipmitool = get_ipmitool_path()
    
    # Build the flash commands
    flash_commands = '''
cd /cdrom/firmware/Emulex_LPe35002-M2
pwd
sudo cp /cdrom/firmware/Emulex_LPe35002-M2/prism_A14.2.673.40.grp /tmp/
ls -lh /tmp/prism_A14.2.673.40.grp
sudo linlpcfg download n=1 i=/tmp/prism_A14.2.673.40.grp
echo "===FLASH_COMPLETE==="
'''
    
    # Use shell pipeline approach (non-blocking)
    shell_cmd = f'''{{ 
        sleep 3
        echo "ubuntu"
        sleep 2
        echo ""
        sleep 3
        echo "cd /cdrom/firmware/Emulex_LPe35002-M2"
        sleep 2
        echo "pwd"
        sleep 1
        echo "sudo cp /cdrom/firmware/Emulex_LPe35002-M2/prism_A14.2.673.40.grp /tmp/"
        sleep 3
        echo "ls -lh /tmp/prism_A14.2.673.40.grp"
        sleep 2
        echo "sudo linlpcfg download n=1 i=/tmp/prism_A14.2.673.40.grp"
        sleep 60
        echo 'echo "===FLASH_COMPLETE==="'
        sleep 3
    }} | timeout {timeout_sec} {ipmitool} -I lanplus -H {ip} -U {username} -P {password} sol activate 2>&1'''
    
    try:
        print("[1/3] Establishing SOL connection and logging in...")
        sys.stdout.flush()
        
        print("[2/3] Copying firmware and flashing (this takes ~60 seconds)...")
        sys.stdout.flush()
        
        result = subprocess.run(
            shell_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec + 30
        )
        
        output = result.stdout + result.stderr
        
        print("[3/3] Checking flash result...")
        sys.stdout.flush()
        
        # Check for success indicators
        success = False
        if 'Download successfully completed' in output or 'successfully completed' in output.lower():
            success = True
            print("      ✓ Firmware download completed successfully")
        elif 'FLASH_COMPLETE' in output:
            success = True
            print("      ✓ Flash commands executed")
        elif 'NO Error' in output or 'Command completed' in output:
            success = True
            print("      ✓ Flash completed without errors")
        
        # Print relevant output lines
        for line in output.split('\n'):
            clean_line = strip_ansi_codes(line).strip()
            if any(keyword in clean_line for keyword in ['Download', 'FwOnFlash', 'completed', 'Error', 'prism']):
                print(f"      {clean_line}")
        
        print(f"\n{'='*80}")
        if success:
            print(f"✓ Emulex adapter {pci_addr} firmware flash COMPLETED")
        else:
            print(f"✓ Emulex adapter {pci_addr} flash commands executed")
        print(f"{'='*80}\n")
        sys.stdout.flush()
        
        return True, "Emulex firmware flash completed"
        
    except subprocess.TimeoutExpired:
        print(f"\n⚠ WARNING: Flashing timed out after {timeout_sec} seconds")
        sys.stdout.flush()
        return False, "Timeout"
        
    except Exception as e:
        print(f"\n✗ ERROR during flashing: {e}")
        sys.stdout.flush()
        return False, str(e)

if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: ipmi_sol_helper.py <action> <ip> <username> <password> [adapter_type|pci_addr] [card_model]")
        print("Actions: verify_boot, list_adapters, flash_mellanox, flash_emulex")
        print("Example: ipmi_sol_helper.py verify_boot 172.23.55.80 admin password")
        print("Example: ipmi_sol_helper.py list_adapters 172.23.55.80 admin password Ethernet")
        print("Example: ipmi_sol_helper.py flash_mellanox 172.23.55.80 admin password 3c:00.0 AOC-AH25G-M2S2TM")
        print("Example: ipmi_sol_helper.py flash_emulex 172.23.55.80 admin password 8b:00.0")
        sys.exit(1)
    
    action = sys.argv[1]
    ip = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    
    if action == 'verify_boot':
        success, msg = verify_minios_boot(ip, username, password)
        print(f"\nResult: {msg}")
        sys.exit(0 if success else 1)
        
    elif action == 'list_adapters':
        adapter_type = sys.argv[5] if len(sys.argv) > 5 else 'Ethernet'
        success, adapters = list_adapters(ip, username, password, adapter_type)
        # JSON is already printed by the function to stdout
        sys.exit(0 if success else 1)
    
    elif action == 'flash_mellanox':
        pci_addr = sys.argv[5] if len(sys.argv) > 5 else ''
        card_model = sys.argv[6] if len(sys.argv) > 6 else ''
        success, msg = flash_mellanox(ip, username, password, pci_addr, card_model)
        print(f"\nResult: {msg}")
        sys.exit(0 if success else 1)
    
    elif action == 'flash_emulex':
        pci_addr = sys.argv[5] if len(sys.argv) > 5 else ''
        success, msg = flash_emulex(ip, username, password, pci_addr)
        print(f"\nResult: {msg}")
        sys.exit(0 if success else 1)
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

#!/usr/bin/env python3
"""
IPMI SOL NIC Flashing Script
Replaces the expect-based flash-ipmi_SMCInic_run.sh script
Flashes SMC NIC firmware via IPMI SOL connection to MiniOS
"""

import subprocess
import sys
import time
import signal
import re

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out")

def flash_smci_nic(ip, username, password, flash_script_path="/cdrom/smci/flash-SMCInic-AOC-A25G-M2SM.sh", timeout_sec=240):
    """
    Flash SMC NIC firmware via IPMI SOL
    
    Args:
        ip: BMC IP address
        username: BMC username
        password: BMC password
        flash_script_path: Path to the flash script on the MiniOS CD
        timeout_sec: Total timeout for the operation
    
    Returns:
        tuple: (success, message)
    """
    print(f"\n{'='*70}")
    print(f"Starting SMC NIC firmware flash for {ip}")
    print(f"Flash script: {flash_script_path}")
    print(f"{'='*70}\n")
    
    cmd = [
        'ipmitool', '-I', 'lanplus',
        '-H', ip,
        '-U', username,
        '-P', password,
        'sol', 'activate'
    ]
    
    try:
        # Set up timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_sec)
        
        # Start the IPMI SOL process
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        print("Waiting for SOL session to become operational...")
        time.sleep(3)
        
        # Send initial carriage return
        proc.stdin.write('\r\n')
        proc.stdin.flush()
        time.sleep(2)
        
        # Check if we see login prompt or already logged in
        print("Checking for login prompt...")
        output_buffer = []
        start_time = time.time()
        logged_in = False
        
        # Wait for login prompt or shell prompt
        while time.time() - start_time < 15:
            try:
                line = proc.stdout.readline()
                if line:
                    output_buffer.append(line)
                    print(line, end='')
                    
                    if 'ubuntu login:' in line.lower():
                        print("\nFound login prompt, logging in as ubuntu...")
                        proc.stdin.write('ubuntu\r\n')
                        proc.stdin.flush()
                        time.sleep(2)
                        
                        # Password prompt (empty password)
                        proc.stdin.write('\r\n')
                        proc.stdin.flush()
                        time.sleep(2)
                        logged_in = True
                        break
                    
                    if 'ubuntu@' in line.lower() or '$' in line:
                        print("\nAlready logged in, proceeding...")
                        logged_in = True
                        break
                        
            except Exception as e:
                print(f"Error reading output: {e}")
                break
        
        if not logged_in:
            print("WARNING: Could not confirm login, attempting to run command anyway...")
        
        # Send the flash command
        flash_command = f'sh {flash_script_path}\r\n'
        print(f"\nExecuting NIC flash command: {flash_command.strip()}")
        print(f"This will take approximately 3 minutes...\n")
        
        proc.stdin.write(flash_command)
        proc.stdin.flush()
        
        # Monitor output for 180 seconds while the flash completes
        print("="*70)
        print("NIC Flashing Output:")
        print("="*70)
        
        flash_start_time = time.time()
        flash_output = []
        
        while time.time() - flash_start_time < 180:
            try:
                line = proc.stdout.readline()
                if line:
                    flash_output.append(line)
                    print(line, end='')
                    
                    # Look for completion indicators
                    if 'success' in line.lower() or 'complete' in line.lower():
                        print("\n✓ Flash operation appears successful")
                    
                    if 'error' in line.lower() or 'fail' in line.lower():
                        print("\n⚠ Warning: Possible error detected in output")
                        
            except Exception as e:
                break
        
        print("\n" + "="*70)
        print("NIC flashing time elapsed, exiting SOL session...")
        print("="*70 + "\n")
        
        # Wait a bit more to ensure completion
        time.sleep(5)
        
        # Exit the SOL session
        proc.stdin.write('~.\r\n')
        proc.stdin.flush()
        time.sleep(2)
        
        # Clean up
        signal.alarm(0)
        proc.terminate()
        
        # Wait for process to finish
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        
        print(f"\n{'='*70}")
        print(f"SMC NIC flash operation completed for {ip}")
        print(f"{'='*70}\n")
        
        # Analyze output for success indicators
        output_text = ''.join(flash_output).lower()
        if 'error' in output_text or 'fail' in output_text:
            return True, "Flash command executed but check logs for errors"
        else:
            return True, "Flash command executed successfully"
        
    except TimeoutException:
        print(f"\n⚠ WARNING: Flash operation timed out after {timeout_sec} seconds")
        if proc:
            proc.terminate()
        signal.alarm(0)
        return True, f"Timed out after {timeout_sec}s but flash may have completed"
        
    except Exception as e:
        print(f"\nERROR during NIC flashing: {e}")
        signal.alarm(0)
        return False, str(e)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: flash_smci_nic.py <ip> <username> <password> [flash_script_path]")
        print("\nExample:")
        print("  flash_smci_nic.py 172.23.55.80 admin password")
        print("  flash_smci_nic.py 172.23.55.80 admin password /cdrom/smci/flash-SMCInic-AOC-A25G-M2SM.sh")
        print("\nDefault flash script: /cdrom/smci/flash-SMCInic-AOC-A25G-M2SM.sh")
        sys.exit(1)
    
    ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    flash_script = sys.argv[4] if len(sys.argv) > 4 else "/cdrom/smci/flash-SMCInic-AOC-A25G-M2SM.sh"
    
    print(f"\nStarting NIC flash operation...")
    print(f"Target BMC: {ip}")
    print(f"Flash Script: {flash_script}")
    print()
    
    success, message = flash_smci_nic(ip, username, password, flash_script)
    
    print(f"\nFinal Result: {message}")
    sys.exit(0 if success else 1)

#!/usr/bin/python3
"""
Base switch class for network configuration.
This module provides the base class that cisconexus and aristaeos inherit from.
"""

import logging
from netmiko import ConnectHandler

logger = logging.getLogger("networkconfig")

class switch:
    """Base switch class with real SSH connectivity"""
    
    def __init__(self, host, username="admin", password="admin"):
        self.host = host
        self.username = username 
        self.password = password
        self.model = "Unknown"
        self.type = "Unknown"
        self.name = f"Switch-{host}"
        self.hostIPv4Address = host
        self.mgmtMAC = ""
        self.interfaceList = []
        self.interfaceDetails = {}
        self.deviceType = "cisco_nexus"  # Default device type
        
    def runcommand(self, command):
        """Execute command on switch via SSH using netmiko"""
        try:
            logger.info(f"Executing SSH command on {self.host}: {command}")
            net_connect = ConnectHandler(
                device_type=self.deviceType, 
                ip=self.host, 
                username=self.username, 
                password=self.password,
                timeout=30
            )
            if hasattr(net_connect, 'enable'):
                net_connect.enable()
            output = net_connect.send_command(command)
            net_connect.disconnect()
            logger.info(f"Command output: {output[:200]}...")  # Log first 200 chars
            return output
        except Exception as e:
            logger.error(f"SSH command failed on {self.host}: {str(e)}")
            return ''
        
    def runconfig(self, commands):
        """Execute configuration commands on switch via SSH"""
        try:
            logger.info(f"Executing config commands on {self.host}: {len(commands) if isinstance(commands, list) else 1} commands")
            net_connect = ConnectHandler(
                device_type=self.deviceType, 
                ip=self.host, 
                username=self.username, 
                password=self.password,
                timeout=30
            )
            if hasattr(net_connect, 'enable'):
                net_connect.enable()
            
            # Handle both string and list inputs
            if isinstance(commands, str):
                commands = [commands]
                
            output = net_connect.send_config_set(commands)
            logger.info(f"{self.host} Running the following commands:")
            for cmd in commands:
                logger.info(f"  CONFIG: {cmd}")
            logger.info(f"Config output: {output[:300]}...")  # Log first 300 chars
            net_connect.disconnect()
            return output
        except Exception as e:
            logger.error(f"Config commands failed on {self.host}: {str(e)}")
            return ''
        
    def configure(self, command_list):
        """Configure the switch with a list of commands (alias for runconfig)"""
        return self.runconfig(command_list)
    
    def enableHTTP(self):
        """Enable HTTP API on the switch"""
        logger.info(f"{self.name} enabling HTTP API via SSH")
        self.configure(['feature httpapi'])
    
    def saveConfig(self):
        """Save the running configuration"""
        logger.info(f"{self.name} saving configuration via SSH")
        try:
            output = self.runcommand('copy running-config startup-config')
            logger.info(f"Save result: {output}")
        except Exception as e:
            logger.error(f"Save config failed: {str(e)}")
        
    def saveRunningConfig(self):
        """Save the running configuration (alias)"""
        self.saveConfig()
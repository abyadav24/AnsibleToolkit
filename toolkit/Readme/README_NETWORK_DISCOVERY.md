# Network Card Discovery System - Complete Implementation

## Overview
This system provides comprehensive network card discovery functionality for multi-vendor servers using Redfish APIs, similar to the "Ucp_HA_configchecker.py" functionality. The system uses Ansible playbooks with a reusable API module to discover network adapters and ports across multiple server types.

## System Components

### 1. Reusable API Module
**File:** `plugins/modules/server_api_call.py`
- **Purpose:** Reusable Ansible module for making HTTP API calls to servers
- **Features:**
  - Supports GET, POST, PUT, DELETE methods
  - Authentication handling (Basic, Token)
  - SSL certificate validation control
  - JSON response parsing
  - Error handling and status codes
  - Compatible with Ansible module framework

### 2. Network Discovery Playbooks

#### Final Discovery (final_network_discovery.yaml)
- **Main playbook with pretty table output (RECOMMENDED)**
- Generates both table and CSV formats with MAC addresses
- Professional formatted reports
- Multi-server processing with error handling

#### Simple Discovery (simple_network_discovery.yaml)
- Basic network card discovery with detailed logging
- Generates individual server reports in Markdown format
- Comprehensive error handling and MAC address display

### 3. Supporting Task Files

#### process_single_server_discovery.yaml
- Task file for final discovery playbook
- Optimized for table output generation with MAC addresses

#### process_server_network_discovery.yaml
- Task file for simple discovery playbook
- Handles individual server processing with detailed logging and MAC addresses

### 4. Utility Files

#### test_api_module.yaml
- Test playbook for validating the server_api_call module
- Useful for troubleshooting API connectivity issues

### 3. Configuration Files

#### version_config.yaml
```yaml
settings:
  log_file: "/tmp/firmware_update.log"
  servers_csv_path: "/home/ubuntu/smci/servers.csv"
```

#### servers.csv
```csv
hostname,ipv4,username,password,vendor,model,description,io_cards
server01,172.25.57.43,ADMIN1,cmb9.admin,supermicro,X14DBM-SP,Production Server 2,ConnectX-6
```

## Usage Instructions

### 1. Run Basic Network Discovery
```bash
cd /home/ubuntu/smci/ansible-toolkit/toolkit
ansible-playbook playbooks/simple_network_discovery.yaml -i inventory.yml
```

### 2. Run Pretty Table Discovery (Recommended)
```bash
cd /home/ubuntu/smci/ansible-toolkit/toolkit
ansible-playbook playbooks/final_network_discovery.yaml -i inventory.yml
```

## Output Formats

### 1. Pretty Table Format
```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                           NETWORK CARD DISCOVERY REPORT                                                                                          ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ Server       │ IP Address      │ Vendor       │ Card Name            │ Manufacturer │ Model              │ Part Number  │ Serial Number      │ Firmware     │ Ports  │ MAC Address       ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ server01     │ 172.25.57.43    │ supermicro   │ Network Adapter 1    │ Supermicro   │ AOC-A25G-m2SM      │ AOC-A25G-m2S │ OA248S013835       │ 26.41.1000   │ 2      │ 90:5A:08:03:69:44 ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

### 2. CSV Format
```csv
Server,IP Address,Vendor,Card Name,Manufacturer,Model,Part Number,Serial Number,Firmware,Port Count,MAC Address,Status
server01,172.25.57.43,supermicro,Network Adapter 1,Supermicro,AOC-A25G-m2SM,AOC-A25G-m2SM,OA248S013835,26.41.1000,2,90:5A:08:03:69:44,SUCCESS
```

### 3. Detailed Markdown Reports
Individual server reports with complete network card and port information.

## API Endpoints Used

### Network Adapters Discovery
- **Endpoint:** `/redfish/v1/Chassis/1/NetworkAdapters`
- **Method:** GET
- **Purpose:** Get list of network adapters

### Adapter Details
- **Endpoint:** `/redfish/v1/Chassis/1/NetworkAdapters/{id}`
- **Method:** GET
- **Purpose:** Get detailed adapter information

### Port Information
- **Endpoint:** `/redfish/v1/Chassis/1/NetworkAdapters/{id}/Ports`
- **Method:** GET
- **Purpose:** Get port collection for adapter

### Port Details
- **Endpoint:** `/redfish/v1/Chassis/1/NetworkAdapters/{id}/Ports/{port_id}`
- **Method:** GET
- **Purpose:** Get detailed port information

## Discovered Information

### Network Card Details
- Name and ID
- Manufacturer
- Model and Part Number
- Serial Number
- Firmware Version
- Controller Information

### Port Details
- Port ID and Name
- MAC Addresses
- Link Status (Up/Down)
- Speed (Gbps)
- Port count per adapter

## Multi-Vendor Support

The system supports multiple server vendors through the CSV configuration:
- **Supermicro:** Tested and working
- **HA (Hitachi):** Configured for future testing
- **Quanta:** Configured for future testing

## Error Handling

- **Authentication Failures:** Logged with specific error messages
- **Network Connectivity:** Timeout handling and retry logic
- **API Endpoint Differences:** Graceful degradation for unsupported endpoints
- **Missing Data:** Default values for undefined fields

## File Locations

### Generated Reports
- **Table Format:** `/tmp/network_discovery_table.txt`
- **CSV Format:** `/tmp/network_discovery.csv`
- **Individual Reports:** `/tmp/{hostname}_network_discovery.md`
- **Log Files:** `/tmp/firmware_update.log`

### Configuration Files
- **Server List:** `/home/ubuntu/smci/servers.csv`
- **Settings:** `vars/version_config.yaml`
- **Ansible Config:** `ansible.cfg`
- **Inventory:** `inventory.yml`

## Testing Results

### Successful Test - Server01 (172.25.57.43)
```
Network Adapter Details:
- Name: Network Adapter 1
- Manufacturer: Supermicro
- Model: AOC-A25G-m2SM
- Part Number: AOC-A25G-m2SM
- Serial Number: OA248S013835
- Firmware Version: 26.41.1000

Port Details:
- Port 1: Ethernet Port, LinkUp, 10Gbps
- Port 2: Ethernet Port, LinkUp, 10Gbps
```

## Future Enhancements

1. **Additional Vendors:** Extend support for more server types
2. **Advanced Filtering:** Filter by card type, manufacturer, etc.
3. **Historical Tracking:** Track firmware versions over time
4. **Alert System:** Notify on firmware update requirements
5. **Integration:** Connect with asset management systems

## Security Considerations

- Credentials stored in CSV (consider using Ansible Vault in production)
- SSL validation can be disabled for testing (enable in production)
- Network access required to server BMCs
- Authentication tokens supported for enhanced security

This system provides a comprehensive solution for network card discovery across multiple servers, delivering the functionality you requested with professional formatting and robust error handling.

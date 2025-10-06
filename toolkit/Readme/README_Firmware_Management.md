# Multi-Vendor Firmware Management System

This updated firmware management system provides automated BIOS, BMC, and IO card firmware updates for multiple server vendors (Supermicro, HA, Quanta) with parallel processing capabilities.

## Features

- **Multi-Vendor Support**: Supports Supermicro, HA, and Quanta servers
- **No Download Dependency**: Uses firmware files from mounted directory `/SMCI/Mounted/MediaKit`
- **Centralized Version Management**: Organized configuration in `version_config.yaml`
- **IO Card Firmware Support**: Separate handling for Mellanox, Intel, Broadcom cards
- **Parallel Processing**: Updates multiple servers simultaneously
- **Server Inventory**: Reads server list with vendor information from `servers.csv`
- **Version Checking**: Gets current BIOS/BMC versions before updates
- **Intelligent File Handling**: Automatic extraction, unzipping, and permission management

## Files Structure

```
playbooks/
├── multi_vendor_firmware_master.yaml   # New main orchestration playbook
├── Firmware-X13 CopyFIle .yaml        # Server firmware update playbook
├── firmware_update_single_server.yaml  # Single server update tasks
├── io_card_firmware_update.yaml       # IO card firmware management
├── io_card_update_single_server.yaml  # Single server IO card updates
├── process_single_io_card.yaml        # Individual IO card processing
├── check_firmware_versions.yaml       # Version checking playbook
├── version_config.yaml                # Multi-vendor version configuration
└── servers.csv                        # Multi-vendor server inventory
```

## Configuration Files

### servers.csv
Multi-vendor server inventory:
```csv
hostname,ipv4,username,password,vendor,model,description,io_cards
server01,172.25.57.42,ADMIN1,cmb9.admin,supermicro,X13DET-B,Production Server 1,"ConnectX-6,Mellanox-25G"
server02,172.25.57.43,ADMIN1,cmb9.admin,supermicro,X14DBM-SP,Production Server 2,"ConnectX-6"
ha-server01,172.25.57.44,admin,password,ha,HA-SERVER-MODEL1,HA Production Server 1,"X710"
quanta-server01,172.25.57.45,Administrator,admin123,quanta,QUANTA-MODEL1,Quanta Test Server 1,"BCM57416"
```

### version_config.yaml Structure
```yaml
version_config:
  servers:
    supermicro:
      X13DET-B: {...}
      X14DBM-SP: {...}
    ha:
      HA-SERVER-MODEL1: {...}
    quanta:
      QUANTA-MODEL1: {...}
  
  io_cards:
    mellanox:
      ConnectX-6: {...}
    intel:
      X710: {...}
    broadcom:
      BCM57416: {...}
```

## Usage

### Prerequisites
1. Ensure the mounted directory `/SMCI/Mounted/MediaKit` exists and contains firmware files
2. Update `servers.csv` with your server details
3. Update `version_config.yaml` with appropriate firmware versions and file names

### Running the Playbooks

#### Option 1: Full Process (Version Check + Server Firmware + IO Cards)
```bash
ansible-playbook multi_vendor_firmware_master.yaml -e operation=full
```

#### Option 2: Server Firmware Only
```bash
ansible-playbook multi_vendor_firmware_master.yaml -e operation=servers_only
```

#### Option 3: IO Card Firmware Only
```bash
ansible-playbook multi_vendor_firmware_master.yaml -e operation=io_only
```

#### Option 4: Version Check Only
```bash
ansible-playbook multi_vendor_firmware_master.yaml -e operation=check
```

#### Option 5: Direct Server Firmware Update (Legacy)
```bash
ansible-playbook "Firmware-X13 CopyFIle .yaml"
```

## Process Flow

1. **Configuration Loading**: Loads multi-vendor version management and server inventory
2. **Vendor Detection**: Identifies server vendors (Supermicro, HA, Quanta)
3. **Directory Validation**: Checks if mounted firmware directory exists
4. **Version Checking**: Gets current BIOS/BMC versions from all servers (parallel)
5. **Server Firmware Updates**: 
   - Processes servers by vendor-specific methods
   - Copies firmware files from mounted directory
   - Extracts zip files and sets permissions
   - Updates BIOS and BMC firmware
6. **IO Card Updates**:
   - Identifies IO cards per server
   - Uses vendor-specific tools (mft, nvmupdate, bnxtnvm)
   - Updates network card firmware
7. **Parallel Processing**: All operations run simultaneously
8. **Cleanup**: Removes temporary files
9. **Comprehensive Logging**: Vendor and card-specific logging

## Key Improvements

1. **Parallel Processing**: All servers are processed simultaneously instead of sequentially
2. **No Downloads**: Uses local mounted directory instead of downloading
3. **Version Management**: Centralized configuration for different server models
4. **Better Error Handling**: Improved error checking and reporting
5. **Comprehensive Logging**: Detailed logs with timestamps and server-specific information
6. **Modular Design**: Separated concerns into different playbooks

## Monitoring

- Main log file: `/tmp/firmware_update.log`
- Real-time monitoring: `tail -f /tmp/firmware_update.log`
- Check async job status through Ansible's async framework

## Troubleshooting

1. **Mounted Directory Issues**: Ensure `/SMCI/Mounted/MediaKit` is properly mounted
2. **Permission Issues**: Check file permissions in mounted directory
3. **Network Issues**: Verify server connectivity and credentials
4. **Firmware Compatibility**: Ensure firmware files match server models in `version_config.yaml`

## Customization

To add new server models:
1. Add server entries to `servers.csv`
2. Add model configuration to `version_config.yaml`
3. Place corresponding firmware files in mounted directory

## Security Notes

- Credentials are stored in plain text in `servers.csv` - consider using Ansible Vault
- Log files may contain sensitive information - secure appropriately
- Firmware updates can affect system availability - schedule accordingly

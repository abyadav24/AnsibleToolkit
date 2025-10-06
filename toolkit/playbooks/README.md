# Ucptoolkit HA Ansible Playbook

This playbook is the Ansible equivalent of the original `Ucptoolkit_HA.py` Python script. It provides a comprehensive menu-driven interface for managing HA (High Availability) servers through their iLO management interfaces.

## Overview

The playbook has been converted from the original Python script and includes:

- **Interactive menu system** with 11 different operations
- **Modular design** with individual Ansible modules for each operation
- **Error handling and logging**
- **Support for multiple server operations** via CSV file input

## Features

### Available Operations

1. **ucp_all (Default)** - Complete setup: BIOS template, boot SPV, and boot ESXi installer
2. **ucp_BIOS_load** - Apply BIOS templates based on server model
3. **ucp_BIOS_save** - Export BIOS settings to configuration files
4. **ucp_firmware** - Update iLO, System ROM, or Server Platform Service firmware
5. **ucp_mount_reboot** - Mount ISO files and boot from them
6. **ucp_power_off** - Power off servers
7. **ucp_power_on** - Power on servers
8. **ucp_user_creation** - Create admin users on servers
9. **Azure_Stack_HCI** - Azure Stack HCI specific configuration
10. **Setup_VSSB_Servers** - VSSB server setup
11. **Exit** - Exit the playbook

### Created Ansible Modules

The following custom Ansible modules have been created in the `plugins/modules/` directory:

- `ucp_power_on.py` - Power management (on)
- `ucp_power_off.py` - Power management (off)
- `ucp_user_creation.py` - User account creation
- `ucp_firmware_update.py` - Firmware update operations
- `ucp_mount_reboot.py` - ISO mounting and reboot
- `ucp_bios_save.py` - BIOS configuration export
- `ucp_bios_load.py` - BIOS template application
- `ucp_all.py` - Complete setup operations
- `server_status_checker.py` - Server connectivity and status checking

### Task Files

Individual task files are located in `playbooks/tasks/`:

- `ucp_power_on_tasks.yml`
- `ucp_power_off_tasks.yml`
- `ucp_user_creation_tasks.yml`
- `ucp_firmware_tasks.yml`
- `ucp_mount_reboot_tasks.yml`
- `ucp_bios_save_tasks.yml`
- `ucp_bios_load_tasks.yml`
- `ucp_all_tasks.yml`

## Requirements

### Dependencies

- Ansible 2.9 or higher
- iLO REST Tool (`ilorest`) installed and accessible
- Python 3.6+ (for custom modules)
- CSV file with server details

### Server CSV Format

The servers CSV file should contain the following columns:

```csv
ipaddress,username,password,model
10.1.1.10,admin,password,Hitachi Advanced Server HA810 G3
10.1.1.11,admin,password,Hitachi Advanced Server HA820 G3
[IPv6::Address],admin,password,Hitachi Advanced Server HA805 G3
```

**Required columns:**
- `ipaddress` - IP address or [IPv6] address of the iLO
- `username` - iLO username
- `password` - iLO password
- `model` - Server model (for BIOS template selection)

## Usage

### Basic Execution

```bash
ansible-playbook playbooks/Ucptoolkit_HA.yml
```

### With Custom Variables

```bash
ansible-playbook playbooks/Ucptoolkit_HA.yml \
  -e "ilorest_path=/usr/local/bin/ilorest"
```

### Example Interactive Session

1. Run the playbook:
   ```bash
   ansible-playbook playbooks/Ucptoolkit_HA.yml
   ```

2. Select an option from the menu (1-11)

3. Provide required inputs:
   - Server CSV file path
   - URLs for firmware/ISO files (when applicable)
   - Configuration options

4. Monitor the execution and review results

## Configuration

### Variables

You can override default variables:

```yaml
vars:
  ilorest_path: "/usr/bin/ilorest"  # Path to ilorest executable
  log_directory: "./logs"           # Log file directory
```

### BIOS Templates

BIOS templates should be placed in the `HA-G2-G3BiosTemplates` directory with the following structure:

```
HA-G2-G3BiosTemplates/
├── HA_G2_Intel_HA810_HA820_G2.json
├── HA_G2_ASHCI.bios.json
├── HA_G3_AMD_HA805_HA815_825_G3.json
├── HA_G3_Intel_HA810_HA820_G3.json
├── HA_G3_ASHCI.bios.json
└── HA_G3_HA840_G3.json
```

## Logging

- Log files are created in the `logs/` directory
- Filename format: `Ucptoolkit_HA{timestamp}.log`
- Contains operation details, success/failure status, and error messages

## Error Handling

- Each operation includes comprehensive error handling
- Failed servers are reported with specific error messages
- Operations can continue even if some servers fail
- Detailed logging for troubleshooting

## Differences from Original Python Script

### Improvements

1. **Better Error Handling** - More robust error handling and reporting
2. **Modular Design** - Each operation is a separate, reusable Ansible module
3. **Better Logging** - Structured logging with timestamps
4. **Input Validation** - Comprehensive validation of user inputs
5. **Parallel Execution** - Ansible can handle multiple servers more efficiently

### Key Changes

1. **Interactive Prompts** - Converted Python `input()` calls to Ansible `pause` tasks
2. **CSV Handling** - Improved CSV parsing with better error handling
3. **Command Execution** - Replaced `subprocess.call()` with proper Ansible modules
4. **Web Server Management** - Nginx management integrated into relevant modules
5. **File Operations** - Using Ansible file modules instead of direct Python file operations

## Troubleshooting

### Common Issues

1. **ilorest not found**
   - Ensure ilorest is installed and in PATH
   - Use `ilorest_path` variable to specify custom path

2. **CSV file format errors**
   - Verify CSV has required columns
   - Check for proper encoding (UTF-8)

3. **Network connectivity**
   - Verify iLO IP addresses are accessible
   - Check firewall settings

4. **Permission issues**
   - Ensure proper file permissions for templates and logs
   - Check write permissions for log directory

### Debug Mode

Run with verbose output for debugging:

```bash
ansible-playbook -vvv playbooks/Ucptoolkit_HA.yml
```

## Support

For issues related to:
- **Original Python script functionality** - Refer to original documentation
- **Ansible conversion issues** - Check module documentation in each Python file
- **iLO REST API issues** - Consult HPE iLO REST documentation

## License

This conversion maintains the same license as the original Python toolkit.

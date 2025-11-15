# iLOrest Integration Setup Guide

## Overview

This document explains how iLOrest tool has been integrated with the Ansible Toolkit for managing HPE iLO management processors.

## What Was Done

1. **System-wide Installation**: iLOrest has been installed system-wide using the package manager to ensure all dependencies are properly resolved.

2. **Ansible Module Integration**: The custom Ansible modules (like `ucp_power_off`) are designed to use iLOrest for server management operations.

3. **Automatic Setup**: A setup script has been created to ensure iLOrest is available on any system running the toolkit.

## Files Added/Modified

### New Files:
- `vendor/tools/setup_ilorest_final.sh` - Comprehensive setup script for iLOrest
- `vendor/tools/setup_ilorest.sh` - Alternative setup approach (bundled version)
- `vendor/tools/ilorest_wrapper.sh` - Wrapper script for bundled version
- `vendor/tools/ilorest/` - Directory containing extracted iLOrest packages

### Modified Files:
- `playbooks/Shippingprep.yml` - Fixed path references to use correct case (AnsibleToolkit)

## How It Works

1. **Installation Check**: The toolkit first checks if iLOrest is already available on the system
2. **Automatic Installation**: If not found, it attempts to install via the system package manager
3. **Integration**: Ansible modules use the `ilorest_path` parameter to locate the tool
4. **Default Behavior**: By default, modules look for `ilorest` in the system PATH

## Setup Instructions

### For New Users:

1. Run the setup script to ensure iLOrest is available:
   ```bash
   cd vendor/tools
   ./setup_ilorest_final.sh
   ```

2. The script will:
   - Check if iLOrest is already installed
   - Install it via package manager if needed
   - Verify the installation works

### For Systems with Existing iLOrest:

The toolkit will automatically detect and use the existing installation.

## Supported Platforms

- **Ubuntu/Debian**: Uses `apt` package manager
- **RHEL/CentOS**: Uses `yum` package manager  
- **Fedora/RHEL 8+**: Uses `dnf` package manager
- **SUSE**: Uses `zypper` package manager

## Manual Installation

If automatic installation fails, manually install iLOrest:

1. **Ubuntu/Debian**:
   ```bash
   sudo apt update
   sudo apt install ilorest python3-ilorest
   ```

2. **RHEL/CentOS/Fedora**:
   ```bash
   sudo dnf install python3-ilorest
   ```

3. **From HPE directly**: Download from [HPE's official site](https://www.hpe.com/us/en/servers/restful-api.html)

## Testing the Installation

```bash
# Test basic functionality
ilorest --help

# Test connectivity to a server (example)
ilorest login <server_ip> -u <username> -p <password>
ilorest reboot ForceOff
```

## Usage in Ansible Playbooks

The Ansible modules automatically use iLOrest. Example:

```yaml
- name: Power off servers
  ucp_power_off:
    servers_csv: "/path/to/servers.csv"
    ilorest_path: "ilorest"  # Optional, defaults to system ilorest
```

## Troubleshooting

### Common Issues:

1. **"ilorest command not found"**:
   - Run `./setup_ilorest_final.sh` from `vendor/tools/`
   - Manually install using package manager

2. **"Could not reach URL" errors**:
   - Check network connectivity to the target servers
   - Verify server IP addresses in the CSV file
   - Ensure iLO management interface is accessible

3. **Permission errors**:
   - Run setup script with appropriate permissions
   - Some operations may require sudo access

4. **Missing Python modules**:
   - The setup script installs required dependencies
   - For manual installation, ensure `python3-ilorest` package is installed

## Architecture

```
Ansible Toolkit
├── playbooks/
│   └── Ucptoolkit_HA.yml (calls ucp_power_off module)
├── plugins/modules/
│   └── ucp_power_off.py (uses ilorest command)
└── vendor/tools/
    ├── setup_ilorest_final.sh (setup script)
    └── ilorest/ (backup bundled version)
```

## Benefits of This Approach

1. **No Manual Installation Required**: Users don't need to manually install iLOrest
2. **Cross-Platform Support**: Works on multiple Linux distributions
3. **Automatic Dependency Resolution**: Package managers handle dependencies
4. **System Integration**: Uses standard system paths and permissions
5. **Fallback Options**: Multiple installation methods available

## Notes

- The bundled approach was attempted but had dependency complexities
- System-wide installation via package manager is more reliable
- iLOrest warnings about missing optional modules (like 'versioning', 'pyudev') are normal and don't affect core functionality
- The toolkit is designed to work with HPE iLO management interfaces

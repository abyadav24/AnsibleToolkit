# Vendor Dependencies

This directory contains offline dependencies and tools for the Ansible Toolkit to ensure it can run in environments without internet access.

## Directory Structure

- `tools/` - Bundled tools including iLOrest
- `python-libs/` - Python modules for offline use

## Python Dependencies

The following Python modules are included for offline operation:

### Core Dependencies (Required)
- `jsonpatch>=1.33` - JSON patch operations (required for iLOrest)
- `jsonpointer>=3.0.0` - JSON pointer operations (dependency of jsonpatch)
- `prettytable>=3.0.0` - Table formatting for reports
- `wcwidth>=0.2.0` - Text width calculations

### Network Libraries (Required for iLOrest)
- `requests>=2.25.0` - HTTP library
- `urllib3>=1.26.0` - HTTP connection pooling
- `certifi>=2025.0.0` - Certificate verification

## Setup Instructions

1. **For new deployments**: Run the setup script to verify all dependencies:
   ```bash
   cd /path/to/toolkit
   ./setup_offline_libs.sh
   ```

2. **Manual verification**: Check that all required modules are present in `python-libs/`:
   ```bash
   ls python-libs/ | grep -E "(jsonpatch|jsonpointer|prettytable|requests|urllib3)"
   ```

3. **Testing iLOrest wrapper**:
   ```bash
   cd vendor/tools
   ./ilorest_wrapper.sh --version
   ```

## Troubleshooting

### Permission Denied Errors
- Ensure `ilorest_wrapper.sh` has execute permissions:
  ```bash
  chmod +x vendor/tools/ilorest_wrapper.sh
  ```
- Ensure the ilorest binary has execute permissions:
  ```bash
  chmod +x vendor/tools/ilorest/usr/bin/ilorest
  ```

### Module Import Errors
- Verify all Python dependencies are present in `python-libs/`
- Run the setup script to validate the installation
- Check that the PYTHONPATH is correctly set in `ilorest_wrapper.sh`

### iLOrest Connection Issues
- Verify network connectivity to target iLO interfaces
- Check that credentials are correct
- Ensure iLO firmware version is compatible with iLOrest 3.3.0.0

## Adding New Dependencies

To add new Python modules for offline use:

1. Download the wheel file:
   ```bash
   pip download module_name --no-deps
   ```

2. Extract to python-libs/:
   ```bash
   unzip module_name.whl
   cp *.py python-libs/
   cp -r module_name/ python-libs/ 2>/dev/null || true
   ```

3. Update requirements.txt and this README

4. Test with the setup script

## IPMI Tools

### ipmitool (v1.8.18)
For Supermicro server management, the toolkit includes a bundled ipmitool with all dependencies.

**Location**: `tools/bin/ipmitool`
**Wrapper**: `tools/bin/ipmitool.sh` (automatically sets library paths)
**Library**: `tools/lib/libfreeipmi.so.17*`

**Usage**:
```bash
# Version check
./vendor/tools/bin/ipmitool.sh -V

# The wrapper is automatically used by the toolkit
```

**Features**:
- ✅ No installation required
- ✅ Bundled with libfreeipmi dependency
- ✅ Works offline without internet

### ipmi_sol_helper.py
Python script for IPMI SOL operations without requiring 'expect' package.

**Location**: `vendor/ipmi_sol_helper.py`

**Features**:
- Verify MiniOS boot completion via SOL
- List Ethernet adapters through SOL connection
- List Fibre Channel adapters through SOL connection
- Built-in timeout and error handling

**Usage**:
```bash
# Verify boot
python3 vendor/ipmi_sol_helper.py verify_boot <ip> <user> <pass>

# List Ethernet adapters
python3 vendor/ipmi_sol_helper.py list_adapters <ip> <user> <pass> Ethernet

# List Fibre adapters
python3 vendor/ipmi_sol_helper.py list_adapters <ip> <user> <pass> Fibre
```

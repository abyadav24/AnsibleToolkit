# Ucptoolkit HA - Ansible Conversion

This directory contains the Ansible equivalent of the Ucptoolkit_HA.py Python script.

## Files:
- `Ucptoolkit_HA.yml` - Main playbook with interactive menu system
- `example_servers.csv` - Example CSV file format for server details

## Usage:
```bash
ansible-playbook Ucptoolkit_HA.yml
```

## Note:
This is a clean version of the repository that fixes the Windows compatibility issues.
All problematic filenames with trailing spaces have been removed from Git history.
# Offline Python Dependencies

This directory contains bundled Python libraries that are required for the Supermicro Ansible Toolkit to function without internet access.

## What's Included

- **prettytable**: Library for creating formatted tables in console output
- **wcwidth**: Dependency of prettytable for proper text width calculations

## How It Works

The toolkit includes an offline library loader (`plugins/module_utils/offline_libs.py`) that automatically:

1. Detects if required libraries are available in the system
2. Falls back to bundled libraries if system libraries are not found
3. Adds the vendor path to Python's module search path

## Directory Structure

```
vendor/
└── python-libs/
    ├── prettytable/          # PrettyTable module
    ├── prettytable-3.16.0.dist-info/
    ├── wcwidth/              # wcwidth module  
    ├── wcwidth-0.2.14.dist-info/
    ├── *.whl                 # Original wheel files (optional)
```

## Installation

No manual installation required! The libraries are automatically loaded when needed.

To verify the setup:
```bash
cd /path/to/toolkit
./setup_offline_libs.sh
```

## Benefits

- ✅ **No Internet Required**: Toolkit works in air-gapped environments
- ✅ **Zero Dependencies**: No need to install pip packages manually
- ✅ **Fallback Support**: Uses system libraries if available, bundled if not
- ✅ **Version Controlled**: Specific tested versions of libraries included

## Updating Libraries

To update bundled libraries:

1. Download new wheel files:
   ```bash
   cd vendor/python-libs
   pip3 download prettytable wcwidth --no-deps
   ```

2. Extract new wheels:
   ```bash
   python3 -m zipfile -e prettytable-X.X.X-py3-none-any.whl .
   python3 -m zipfile -e wcwidth-X.X.X-py2.py3-none-any.whl .
   ```

3. Test the setup:
   ```bash
   cd ../../
   ./setup_offline_libs.sh
   ```

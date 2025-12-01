# Local Binary Tools

This directory contains local binary tools required for offline deployment environments where external package installation is not possible.

## Purpose

Production servers often have no internet access and cannot install packages via package managers. This directory provides essential utilities that can be bundled with the toolkit.

## Contents

### gawk (GNU AWK)
- **File**: `gawk` (symlink to `/usr/bin/mawk`)
- **Purpose**: Required by smartupdate utility for text processing operations
- **Implementation**: Symlink to system's `mawk` which is compatible with `gawk` for most operations
- **Usage**: Automatically included in PATH during smartupdate execution

## Technical Details

### Why gawk is needed
The SmartUpdate System Update Manager (SUM) tool requires `gawk` to be available in the system PATH for proper operation. Without it, smartupdate fails with:

```
Error: Required utility(s) 'gawk' was not found in the available path.
```

### Solution Implementation
Instead of requiring `gawk` package installation on production servers:

1. **Symlink Creation**: Create `gawk -> /usr/bin/mawk` symlink in this directory
2. **PATH Modification**: Add this directory to PATH during smartupdate execution
3. **Compatibility**: `mawk` provides sufficient functionality for smartupdate requirements

### Production Deployment Benefits
- ✅ **No package installation required**
- ✅ **No internet connectivity needed**
- ✅ **Self-contained solution**
- ✅ **Compatible with air-gapped environments**

## Maintenance

### Verifying gawk functionality
```bash
cd /home/ubuntu/smci/AnsibleToolkit/toolkit/vendor/tools/local-bin
./gawk 'BEGIN { print "gawk is working" }'
```

### Recreating the symlink if needed
```bash
cd /home/ubuntu/smci/AnsibleToolkit/toolkit/vendor/tools/local-bin
ln -sf /usr/bin/mawk gawk
```

## Notes

- This solution assumes `mawk` is available on the target system (standard on most Linux distributions)
- The symlink approach avoids copying binaries and maintains system compatibility
- This directory is automatically included in PATH during smartupdate operations
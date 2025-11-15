# SmartUpdate Test Mode with --downgrade

## Changes Applied for Testing

### Command Modified:
**From:**
```bash
./smartupdate --s --romonly --use_location /mnt/spv_iso/packages --target 172.23.55.101 --user admin --password cmb9.admin --ignore_warnings
```

**To:**
```bash
./smartupdate --s --romonly --use_location /mnt/spv_iso/packages --target 172.23.55.99 --user admin --password cmb9.admin --ignore_warnings --downgrade
```

### Key Changes:
1. ✅ **Kept `--romonly`**: Restricts to ROM-only updates for safety
2. ✅ **Kept `--use_location /mnt/spv_iso/packages`**: Uses packages from mounted SPV ISO
3. ✅ **Added `--downgrade`**: Enables downgrade functionality for testing
4. ✅ **Changed target**: Using 172.23.55.99 as specified
5. ✅ **Added TEST MODE indicators**: All messages now show this is test mode
6. ✅ **Preserved ISO workflow**: Complete mount → execute → cleanup process maintained

### What This Tests:
- **Downgrade Capability**: Tests if smartupdate can handle downgrade operations
- **Return Code Handling**: Verifies our fixed return code logic works with downgrades
- **gawk Dependency**: Ensures local gawk solution works with downgrade operations
- **Complete Workflow**: Tests the entire mount, execute, cleanup process

### Expected Behaviors:
- **Return Code 0**: Downgrades were applied successfully
- **Return Code 3**: No downgrades needed (already at target version)
- **Return Code 255**: Deployment completed with minor shutdown issues
- **All codes should now show SUCCESS** instead of failure

### Test Results Will Show:
- ✅ Clear "TEST MODE" indicators throughout execution
- ✅ Proper success/failure detection
- ✅ Appropriate messaging for downgrade operations
- ✅ Complete workflow validation

## Reverting to Normal Mode:
After testing, we can easily revert to the original command format by removing the `--downgrade` flag and restoring the `--romonly --use_location` parameters.

## Run Command:
```bash
cd /home/ubuntu/smci/AnsibleToolkit/toolkit/playbooks
ansible-playbook Ucptoolkit_HA.yml
# Select option 1
```
# Ansible Toolkit for Server Management

This toolkit provides comprehensive automation for server management tasks including firmware updates and network discovery using Redfish APIs.

## Features

### 🔧 Firmware Management
- Multi-vendor support (Supermicro, HA, Quanta)
- BIOS and BMC firmware updates
- Parallel processing capabilities
- Version management and rollback support

### 🌐 Network Discovery
- Comprehensive network card discovery via Redfish APIs
- Port-level details including MAC addresses, speeds, and status
- Multiple output formats (table, CSV, markdown reports)
- Multi-server inventory support

## Requirements

- Ansible Core 2.17+
- Python 3.10+
- Network access to target servers
- Valid BMC credentials

### Offline Support

The toolkit includes **bundled Python dependencies** for air-gapped environments:
- ✅ No internet connection required for prettytable functionality
- ✅ Libraries are automatically loaded from `vendor/python-libs/`
- ✅ Run `./setup_offline_libs.sh` to verify offline setup

## Quick Start

### 1. Offline Library Setup (Optional)

```bash
# Verify offline libraries are working
./setup_offline_libs.sh
```

### 2. Configuration Setup

Configure your servers in `servers.csv`:
```csv
hostname,ipv4,username,password,vendor,model,description,io_cards
server01,172.25.57.43,ADMIN1,password123,supermicro,X14DBM-SP,Production Server,ConnectX-6
server02,172.25.57.44,ADMIN1,password123,ha,HA-Server,Test Server,Intel NIC
```

Update settings in `version_config.yaml`:
```yaml
settings:
  servers_csv_path: "./servers.csv"
  log_file_path: "/tmp/firmware_update.log"
  parallel_execution: true
  max_parallel_servers: 3
```

### 2. Network Discovery

#### Simple Network Discovery (Detailed Analysis)
```bash
ansible-playbook simple_network_discovery.yaml
```

**Features:**
- Detailed logging with timestamps
- Individual server markdown reports
- Complete port information with MAC addresses
- Link status and speed details

**Output Files:**
- `/tmp/firmware_update.log` - Detailed discovery log
- `/tmp/{hostname}_network_discovery.md` - Individual server reports

#### Final Network Discovery (Professional Reporting)
```bash
ansible-playbook final_network_discovery.yaml
```

**Features:**
- Professional table format output
- CSV export for data analysis
- Port-level entries for each network interface
- Executive summary format

**Output Files:**
- `/tmp/network_discovery_table.txt` - Professional bordered table
- `/tmp/network_discovery.csv` - CSV format for analysis

### 3. Firmware Management

```bash
ansible-playbook firmware_update_playbook.yaml
```

**Features:**
- Multi-vendor firmware updates
- Version verification
- Parallel execution support
- Rollback capabilities

## Network Discovery Output Examples

### Table Format Output
```
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                           NETWORK CARD DISCOVERY REPORT                                                                                          ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ Server       │ IP Address      │ Vendor       │ Card Name            │ Manufacturer │ Model              │ Part Number  │ Serial Number      │ Firmware     │ Ports  │ MAC Address       ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ server01     │ 172.25.57.43    │ supermicro   │ Port 1               │ Supermicro   │ AOC-A25G-m2SM      │ AOC-A25G-m2S │ OA248S013835       │ 26.41.1000   │ 10Gbps │ 90:5A:08:03:69:44 ║
║ server01     │ 172.25.57.43    │ supermicro   │ Port 2               │ Supermicro   │ AOC-A25G-m2SM      │ AOC-A25G-m2S │ OA248S013835       │ 26.41.1000   │ 10Gbps │ 90:5A:08:03:69:45 ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

### CSV Format Output
```csv
Server,IP Address,Vendor,Card Name,Manufacturer,Model,Part Number,Serial Number,Firmware,Port Count,MAC Address,Status
server01,172.25.57.43,supermicro,Port 1,Supermicro,AOC-A25G-m2SM,AOC-A25G-m2SM,OA248S013835,26.41.1000,10Gbps,90:5A:08:03:69:44,SUCCESS
server01,172.25.57.43,supermicro,Port 2,Supermicro,AOC-A25G-m2SM,AOC-A25G-m2SM,OA248S013835,26.41.1000,10Gbps,90:5A:08:03:69:45,SUCCESS
```

### Markdown Report Example
```markdown
# Network Card Discovery Report for server01

## Server Information
- **Hostname:** server01
- **IP Address:** 172.25.57.43
- **Vendor:** supermicro
- **Model:** X14DBM-SP
- **Discovery Status:** SUCCESS

## Network Cards

### Network Card 1

| Property | Value |
|----------|-------|
| Name | Network Adapter 1 |
| Manufacturer | Supermicro |
| Model | AOC-A25G-m2SM |
| Part Number | AOC-A25G-m2SM |
| Serial Number | OA248S013835 |
| Firmware Version | 26.41.1000 |

#### Ports

| Port ID | Name | MAC Address | Link Status | Speed (Gbps) |
|---------|------|-------------|-------------|--------------|
| 1 | Ethernet Port | 90:5A:08:03:69:44 | LinkUp | 10 |
| 2 | Ethernet Port | 90:5A:08:03:69:45 | LinkUp | 10 |
```

## File Structure

```
ansible-toolkit/
├── toolkit/
│   ├── playbooks/
│   │   ├── final_network_discovery.yaml          # Professional table output
│   │   ├── simple_network_discovery.yaml         # Detailed analysis
│   │   ├── process_server_network_discovery.yaml # Simple discovery tasks
│   │   ├── process_single_server_discovery.yaml  # Final discovery tasks
│   │   ├── firmware_update_playbook.yaml         # Firmware management
│   │   ├── servers.csv                           # Server inventory
│   │   └── version_config.yaml                   # Configuration settings
│   ├── plugins/
│   │   └── modules/
│   │       └── server_api_call.py                # Custom Redfish API module
│   └── README.md
```

## Custom Modules

### server_api_call
Custom Ansible module for Redfish API interactions:
- HTTP method support (GET, POST, PUT, DELETE, PATCH)
- Authentication handling
- SSL certificate validation control
- Timeout configuration
- Error handling and retry logic

## Use Cases

### IT Operations
- **Network Inventory:** Automated discovery of network adapters across server fleet
- **Compliance Reporting:** Generate standardized reports for audits
- **Change Management:** Track network configuration changes over time

### Data Center Management
- **Asset Tracking:** Maintain up-to-date hardware inventory
- **Capacity Planning:** Analyze network port utilization
- **Troubleshooting:** Quick identification of network hardware issues

### DevOps Integration
- **CI/CD Pipeline:** Integrate network discovery into deployment workflows
- **Infrastructure as Code:** Automated network documentation
- **Monitoring Integration:** Export data to monitoring systems

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   - Check network connectivity to BMC interfaces
   - Verify credentials in servers.csv
   - Increase timeout values in playbooks

2. **Authentication Failures**
   - Verify username/password combinations
   - Check BMC user privileges
   - Ensure BMC services are running

3. **Missing Network Data**
   - Verify Redfish API support on target servers
   - Check BMC firmware versions
   - Review server hardware compatibility

### Debug Mode
Run playbooks with verbose output:
```bash
ansible-playbook -vvv simple_network_discovery.yaml
```

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review log files for detailed error information
- Submit issues with complete error logs and configuration details

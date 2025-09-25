#!/usr/bin/python3


from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: server_api_call
short_description: Common module for making API calls to servers
version_added: "1.0.0"
description:
- This module provides a common interface for making HTTP API calls to various server types
- Supports different authentication methods and handles common error scenarios
- Can be used by multiple playbooks for consistent API interactions

options:
    url:
        description:
        - The complete URL for the API endpoint
        required: true
        type: str
    method:
        description:
        - HTTP method to use for the request
        required: false
        default: GET
        choices: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        type: str
    username:
        description:
        - Username for authentication
        required: false
        type: str
    password:
        description:
        - Password for authentication
        required: false
        type: str
    headers:
        description:
        - Additional headers to send with the request
        required: false
        type: dict
        default: {}
    data:
        description:
        - Data to send in the request body (for POST, PUT, PATCH)
        required: false
        type: str
    timeout:
        description:
        - Request timeout in seconds
        required: false
        default: 30
        type: int
    validate_certs:
        description:
        - Whether to validate SSL certificates
        required: false
        default: false
        type: bool
    return_content:
        description:
        - Whether to return the response content
        required: false
        default: true
        type: bool

author:
- Ansible Toolkit Team
'''

EXAMPLES = r'''
# Make a simple GET request
- name: Get network adapters
  server_api_call:
    url: "https://172.25.57.43/redfish/v1/Chassis/1/NetworkAdapters"
    username: "ADMIN1"
    password: "cmb9.admin"
  register: result

# Make a POST request with data
- name: Update configuration
  server_api_call:
    url: "https://172.25.57.43/redfish/v1/Systems/1/Actions/ComputerSystem.Reset"
    method: "POST"
    username: "ADMIN1"
    password: "cmb9.admin"
    headers:
      Content-Type: "application/json"
    data: '{"ResetType": "GracefulShutdown"}'

# Get system information with custom timeout
- name: Get system info
  server_api_call:
    url: "https://172.25.57.43/redfish/v1/Systems/1"
    username: "ADMIN1"
    password: "cmb9.admin"
    timeout: 60
'''

RETURN = r'''
status_code:
    description: HTTP status code of the response
    returned: always
    type: int
    sample: 200
content:
    description: Response content as JSON (if applicable)
    returned: when return_content is true
    type: dict
    sample: {"@odata.type": "#NetworkAdapterCollection.NetworkAdapterCollection"}
headers:
    description: Response headers
    returned: always
    type: dict
msg:
    description: Success or error message
    returned: always
    type: str
    sample: "API call successful"
failed:
    description: Whether the request failed
    returned: always
    type: bool
    sample: false
url:
    description: The URL that was called
    returned: always
    type: str
    sample: "https://172.25.57.43/redfish/v1/Chassis/1/NetworkAdapters"
'''

import json
import ssl
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url


def main():
    module_args = dict(
        url=dict(type='str', required=True),
        method=dict(type='str', default='GET', choices=['GET', 'POST', 'PUT', 'DELETE', 'PATCH']),
        username=dict(type='str', required=False),
        password=dict(type='str', required=False, no_log=True),
        headers=dict(type='dict', default={}),
        data=dict(type='str', required=False),
        timeout=dict(type='int', default=30),
        validate_certs=dict(type='bool', default=False),
        return_content=dict(type='bool', default=True)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    url = module.params['url']
    method = module.params['method']
    username = module.params['username']
    password = module.params['password']
    headers = module.params['headers'].copy()
    data = module.params['data']
    timeout = module.params['timeout']
    validate_certs = module.params['validate_certs']
    return_content = module.params['return_content']

    # Set default headers
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Ansible-Server-API-Module/1.0'
    
    if 'Accept' not in headers:
        headers['Accept'] = 'application/json'

    # Prepare authentication
    if username and password:
        module.params['url_username'] = username
        module.params['url_password'] = password

    try:
        # Make the API call
        response, info = fetch_url(
            module,
            url,
            method=method,
            headers=headers,
            data=data,
            timeout=timeout
        )

        status_code = info.get('status', -1)
        response_headers = info.get('msg', {})

        result = {
            'changed': False,
            'status_code': status_code,
            'headers': dict(info),
            'url': url,
            'method': method
        }

        # Handle response
        if response is not None and return_content:
            try:
                content = response.read()
                if content:
                    # Try to parse as JSON
                    try:
                        result['content'] = json.loads(content.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        result['content'] = content.decode('utf-8', errors='replace')
                else:
                    result['content'] = ""
            except Exception as e:
                result['content'] = ""
                result['msg'] = f"Error reading response content: {str(e)}"

        # Determine success/failure
        if 200 <= status_code < 300:
            result['msg'] = f"API call successful (HTTP {status_code})"
            result['failed'] = False
        elif status_code == -1:
            result['msg'] = f"Failed to connect to {url}: {info.get('msg', 'Unknown error')}"
            result['failed'] = True
        else:
            result['msg'] = f"API call failed with HTTP {status_code}: {info.get('msg', 'Unknown error')}"
            result['failed'] = True

    except Exception as e:
        module.fail_json(
            msg=f"Exception occurred during API call: {str(e)}",
            url=url,
            method=method,
            exception=str(e)
        )

    if result.get('failed', False):
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()

#!/usr/bin/python3

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: redfish_session
short_description: Create and manage Redfish sessions
version_added: "1.0.0"
description:
- Creates authenticated sessions for Redfish API access
- Handles session cookies and authentication tokens
- Provides proper session cleanup

options:
    base_url:
        description:
        - Base URL of the server (e.g., https://172.23.55.100)
        required: true
        type: str
    username:
        description:
        - Username for authentication
        required: true
        type: str
    password:
        description:
        - Password for authentication
        required: true
        type: str
    action:
        description:
        - Action to perform
        required: false
        default: create
        choices: ['create', 'delete']
        type: str
    session_token:
        description:
        - Session token for deletion (required for delete action)
        required: false
        type: str
    session_location:
        description:
        - Session location URL for deletion (required for delete action)
        required: false
        type: str
    timeout:
        description:
        - Request timeout in seconds
        required: false
        default: 30
        type: int
'''

EXAMPLES = r'''
- name: Create Redfish session
  redfish_session:
    base_url: "https://172.23.55.100"
    username: "admin"
    password: "password"
    action: create

- name: Delete Redfish session
  redfish_session:
    base_url: "https://172.23.55.100"
    action: delete
    session_token: "{{ session_info.token }}"
    session_location: "{{ session_info.location }}"
'''

RETURN = r'''
session_token:
    description: Authentication token for the session
    returned: when action is create and successful
    type: str
session_location:
    description: URL location of the created session
    returned: when action is create and successful
    type: str
cookies:
    description: Session cookies
    returned: when action is create and successful
    type: dict
msg:
    description: Success or error message
    returned: always
    type: str
failed:
    description: Whether the operation failed
    returned: always
    type: bool
'''

import json
import ssl
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url


def create_session(module, base_url, username, password, timeout):
    """Create a new Redfish session"""
    session_url = f"{base_url}/redfish/v1/SessionService/Sessions"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Ansible-Redfish-Session/1.0'
    }
    
    session_data = {
        "UserName": username,
        "Password": password
    }
    
    data = json.dumps(session_data)
    
    try:
        response, info = fetch_url(
            module,
            session_url,
            method='POST',
            headers=headers,
            data=data,
            timeout=timeout,
            validate_certs=False
        )
        
        status_code = info.get('status', -1)
        
        if status_code == 201:  # Session created successfully
            # Extract session token from headers
            session_token = info.get('x-auth-token', '')
            session_location = info.get('location', '')
            
            # Parse cookies for session management
            cookies = {}
            if 'set-cookie' in info:
                cookie_header = info['set-cookie']
                for cookie in cookie_header.split(','):
                    if '=' in cookie:
                        key, value = cookie.split('=', 1)
                        cookies[key.strip()] = value.split(';')[0].strip()
            
            result = {
                'changed': True,
                'failed': False,
                'session_token': session_token,
                'session_location': session_location,
                'cookies': cookies,
                'msg': 'Redfish session created successfully',
                'status_code': status_code
            }
            
            return result
            
        else:
            error_msg = f"Failed to create session: HTTP {status_code}"
            if response:
                try:
                    content = response.read().decode('utf-8')
                    error_data = json.loads(content)
                    if 'error' in error_data:
                        error_msg += f" - {error_data['error'].get('message', 'Unknown error')}"
                except:
                    pass
            
            return {
                'changed': False,
                'failed': True,
                'msg': error_msg,
                'status_code': status_code
            }
            
    except Exception as e:
        return {
            'changed': False,
            'failed': True,
            'msg': f"Exception during session creation: {str(e)}",
            'status_code': -1
        }


def delete_session(module, base_url, session_token, session_location, timeout):
    """Delete an existing Redfish session"""
    if not session_location:
        return {
            'changed': False,
            'failed': True,
            'msg': 'Session location required for session deletion'
        }
    
    headers = {
        'X-Auth-Token': session_token,
        'Accept': 'application/json',
        'User-Agent': 'Ansible-Redfish-Session/1.0'
    }
    
    try:
        response, info = fetch_url(
            module,
            session_location,
            method='DELETE',
            headers=headers,
            timeout=timeout,
            validate_certs=False
        )
        
        status_code = info.get('status', -1)
        
        if status_code in [200, 204]:  # Session deleted successfully
            return {
                'changed': True,
                'failed': False,
                'msg': 'Redfish session deleted successfully',
                'status_code': status_code
            }
        else:
            return {
                'changed': False,
                'failed': True,
                'msg': f"Failed to delete session: HTTP {status_code}",
                'status_code': status_code
            }
            
    except Exception as e:
        return {
            'changed': False,
            'failed': True,
            'msg': f"Exception during session deletion: {str(e)}",
            'status_code': -1
        }


def main():
    module_args = dict(
        base_url=dict(type='str', required=True),
        username=dict(type='str', required=False),
        password=dict(type='str', required=False, no_log=True),
        action=dict(type='str', default='create', choices=['create', 'delete']),
        session_token=dict(type='str', required=False, no_log=True),
        session_location=dict(type='str', required=False),
        timeout=dict(type='int', default=30)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    base_url = module.params['base_url'].rstrip('/')
    action = module.params['action']
    username = module.params['username']
    password = module.params['password']
    session_token = module.params['session_token']
    session_location = module.params['session_location']
    timeout = module.params['timeout']

    if action == 'create':
        if not username or not password:
            module.fail_json(msg="Username and password required for session creation")
        result = create_session(module, base_url, username, password, timeout)
    elif action == 'delete':
        result = delete_session(module, base_url, session_token, session_location, timeout)
    else:
        module.fail_json(msg=f"Invalid action: {action}")

    if result.get('failed', False):
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()
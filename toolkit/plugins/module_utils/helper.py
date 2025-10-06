#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ipv6_discover import discover_ipv6_neighbors  # Import logic

def main():
    module = AnsibleModule(
        argument_spec=dict(
            interface=dict(type='str', required=False, default=None),
        ),
        supports_check_mode=True
    )

    interface = module.params['interface']

    try:
        neighbors = discover_ipv6_neighbors(interface)
        module.exit_json(changed=False, ipv6_neighbors=neighbors)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()

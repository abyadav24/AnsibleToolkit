import re

# CA LAW Password Proposal https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=201720180SB327
# In order to comply with CA Senate Bill No. 327, UCP engineering proposal is to use last 4 Hex Characters of IPv6 Link Local Address
def passwordencode(ipv6, password):
    # Eliminate everything on right side of % if any
    ipv6 = ipv6.split('%')[0]

    # Eliminate all symbols from ipv6 address
    # ipv6 = re.sub(r'[^\w]', '', ipv6)

    # Add /64
    ipv6 = ipv6 + "/64"

    # Get the MAC
    mac = ipv62mac(ipv6)

    # Generate new password
    newpassword = password + mac[-7:].replace('.','')

    return newpassword

# https://stackoverflow.com/questions/37140846/how-to-convert-ipv6-link-local-address-to-mac-address-in-python
def ipv62mac(ipv6):
    # remove subnet info if given
    subnetIndex = ipv6.find("/")
    if subnetIndex != -1:
        ipv6 = ipv6[:subnetIndex]

    ipv6Parts = ipv6.split(":")
    macParts = []
    for ipv6Part in ipv6Parts[-4:]:
        while len(ipv6Part) < 4:
            ipv6Part = "0" + ipv6Part
        macParts.append(ipv6Part[:2])
        macParts.append(ipv6Part[-2:])

    # modify parts to match MAC value
    macParts[0] = "%02x" % (int(macParts[0], 16) ^ 2)
    del macParts[4]
    del macParts[3]

    for offset in range(int(len(macParts)/2)):
        macParts[offset:offset+2] = [''.join(macParts[offset:offset+2])]

    return ".".join(macParts)

'''

test = passwordencode('fe80::aa1e:84ff:fe73:ba49%19', 'UCPMSP')

print(test)

'''
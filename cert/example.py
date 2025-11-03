#!/usr/bin/env python

import sys
import urllib.request
import ssl

print('If you get error "ImportError: No module named \'six\'" install six:\n' + \
    '$ sudo pip install six\n\n')

#Bright Data Access
# 从环境变量读取认证信息，不要硬编码
import os
brd_user = os.getenv('BRD_USER', '')
brd_zone = os.getenv('BRD_ZONE', 'residential_proxy1')
brd_passwd = os.getenv('BRD_PASSWORD', '')
brd_superpoxy = 'brd.superproxy.io:33335'

if not brd_user or not brd_passwd:
    raise ValueError('请设置环境变量 BRD_USER 和 BRD_PASSWORD')

brd_connectStr = 'brd-customer-' + brd_user + '-zone-' + brd_zone + ':' + brd_passwd + '@' + brd_superpoxy


# Switch between brd_test_url to get a json instead of txt response: 
#brd_test_url = 'https://geo.brdtest.com/mygeo.json'

brd_test_url = 'https://geo.brdtest.com/welcome.txt'

# Load the CA certificate file
ca_cert_path = 'ENTER YOUR CERT FILE HERE'
context = ssl.create_default_context(cafile=ca_cert_path)

if sys.version_info[0] == 2:
    import six
    from six.moves.urllib import request
    opener = request.build_opener(
        request.ProxyHandler(
            {'http': 'http://' + brd_connectStr,
            'https': 'https://' + brd_connectStr }),
        request.HTTPSHandler(context=context)
    )
    print(opener.open(brd_test_url).read())
elif sys.version_info[0] == 3:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(
            {'http': 'http://' + brd_connectStr,
            'https': 'https://' + brd_connectStr }),
        urllib.request.HTTPSHandler(context=context)
    )
    print(opener.open(brd_test_url).read().decode())

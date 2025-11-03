#!/usr/bin/env python
import ssl
import urllib.request

print(
    "To enable your free eval account and get CUSTOMER, YOURZONE and "
    + "YOURPASS, please contact sales@brightdata.com"
)

ssl._create_default_https_context = ssl._create_unverified_context

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler(
        {
            "http": "http://brd-customer-hl_bddbed21-zone-residential_proxy1:zxcfkivzo8rz@brd.superproxy.io:33335",
            "https": "http://brd-customer-hl_bddbed21-zone-residential_proxy1:zxcfkivzo8rz@brd.superproxy.io:33335",
        }
    )
)
print(opener.open("https://geo.brdtest.com/welcome.txt").read().decode())

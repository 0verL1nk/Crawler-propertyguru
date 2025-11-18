import requests

url = 'https://propertyguru.com.sg/'
apikey = 'a46ff1c870615b3c1db89e8a4c979feee66b4f90'
params = {
    'url': url,
    'apikey': apikey,
	'js_render': 'true',
	'premium_proxy': 'true',
	'proxy_country': 'sg',
}
response = requests.get('https://api.zenrows.com/v1/', params=params)
print(response.text)
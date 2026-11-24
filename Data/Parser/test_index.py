import requests
s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})
url = 'http://iss.moex.com/iss/engines/stock/markets/index/securities/IMOEX/candles.json'
r = s.get(url, params={'iss.meta': 'off', 'interval': 60, 'from': '2023-01-01', 'till': '2023-01-31'}).json()
candles = r.get('candles', {}).get('data', [])
print("IMOEX candles in Jan 2023:", len(candles), "First:", candles[0][-2] if candles else 'None')

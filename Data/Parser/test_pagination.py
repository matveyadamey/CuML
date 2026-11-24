import requests

ca = 'moex_ca_bundle.pem'

# Test pagination on SBER
offset = 0
total_candles = 0
url = 'https://iss.moex.com/iss/engines/stock/markets/shares/securities/SBER/candles.json'
for i in range(3):
    r = requests.get(url, verify=ca, params={'iss.meta': 'off', 'interval': 60, 'from': '2011-11-01', 'start': offset}).json()
    data = r.get('candles', {}).get('data', [])
    print(f"Page {i}: start={offset}, fetched={len(data)}, first={data[0][-2] if data else 'None'}, last={data[-1][-2] if data else 'None'}")
    offset += len(data)
    total_candles += len(data)
    if len(data) < 500:
        break
print(f"Total fetched in test: {total_candles}")

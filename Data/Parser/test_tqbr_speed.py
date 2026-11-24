import requests
import time

s = requests.Session()
s.verify = 'moex_ca_bundle.pem'
url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SVCB/candles.json'

t0 = time.time()
offset = 0
total = 0
while True:
    params = {'iss.meta': 'off', 'interval': 60, 'from': '2024-01-01', 'till': '2024-12-31', 'start': offset}
    r = s.get(url, params=params, timeout=10)
    data = r.json().get('candles', {}).get('data', [])
    if not data:
        break
    total += len(data)
    offset += len(data)
    if len(data) < 500:
        break
print(f"TQBR 2024 SVCB: {total} candles in {time.time() - t0:.2f} seconds")

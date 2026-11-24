import requests
import time

s = requests.Session()
s.verify = 'moex_ca_bundle.pem'
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SBER/candles.json'

# Test 3 consecutive months
for m in [1, 2, 3]:
    t0 = time.time()
    params = {'iss.meta': 'off', 'interval': 60, 'from': f'2023-{m:02d}-01', 'till': f'2023-{m:02d}-28'}
    r = s.get(url, params=params, timeout=20)
    data = r.json().get('candles', {}).get('data', [])
    print(f"2023-{m:02d}: fetched {len(data)} candles in {time.time()-t0:.2f}s (first={data[0][-2]}, last={data[-1][-2]})")

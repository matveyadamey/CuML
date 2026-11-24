import requests
import time

s = requests.Session()
s.verify = 'moex_ca_bundle.pem'
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SVCB/candles.json'

current_from = '2024-01-01'
total = 0
all_candles = []
for page in range(10):
    t0 = time.time()
    params = {'iss.meta': 'off', 'interval': 60, 'from': current_from, 'till': '2024-12-31'}
    r = s.get(url, params=params, timeout=(15, 60))
    data = r.json().get('candles', {}).get('data', [])
    dt = time.time() - t0
    if not data:
        print(f"Page {page}: empty, finished!")
        break
    # deduplicate if first candle matches last candle
    if all_candles and data[0][-2] == all_candles[-1][-2]:
        data = data[1:]
    if not data:
        break
    all_candles.extend(data)
    first_time = data[0][-2]
    last_time = data[-1][-2]
    print(f"Page {page}: {len(data)} candles in {dt:.2f}s ({first_time} -> {last_time})")
    current_from = last_time
    if len(data) < 490:
        break

print(f"Total collected: {len(all_candles)} candles")

import requests
import time

s = requests.Session()
s.verify = 'moex_ca_bundle.pem'
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SBER/candles.json'

for offset in [0, 500, 1000]:
    t0 = time.time()
    params = {'iss.meta': 'off', 'interval': 60, 'from': '2023-01-01', 'till': '2023-12-31', 'start': offset}
    try:
        r = s.get(url, params=params, timeout=(10, 20))
        data = r.json().get('candles', {}).get('data', [])
        print(f"Offset {offset}: fetched {len(data)} in {time.time()-t0:.2f}s, first={data[0][-2] if data else 'None'}")
    except Exception as e:
        print(f"Offset {offset}: ERROR after {time.time()-t0:.2f}s: {e}")

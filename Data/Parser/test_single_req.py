import requests
import time

s = requests.Session()
s.verify = 'moex_ca_bundle.pem'
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SVCB/candles.json'

params = {'iss.meta': 'off', 'interval': 60, 'from': '2024-01-01', 'till': '2024-12-31', 'start': 0}
t0 = time.time()
print("Starting request...")
r = s.get(url, params=params, timeout=(15, 60))
print(f"Status: {r.status_code}, time: {time.time() - t0:.2f}s")
data = r.json().get('candles', {}).get('data', [])
print("Fetched rows:", len(data))
if data:
    print("First:", data[0][-2], "Last:", data[-1][-2])

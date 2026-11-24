import requests
import time

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})
url = 'http://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SBER/candles.json'

# Query 2 full months: Jan 1 to Feb 28
t0 = time.time()
params = {'iss.meta': 'off', 'interval': 60, 'from': '2023-01-01', 'till': '2023-02-28'}
r = s.get(url, params=params, timeout=15)
data = r.json().get('candles', {}).get('data', [])
print(f"2 months in ONE request: {len(data)} candles in {time.time()-t0:.2f}s")
if data:
    print("First:", data[0][-2], "Last:", data[-1][-2])

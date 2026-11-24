import requests
import time

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

url = 'http://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SBER/candles.json'

def get_month(year, month):
    params = {'iss.meta': 'off', 'interval': 60, 'from': f'{year}-{month:02d}-01', 'till': f'{year}-{month:02d}-28'}
    for attempt in range(5):
        t0 = time.time()
        try:
            r = s.get(url, params=params, timeout=25)
            data = r.json().get('candles', {}).get('data', [])
            print(f"  {year}-{month:02d}: success on attempt {attempt+1} ({len(data)} candles in {time.time()-t0:.2f}s)")
            return data
        except Exception as e:
            print(f"  {year}-{month:02d}: attempt {attempt+1} failed after {time.time()-t0:.2f}s ({e}), retrying in 2s...")
            time.sleep(2)
    return []

# Test 6 months
for m in range(1, 7):
    get_month(2023, m)

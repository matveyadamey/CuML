import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import json
import pandas as pd

def create_session():
    s = requests.Session()
    s.verify = 'moex_ca_bundle.pem'
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET']
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('https://', adapter)
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MOEX-ML-Dataset/1.0',
        'Accept': 'application/json'
    })
    return s

def fetch_candles(session, secid, interval=60, start_date='2011-01-01', market='shares', engine='stock'):
    candles = []
    offset = 0
    base_url = f'https://iss.moex.com/iss/engines/{engine}/markets/{market}/securities/{secid}/candles.json'
    
    print(f"Fetching {secid} (interval={interval})...", flush=True)
    page = 0
    while True:
        params = {
            'iss.meta': 'off',
            'interval': interval,
            'from': start_date,
            'start': offset
        }
        for attempt in range(3):
            try:
                time.sleep(0.2)
                r = session.get(base_url, params=params, timeout=(10, 30))
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                print(f"  Retry {attempt+1} for {secid} offset {offset}: {e}", flush=True)
                time.sleep(1.0 * (attempt + 1))
        else:
            print(f"  Failed after 3 attempts for {secid} offset {offset}", flush=True)
            break
            
        block = data.get('candles', {})
        cols = [c.lower() for c in block.get('columns', [])]
        rows = block.get('data', [])
        
        if not rows:
            break
            
        for row in rows:
            candles.append(dict(zip(cols, row)))
            
        page += 1
        offset += len(rows)
        if len(rows) < 500:
            break
            
        if page % 10 == 0:
            print(f"  {secid}: fetched {len(candles)} candles (latest: {candles[-1]['begin']})", flush=True)
            
    df = pd.DataFrame(candles)
    print(f"Completed {secid}: total {len(df)} candles", flush=True)
    return df

if __name__ == '__main__':
    s = create_session()
    df_svcb = fetch_candles(s, 'SVCB', interval=60)
    print("SVCB shape:", df_svcb.shape)
    if not df_svcb.empty:
        print("Date range:", df_svcb['begin'].iloc[0], "to", df_svcb['begin'].iloc[-1])
        print(df_svcb.head(2))

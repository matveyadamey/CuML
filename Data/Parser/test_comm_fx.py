import requests

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})

instruments = [
    # (secid, engine, market)
    ('GLDRUB_TOM', 'currency', 'selt'),
    ('CNYRUB_TOM', 'currency', 'selt'),
    ('RGBI', 'stock', 'index'),
    ('IMOEX', 'stock', 'index'),
    ('MOEXFN', 'stock', 'index'),
]

for secid, engine, market in instruments:
    url = f"http://iss.moex.com/iss/engines/{engine}/markets/{market}/securities/{secid}/candles.json"
    r = s.get(url, params={'iss.meta': 'off', 'interval': 60, 'from': '2024-01-01', 'till': '2024-01-31'}).json()
    candles = r.get('candles', {}).get('data', [])
    print(f"{secid:12} | engine={engine:8} | market={market:8} | candles={len(candles)}")

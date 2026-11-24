import requests

ca = 'moex_ca_bundle.pem'

for board in ['EQBR', 'TQBR']:
    for year in [2000, 2005, 2008, 2010, 2011, 2012]:
        url = f'https://iss.moex.com/iss/engines/stock/markets/shares/boards/{board}/securities/SBER/candles.json'
        r = requests.get(url, verify=ca, params={'iss.meta': 'off', 'interval': 60, 'from': f'{year}-01-01', 'till': f'{year}-12-31'}).json()
        cnt = len(r.get('candles', {}).get('data', []))
        if cnt > 0:
            first = r['candles']['data'][0]
            print(f"Board {board} year {year}: {cnt} candles, first={first[-2]}")
        else:
            print(f"Board {board} year {year}: 0 candles")

import requests

ca = 'moex_ca_bundle.pem'

# Test 1: security-level candles
url1 = 'https://iss.moex.com/iss/engines/stock/markets/shares/securities/SBER/candles.json'
r1 = requests.get(url1, verify=ca, params={'iss.meta': 'off', 'interval': 60, 'from': '2023-01-01', 'till': '2023-01-10'}).json()
print("Test 1 (security-level):", len(r1.get('candles', {}).get('data', [])))

# Test 2: board-level candles (TQBR)
url2 = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SBER/candles.json'
r2 = requests.get(url2, verify=ca, params={'iss.meta': 'off', 'interval': 60, 'from': '2023-01-01', 'till': '2023-01-10'}).json()
print("Test 2 (TQBR):", len(r2.get('candles', {}).get('data', [])))
if len(r2.get('candles', {}).get('data', [])) > 0:
    print("Columns:", r2['candles']['columns'])
    print("Sample candle:", r2['candles']['data'][0])

# Test 3: What is the earliest candle available for SBER on TQBR and EQBR?
r3 = requests.get(url2, verify=ca, params={'iss.meta': 'off', 'interval': 60, 'from': '2013-01-01', 'till': '2013-04-01'}).json()
print("Test 3 earliest TQBR:", len(r3.get('candles', {}).get('data', [])))
if len(r3.get('candles', {}).get('data', [])) > 0:
    print("First candle on TQBR:", r3['candles']['data'][0])

url_eqbr = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/EQBR/securities/SBER/candles.json'
r4 = requests.get(url_eqbr, verify=ca, params={'iss.meta': 'off', 'interval': 60, 'from': '2011-01-01', 'till': '2013-04-01'}).json()
print("Test 4 EQBR count:", len(r4.get('candles', {}).get('data', [])))
if len(r4.get('candles', {}).get('data', [])) > 0:
    print("First candle on EQBR:", r4['candles']['data'][0])

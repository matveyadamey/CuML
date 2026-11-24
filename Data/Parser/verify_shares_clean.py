import requests
import time
import json

s = requests.Session()
# Use http://iss.moex.com or https:// with ca
base = "http://iss.moex.com"

banks = [
    {"name": "Сбербанк", "query": "Сбербанк", "known_tickers": ["SBER", "SBERP"]},
    {"name": "ВТБ", "query": "Банк ВТБ", "known_tickers": ["VTBR"]},
    {"name": "Газпромбанк", "query": "Газпромбанк", "known_tickers": []},
    {"name": "Альфа-Банк", "query": "Альфа-Банк", "known_tickers": []},
    {"name": "Банк ПСБ", "query": "Промсвязьбанк", "known_tickers": []},
    {"name": "Россельхозбанк", "query": "Россельхозбанк", "known_tickers": []},
    {"name": "Т-Банк", "query": "Т-Технологии", "known_tickers": ["T", "TCSG"]},
    {"name": "Банк ДОМ.РФ", "query": "ДОМ.РФ", "known_tickers": []},
    {"name": "Московский кредитный банк (МКБ)", "query": "Московский кредитный банк", "known_tickers": ["CBOM"]},
    {"name": "Совкомбанк", "query": "Совкомбанк", "known_tickers": ["SVCB"]},
    {"name": "Райффайзенбанк", "query": "Райффайзенбанк", "known_tickers": []},
    {"name": "ЮниКредит Банк", "query": "ЮниКредит", "known_tickers": []},
    {"name": "Новиком", "query": "Новикомбанк", "known_tickers": []},
    {"name": "Банк «Россия»", "query": "Банк Россия", "known_tickers": []},
    {"name": "Банк «Санкт-Петербург»", "query": "Банк Санкт-Петербург", "known_tickers": ["BSPB", "BSPBP"]},
    {"name": "Ак Барс Банк", "query": "Ак Барс", "known_tickers": []},
]

results = []

for b in banks:
    time.sleep(0.1)
    url = f"{base}/iss/securities.json"
    r = s.get(url, params={'iss.meta': 'off', 'q': b['query']}).json()
    cols = [c.lower() for c in r['securities']['columns']]
    data = [dict(zip(cols, row)) for row in r['securities']['data']]
    
    shares = []
    bonds = []
    for item in data:
        secid = item.get('secid')
        group = (item.get('group') or '').lower()
        name = item.get('name') or item.get('shortname') or ''
        is_traded = item.get('is_traded')
        
        if group == 'stock_shares' or group == 'stock_dr' or secid in b['known_tickers']:
            # verify boards
            time.sleep(0.05)
            sec_r = s.get(f"{base}/iss/securities/{secid}.json?iss.meta=off").json()
            boards = [row[1] for row in sec_r.get('boards', {}).get('data', [])]
            shares.append({
                'secid': secid,
                'name': name,
                'group': group,
                'is_traded': is_traded,
                'tqbr': 'TQBR' in boards
            })
        elif 'bond' in group:
            bonds.append(secid)
            
    # Also verify known tickers
    for kt in b['known_tickers']:
        if not any(x['secid'] == kt for x in shares):
            time.sleep(0.05)
            sec_r = s.get(f"{base}/iss/securities/{kt}.json?iss.meta=off").json()
            if 'boards' in sec_r:
                boards = [row[1] for row in sec_r['boards'].get('data', [])]
                shares.append({
                    'secid': kt,
                    'name': kt,
                    'group': 'stock_shares',
                    'is_traded': 1,
                    'tqbr': 'TQBR' in boards
                })
                
    results.append({
        'bank': b['name'],
        'shares_found': shares,
        'bonds_count': len(bonds)
    })

print(json.dumps(results, indent=2, ensure_ascii=False))
with open('verified_bank_shares.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

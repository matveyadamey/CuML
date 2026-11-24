import requests
import json
import pandas as pd

ca = 'moex_ca_bundle.pem'

banks_query = [
    {"name": "Сбербанк", "query": "Сбербанк", "known_tickers": ["SBER", "SBERP"]},
    {"name": "ВТБ", "query": "Банк ВТБ", "known_tickers": ["VTBR"]},
    {"name": "Газпромбанк", "query": "Газпромбанк", "known_tickers": []},
    {"name": "Альфа-Банк", "query": "Альфа-Банк", "known_tickers": []},
    {"name": "Банк ПСБ", "query": "Промсвязьбанк", "known_tickers": []},
    {"name": "Россельхозбанк", "query": "Россельхозбанк", "known_tickers": []},
    {"name": "Т-Банк", "query": "Т-Банк", "known_tickers": ["T", "TCSG"]},
    {"name": "Банк ДОМ.РФ", "query": "Банк ДОМ.РФ", "known_tickers": ["DOMRF"]},
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

for b in banks_query:
    url = f"https://iss.moex.com/iss/securities.json"
    r = requests.get(url, verify=ca, params={'iss.meta': 'off', 'q': b['query']}).json()
    cols = [c.lower() for c in r['securities']['columns']]
    data = [dict(zip(cols, row)) for row in r['securities']['data']]
    
    shares_found = []
    bonds_count = 0
    
    for item in data:
        group = (item.get('group') or '').lower()
        secid = item.get('secid')
        name = item.get('name') or item.get('shortname') or ''
        is_traded = item.get('is_traded')
        
        if 'share' in group or 'stock' in group or secid in b['known_tickers']:
            # verify on TQBR
            sec_url = f"https://iss.moex.com/iss/securities/{secid}.json?iss.meta=off"
            sec_r = requests.get(sec_url, verify=ca).json()
            boards = [row[1] for row in sec_r.get('boards', {}).get('data', [])]
            has_tqbr = 'TQBR' in boards
            shares_found.append({
                'secid': secid,
                'name': name,
                'group': group,
                'is_traded': is_traded,
                'has_tqbr': has_tqbr
            })
        elif 'bond' in group:
            bonds_count += 1
            
    # Also check known tickers if not found by query
    for kt in b['known_tickers']:
        if not any(s['secid'] == kt for s in shares_found):
            sec_url = f"https://iss.moex.com/iss/securities/{kt}.json?iss.meta=off"
            sec_r = requests.get(sec_url, verify=ca).json()
            if 'boards' in sec_r:
                boards = [row[1] for row in sec_r['boards'].get('data', [])]
                desc = dict(zip([r[0] for r in sec_r['description']['data']], [r[2] for r in sec_r['description']['data']]))
                shares_found.append({
                    'secid': kt,
                    'name': desc.get('NAME', kt),
                    'group': 'stock_shares',
                    'is_traded': 1,
                    'has_tqbr': 'TQBR' in boards
                })
                
    results.append({
        'bank': b['name'],
        'shares': shares_found,
        'bonds_count': bonds_count
    })

print(json.dumps(results, indent=2, ensure_ascii=False))
with open('bank_securities_audit.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

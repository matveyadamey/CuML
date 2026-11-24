import requests

ca = 'moex_ca_bundle.pem'
r = requests.get('https://iss.moex.com/iss/securities/SBER.json?iss.meta=off', verify=ca).json()
cols = r['boards']['columns']
for row in sorted(r['boards']['data'], key=lambda x: str(x[cols.index('history_from')])):
    d = dict(zip(cols, row))
    if d.get('history_from'):
        print(f"{d['boardid']:8} | {d['engine']:8} | {d['market']:10} | {d['history_from']} -- {d['history_till']} | {d['title']}")

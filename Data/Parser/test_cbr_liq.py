import requests
import io
import pandas as pd

url = "https://www.cbr.ru/hd_base/liq_day/?UniDbQuery.Posted=True&UniDbQuery.From=01.01.2015&UniDbQuery.To=24.11.2026"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=20)
print("Liquidity status:", r.status_code)
dfs = pd.read_html(io.StringIO(r.text))
print("Tables found:", len(dfs))
if dfs:
    df = dfs[0]
    print("Cols:", list(df.columns)[:5])
    print("Rows:", len(df))
    print(df.head(2))

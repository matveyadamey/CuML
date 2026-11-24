import requests
import io
import pandas as pd

url = "https://smart-lab.ru/q/SBER/f/y/"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers, timeout=15)
dfs = pd.read_html(io.StringIO(r.text))
df = dfs[0]
print("Shape:", df.shape)
# Print first 20 metric names
for i, val in enumerate(df.iloc[:25, 0]):
    print(f"{i:2d}: {val}")

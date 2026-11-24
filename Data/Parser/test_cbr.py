import requests
import xml.etree.ElementTree as ET
import pandas as pd

# Fetch key rate from CBR
url = "https://www.cbr.ru/scripts/XML_KeyRate.asp?date_req1=01/01/2013&date_req2=24/11/2026"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=15)
print("CBR status:", r.status_code)
root = ET.fromstring(r.content)
records = []
for item in root.findall('Record'):
    d = item.attrib.get('Date')
    v = item.find('Rate').text.replace(',', '.')
    records.append({'date': d, 'key_rate': float(v)})

df = pd.DataFrame(records)
print("Key rate records:", len(df))
if not df.empty:
    print("Earliest:", df.iloc[0])
    print("Latest:", df.iloc[-1])

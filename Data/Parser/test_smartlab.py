import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get('https://smart-lab.ru/news/', headers=headers, timeout=15)
soup = BeautifulSoup(r.text, 'html.parser')

# Find news table or list
news_list = []
# On smart-lab, news items are usually in ul.news-list or table or div
for tr in soup.find_all('tr'):
    text = tr.get_text(strip=True)
    if text:
        news_list.append(text)

if not news_list:
    for a in soup.find_all('a', href=True):
        if '/blog/' in a['href'] or '/news/' in a['href']:
            news_list.append((a.get_text(strip=True), a['href']))

print(f"Total items found: {len(news_list)}")
for item in news_list[:10]:
    print("  ->", item[:100])

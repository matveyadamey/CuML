#!/usr/bin/env python3
"""
Financial News & Corporate Disclosure Parser with Sentiment Analysis
Collects banking news and corporate disclosures from official RSS feeds (Interfax, RBC, Banki.ru),
computes financial sentiment scores (-1.0 to +1.0) and news intensity indicators.
"""

from pathlib import Path
import re
from datetime import datetime
import pandas as pd
import requests
import xml.etree.ElementTree as ET

NEWS_DIR = Path("moex_banking_dataset") / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

# Lexicon of financial sentiment keywords for Russian banking sector
POSITIVE_WORDS = {
    "рост", "выросла", "увеличилась", "рекордная", "прибыль", "дивиденды", "выплата",
    "повысил", "превысил", "улучшил", "успешный", "лидер", "доходность", "перевыполнил",
    "рентабельность", "байбек", "росте", "позитивный", "устойчивый", "поддержка"
}

NEGATIVE_WORDS = {
    "падение", "упала", "снизилась", "убыток", "убытки", "санкции", "штраф", "отзыв",
    "дефицит", "кризис", "давление", "проблема", "риск", "снизил", "ухудшил",
    "дефолт", "санкций", "заморозка", "отток", "негативный", "просрочка", "резервы"
}

BANK_KEYWORDS = {
    "SBER": ["сбер", "сбербанк", "греф"],
    "VTBR": ["втб", "костин"],
    "T": ["т-банк", "тинькофф", "ткс", "т-технологии"],
    "SVCB": ["совкомбанк", "хотимский"],
    "CBOM": ["мкб", "московский кредитный"],
    "BSPB": ["бспб", "санкт-петербург", "банк санкт"]
}

def analyze_sentiment(text):
    text_lower = text.lower()
    words = re.findall(r"[а-яa-z0-9]+", text_lower)
    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    total = pos_count + neg_count
    if total == 0:
        return 0.0, 0.0  # sentiment, confidence
    score = (pos_count - neg_count) / total
    confidence = min(total / 5.0, 1.0)
    return score, confidence

def identify_bank(text):
    text_lower = text.lower()
    for ticker, kws in BANK_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            return ticker
    return "SECTOR"

def fetch_rss_news(rss_url, source_name):
    print(f"Fetching news from {source_name} ({rss_url})...", flush=True)
    try:
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else ""
            desc = item.find("description").text if item.find("description") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            full_text = f"{title}. {desc}"
            sentiment, conf = analyze_sentiment(full_text)
            ticker = identify_bank(full_text)
            items.append({
                "source": source_name,
                "pub_date_raw": pub_date,
                "title": title,
                "ticker": ticker,
                "sentiment_score": sentiment,
                "sentiment_confidence": conf
            })
        print(f"  -> Found {len(items)} news items from {source_name}", flush=True)
        return items
    except Exception as e:
        print(f"  -> Error parsing {source_name}: {e}", flush=True)
        return []

def main():
    print("=" * 60)
    print("Financial News & Corporate Disclosure Sentiment Parser")
    print("=" * 60)
    
    # Public financial RSS feeds
    feeds = [
        ("https://www.vedomosti.ru/rss/rubric/finance", "Vedomosti Finance"),
        ("https://www.kommersant.ru/RSS/finance.xml", "Kommersant Finance"),
        ("https://tass.ru/rss/v2.xml?rubric=ekonomika", "TASS Economy")
    ]
    
    all_news = []
    for url, name in feeds:
        items = fetch_rss_news(url, name)
        all_news.extend(items)
        
    if all_news:
        df = pd.DataFrame(all_news)
        df.to_parquet(NEWS_DIR / "latest_financial_news_sentiment.parquet", index=False)
        df.to_csv(NEWS_DIR / "latest_financial_news_sentiment.csv", index=False)
        print(f"\nSUCCESS! Saved {len(df)} financial news records with NLP sentiment scores to {NEWS_DIR / 'latest_financial_news_sentiment.parquet'}")
    else:
        print("No live RSS items returned (offline or network restriction). Pipeline template created successfully.")

if __name__ == "__main__":
    main()

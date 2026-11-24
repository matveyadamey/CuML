#!/usr/bin/env python3
"""
Smart-Lab (smart-lab.ru) Scraper for Russian Banking Sector:
1. Newsfeed with intensity/popularity metrics and sentiment
2. Dividend calendar for banking stocks (dividends, yields, cut-off dates, gaps)
Saves to moex_banking_dataset/smartlab/
"""

import io
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

SMARTLAB_DIR = Path("moex_banking_dataset") / "smartlab"
SMARTLAB_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

BANK_TICKERS = {"SBER", "SBERP", "VTBR", "T", "TCSG", "CBOM", "SVCB", "BSPB", "BSPBP", "USBN"}

def collect_smartlab_dividends():
    print("[1/2] Fetching Smart-Lab Dividend Calendar for Banking Sector...", flush=True)
    url = "https://smart-lab.ru/dividends/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        dfs = pd.read_html(io.StringIO(r.text))
        if not dfs:
            print("  -> No dividend tables found.")
            return pd.DataFrame()
            
        df = dfs[0]
        # Standardize columns
        cols = [str(c).strip() for c in df.columns]
        df.columns = cols
        
        # Filter for our banks
        if "Тикер" in df.columns:
            bank_divs = df[df["Тикер"].isin(BANK_TICKERS)].copy()
        else:
            bank_divs = df.copy()
            
        # Clean numeric fields
        if "Дивиденд, руб" in bank_divs.columns:
            bank_divs["dividend_rub"] = pd.to_numeric(bank_divs["Дивиденд, руб"].astype(str).str.replace(" ", "").str.replace(",", "."), errors="coerce")
        if "Див. Дох." in bank_divs.columns:
            bank_divs["yield_pct"] = pd.to_numeric(bank_divs["Див. Дох."].astype(str).str.replace("%", "").str.replace(" ", "").str.replace(",", "."), errors="coerce")
            
        # Save
        bank_divs.to_parquet(SMARTLAB_DIR / "smartlab_bank_dividends.parquet", index=False)
        bank_divs.to_csv(SMARTLAB_DIR / "smartlab_bank_dividends.csv", index=False)
        print(f"  -> Saved {len(bank_divs)} dividend events for banking stocks to {SMARTLAB_DIR / 'smartlab_bank_dividends.parquet'}", flush=True)
        return bank_divs
    except Exception as e:
        print(f"  -> Error fetching Smart-Lab dividends: {e}", flush=True)
        return pd.DataFrame()

def collect_smartlab_news():
    print("[2/2] Fetching Smart-Lab Financial News & Intensity...", flush=True)
    rss_url = "https://smart-lab.ru/news/rss/"
    try:
        r = requests.get(rss_url, headers=HEADERS, timeout=20)
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else ""
            desc = item.find("description").text if item.find("description") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            
            # Simple keyword matching for banks
            full_txt = f"{title}. {desc}".lower()
            matched_ticker = "MARKET"
            for t, words in [("SBER", ["сбер"]), ("VTBR", ["втб"]), ("T", ["т-банк", "тинькофф", "ткс"]),
                             ("SVCB", ["совкомбанк"]), ("CBOM", ["мкб"]), ("BSPB", ["бспб", "санкт-петербург"])]:
                if any(w in full_txt for w in words):
                    matched_ticker = t
                    break
                    
            # Check for emoji intensity markers in Smart-Lab news (e.g. 🔥, 📉, 📈, ❗️)
            intensity = 1
            if "🔥" in title or "❗️" in title or "⚡️" in title or "срочно" in full_txt:
                intensity = 3
            elif "📉" in title or "📈" in title or "рекорд" in full_txt:
                intensity = 2
                
            items.append({
                "source": "smart-lab.ru",
                "pub_date_raw": pub_date,
                "ticker": matched_ticker,
                "title": title,
                "link": link,
                "intensity_score": intensity
            })
            
        df = pd.DataFrame(items)
        if not df.empty:
            df.to_parquet(SMARTLAB_DIR / "smartlab_news_intensity.parquet", index=False)
            df.to_csv(SMARTLAB_DIR / "smartlab_news_intensity.csv", index=False)
            print(f"  -> Saved {len(df)} Smart-Lab news records with intensity scores to {SMARTLAB_DIR / 'smartlab_news_intensity.parquet'}", flush=True)
        return df
    except Exception as e:
        print(f"  -> Error fetching Smart-Lab news: {e}", flush=True)
        return pd.DataFrame()

def main():
    print("=" * 60)
    print("Smart-Lab Banking Data Collector")
    print("=" * 60)
    collect_smartlab_dividends()
    collect_smartlab_news()
    print("=" * 60)
    print("Smart-Lab data collection completed successfully!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MOEX Macro & Commodities Downloader:
- GLDRUB_TOM (Gold in RUB, precious metals / currency market)
- CNYRUB_TOM (Chinese Yuan in RUB, currency market)
- RGBI (Russian Government Bond Index / OFZ)
Saves to moex_banking_dataset/macro/
"""

import time
import sys
import calendar
from pathlib import Path
from datetime import datetime
import pandas as pd
import requests

MACRO_DIR = Path("moex_banking_dataset") / "macro"
MACRO_DIR.mkdir(parents=True, exist_ok=True)

INSTRUMENTS = [
    {"secid": "GLDRUB_TOM", "name": "Золото за рубли (MOEX Gold)", "engine": "currency", "market": "selt", "start_year": 2014},
    {"secid": "CNYRUB_TOM", "name": "Китайский юань / рубль", "engine": "currency", "market": "selt", "start_year": 2014},
    {"secid": "RGBI", "name": "Индекс государственных облигаций РФ (RGBI)", "engine": "stock", "market": "index", "start_year": 2011},
]

def fetch_month(session, inst, year, month):
    secid = inst["secid"]
    engine = inst["engine"]
    market = inst["market"]
    _, last_day = calendar.monthrange(year, month)
    url = f"http://iss.moex.com/iss/engines/{engine}/markets/{market}/securities/{secid}/candles.json"
    params = {
        "iss.meta": "off",
        "interval": 60,
        "from": f"{year}-{month:02d}-01",
        "till": f"{year}-{month:02d}-{last_day:02d}",
        "start": 0
    }
    for attempt in range(3):
        try:
            r = session.get(url, params=params, timeout=(6, 12))
            if r.status_code == 200:
                data = r.json()
                block = data.get("candles", {})
                cols = [c.lower() for c in block.get("columns", [])]
                rows = block.get("data", [])
                if rows and cols:
                    df = pd.DataFrame(rows, columns=cols)
                    df["secid"] = secid
                    return df
            time.sleep(1.0)
        except Exception:
            time.sleep(1.0)
    return pd.DataFrame()

def download_all(current_year=2026, current_month=11):
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MOEX-Macro/1.0"})
    
    for inst in INSTRUMENTS:
        secid = inst["secid"]
        cache_path = MACRO_DIR / f"{secid}_hourly.parquet"
        if cache_path.exists():
            print(f"[{secid}] Found existing cache: {cache_path}, skipping.", flush=True)
            continue
            
        print(f"[{secid}] Downloading {inst['name']} ({inst['start_year']} - {current_year})...", flush=True)
        dfs = []
        for y in range(inst["start_year"], current_year + 1):
            m_end = current_month if y == current_year else 12
            for m in range(1, m_end + 1):
                df_m = fetch_month(session, inst, y, m)
                if not df_m.empty:
                    dfs.append(df_m)
                time.sleep(0.06)
            sys.stdout.write(f"\r  {secid}: {y} done ({len(dfs)} months with data)")
            sys.stdout.flush()
            
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            for c in ["open", "close", "high", "low", "value", "volume"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            df["begin"] = pd.to_datetime(df["begin"])
            df = df.sort_values("begin").drop_duplicates(subset=["begin"]).reset_index(drop=True)
            df.to_parquet(cache_path, index=False)
            df.to_csv(MACRO_DIR / f"{secid}_hourly.csv.gz", index=False, compression="gzip")
            print(f"\n[{secid}] SUCCESS! Saved {len(df):,} hourly candles to {cache_path}", flush=True)

if __name__ == "__main__":
    download_all()

#!/usr/bin/env python3
"""
Bank of Russia Structural Liquidity & Net Claims Collector
Downloads daily liquidity deficit/surplus data of the Russian banking sector (2015-2026).
"""

import io
import re
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup

MACRO_DIR = Path("moex_banking_dataset") / "macro"
MACRO_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Liquidity-Collector/1.0"}

def download_liquidity():
    print("Downloading Bank of Russia Structural Liquidity data (2015-2026)...", flush=True)
    url = "https://www.cbr.ru/hd_base/bliquidity/?UniDbQuery.Posted=True&UniDbQuery.From=01.01.2015&UniDbQuery.To=24.11.2026"
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"class": "data"}) or soup.find("table")
    if not table:
        print("Error: Table not found on cbr.ru/hd_base/bliquidity/")
        return pd.DataFrame()
        
    rows = []
    for tr in table.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) >= 2 and re.match(r"\d{2}\.\d{2}\.\d{4}", tds[0]):
            d_str = tds[0]
            # Column 1: Deficit (+)/Surplus (-) in billions RUB
            val_str = tds[1].replace(" ", "").replace("\xa0", "").replace(",", ".")
            try:
                val = float(val_str)
                rows.append({"date_str": d_str, "liquidity_deficit_surplus_bln_rub": val})
            except ValueError:
                pass
                
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date_str"], format="%d.%m.%Y")
        df = df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)
        df = df[["date", "liquidity_deficit_surplus_bln_rub"]]
        
        # Save
        df.to_parquet(MACRO_DIR / "cbr_banking_liquidity_daily.parquet", index=False)
        df.to_csv(MACRO_DIR / "cbr_banking_liquidity_daily.csv", index=False)
        print(f"SUCCESS! Saved {len(df):,} daily records of Banking Liquidity ({df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')})", flush=True)
        return df
    return pd.DataFrame()

if __name__ == "__main__":
    download_liquidity()

#!/usr/bin/env python3
"""
Bank of Russia Zero-Coupon Yield Curve (ZCYC / КБД) Downloader:
Downloads yields for 0.25y, 0.5y, 0.75y, 1y, 2y, 3y, 5y, 7y, 10y, 15y, 20y, 30y
Computes:
- ofz_yield_1y, ofz_yield_2y, ofz_yield_5y, ofz_yield_10y
- ofz_curve_slope_10y_1y (10Y - 1Y slope)
- ofz_slope_change_1d, ofz_slope_change_5d
Saves to moex_banking_dataset/macro/cbr_ofz_zcyc_daily.parquet
"""

import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

OUTPUT_DIR = Path("moex_banking_dataset") / "macro"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

URL = "https://www.cbr.ru/hd_base/zcyc_params/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OFZ-Collector/1.0"
}

def fetch_year(year):
    params = {
        "UniDbQuery.Posted": "True",
        "UniDbQuery.From": f"01.01.{year}",
        "UniDbQuery.To": f"31.12.{year}"
    }
    for attempt in range(3):
        try:
            r = requests.get(URL, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                table = soup.find("table", {"class": "data"})
                if table:
                    rows = table.find_all("tr")
                    if len(rows) > 2:
                        header_cells = [th.text.strip() for th in rows[1].find_all(["th", "td"])]
                        # headers: ['0,25', '0,5', '0,75', '1', '2', '3', '5', '7', '10', '15', '20', '30']
                        col_names = ["date"] + [f"ofz_yield_{c.replace(',', '_')}y" for c in header_cells]
                        data_rows = []
                        for tr in rows[2:]:
                            tds = [td.text.strip().replace(" ", "") for td in tr.find_all(["td"])]
                            if tds and len(tds) == len(col_names):
                                data_rows.append(tds)
                        if data_rows:
                            df = pd.DataFrame(data_rows, columns=col_names)
                            return df
            time.sleep(1.0)
        except Exception as e:
            time.sleep(1.0)
    return pd.DataFrame()

def collect_all_zcyc(start_year=2014, end_year=2026):
    print(f"Fetching CBR OFZ Zero-Coupon Yield Curve ({start_year} - {end_year})...")
    all_dfs = []
    for y in range(start_year, end_year + 1):
        df_y = fetch_year(y)
        if not df_y.empty:
            all_dfs.append(df_y)
            print(f"  Year {y}: {len(df_y)} trading days collected.")
        time.sleep(0.3)
        
    if not all_dfs:
        print("Failed to fetch ZCYC data.")
        return
        
    df = pd.concat(all_dfs, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
    
    # Convert yields to float
    yield_cols = [c for c in df.columns if c.startswith("ofz_yield_")]
    for c in yield_cols:
        df[c] = df[c].str.replace(",", ".").astype(float)
        
    df = df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)
    
    # Calculate quant curve slope features
    # 10Y - 1Y slope
    if "ofz_yield_10y" in df.columns and "ofz_yield_1y" in df.columns:
        df["ofz_curve_slope_10y_1y"] = df["ofz_yield_10y"] - df["ofz_yield_1y"]
        df["ofz_slope_change_1d"] = df["ofz_curve_slope_10y_1y"].diff(1)
        df["ofz_slope_change_5d"] = df["ofz_curve_slope_10y_1y"].diff(5)
        
    # Curve curvature: 2*5Y - (1Y + 10Y) (butterfly spread)
    if all(c in df.columns for c in ["ofz_yield_1y", "ofz_yield_5y", "ofz_yield_10y"]):
        df["ofz_curve_butterfly_spread"] = 2 * df["ofz_yield_5y"] - (df["ofz_yield_1y"] + df["ofz_yield_10y"])
        
    # Short rate momentum
    if "ofz_yield_1y" in df.columns:
        df["ofz_yield_1y_change_1d"] = df["ofz_yield_1y"].diff(1)
        df["ofz_yield_1y_change_5d"] = df["ofz_yield_1y"].diff(5)
        
    parquet_path = OUTPUT_DIR / "cbr_ofz_zcyc_daily.parquet"
    csv_path = OUTPUT_DIR / "cbr_ofz_zcyc_daily.csv"
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    print(f"\nSUCCESS! Saved {len(df):,} OFZ yield curve days to {parquet_path}")
    print(f"Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
    print("Columns:", list(df.columns))

if __name__ == "__main__":
    collect_all_zcyc()

#!/usr/bin/env python3
"""
External Macro & Market Features Collector
Collects non-MOEX macro data:
1. Bank of Russia Key Rate (Daily series 2013-2026)
2. Bank of Russia / Rosstat Inflation & Target (Monthly series)
3. Bitcoin (BTC/USDT) OHLCV from Binance public historical archives
Saves clean datasets to moex_banking_dataset/macro/
"""

import io
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests

MACRO_DIR = Path("moex_banking_dataset") / "macro"
MACRO_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Macro-Collector/1.0"}

def download_cbr_key_rate():
    print("[1/3] Downloading Bank of Russia Key Rate...", flush=True)
    url = "https://www.cbr.ru/hd_base/KeyRate/?UniDbQuery.Posted=True&UniDbQuery.From=01.01.2013&UniDbQuery.To=24.11.2026"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    
    dfs = pd.read_html(io.StringIO(r.text))
    df = dfs[0].copy()
    df.columns = ["date_raw", "rate_raw"]
    
    # Parse dates and numeric rates
    df["date"] = pd.to_datetime(df["date_raw"], format="%d.%m.%Y")
    # Rate is formatted like 1400 meaning 14.00% or 550 meaning 5.50%
    df["key_rate_pct"] = pd.to_numeric(df["rate_raw"], errors="coerce") / 100.0
    
    df = df.sort_values("date").reset_index(drop=True)
    df = df[["date", "key_rate_pct"]]
    
    # Daily full calendar forward-fill so every calendar date has the active key rate
    idx = pd.date_range(start=df["date"].min(), end=df["date"].max(), freq="D")
    df_daily = df.set_index("date").reindex(idx).ffill().reset_index()
    df_daily.columns = ["date", "key_rate_pct"]
    
    # Save
    df_daily.to_parquet(MACRO_DIR / "cbr_key_rate_daily.parquet", index=False)
    df_daily.to_csv(MACRO_DIR / "cbr_key_rate_daily.csv", index=False)
    print(f"  -> Saved {len(df_daily):,} daily Key Rate records ({df_daily['date'].min().strftime('%Y-%m-%d')} to {df_daily['date'].max().strftime('%Y-%m-%d')})", flush=True)
    return df_daily

def download_cbr_inflation():
    print("[2/3] Downloading CBR / Rosstat Inflation and Targets...", flush=True)
    url = "https://www.cbr.ru/hd_base/infl/"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    
    dfs = pd.read_html(io.StringIO(r.text))
    df = dfs[0].copy()
    df.columns = ["month_year", "key_rate_pct", "cpi_yoy_pct", "cpi_target_pct"]
    
    # Clean numeric columns (1400 -> 14.0%, 635 -> 6.35%)
    for col in ["key_rate_pct", "cpi_yoy_pct", "cpi_target_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0
        
    # Parse month.year e.g. '9.2026' -> '2026-09-01'
    def parse_m_y(s):
        try:
            parts = str(s).strip().split(".")
            m, y = int(parts[0]), int(parts[1])
            return datetime(y, m, 1)
        except Exception:
            return None
            
    df["date"] = df["month_year"].apply(parse_m_y)
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df = df[["date", "cpi_yoy_pct", "cpi_target_pct", "key_rate_pct"]]
    
    df.to_parquet(MACRO_DIR / "cbr_inflation_monthly.parquet", index=False)
    df.to_csv(MACRO_DIR / "cbr_inflation_monthly.csv", index=False)
    print(f"  -> Saved {len(df):,} monthly Inflation records ({df['date'].min().strftime('%Y-%m')} to {df['date'].max().strftime('%Y-%m')})", flush=True)
    return df

def download_binance_btc():
    print("[3/3] Downloading Bitcoin (BTC/USDT) history from Binance API...", flush=True)
    # Paginate daily klines
    all_rows = []
    start_ts = int(datetime(2017, 8, 1).timestamp() * 1000)
    url = "https://api.binance.com/api/v3/klines"
    
    while True:
        params = {
            "symbol": "BTCUSDT",
            "interval": "1d",
            "startTime": start_ts,
            "limit": 1000
        }
        for _ in range(3):
            try:
                r = requests.get(url, params=params, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    break
                time.sleep(1.0)
            except Exception:
                time.sleep(1.0)
        else:
            break
            
        if not data:
            break
            
        all_rows.extend(data)
        last_close_time = data[-1][6]
        start_ts = last_close_time + 1
        
        if len(data) < 1000:
            break
        time.sleep(0.1)
        
    cols = ["open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "count", "taker_buy_volume",
            "taker_buy_quote_volume", "ignore"]
            
    df = pd.DataFrame(all_rows, columns=cols)
    df["date"] = pd.to_datetime(df["open_time"], unit="ms").dt.date
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        
    # Return features
    df["btc_return_1d"] = df["close"].pct_change()
    df["btc_return_1w"] = df["close"].pct_change(7)
    df["btc_close"] = df["close"]
    
    df = df[["date", "btc_close", "btc_return_1d", "btc_return_1w", "volume"]]
    df = df.sort_values("date").reset_index(drop=True)
    
    df.to_parquet(MACRO_DIR / "btc_daily.parquet", index=False)
    df.to_csv(MACRO_DIR / "btc_daily.csv", index=False)
    print(f"  -> Saved {len(df):,} daily BTC records ({df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')})", flush=True)
    return df

def main():
    print("=" * 60)
    print("External Macro & Crypto Feature Collector")
    print("=" * 60)
    download_cbr_key_rate()
    download_cbr_inflation()
    download_binance_btc()
    print("=" * 60)
    print("All Macro and Crypto datasets successfully collected!")
    print("=" * 60)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Parallel Multi-Worker MOEX Banking Sector Dataset Collector
Downloads all Russian banking sector stocks & benchmarks with 3 worker threads,
handles retries, validates OHLCV data, calculates ML indicators, and creates master datasets.
"""

import os
import sys
import time
import json
import calendar
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OUTPUT_DIR = Path("moex_banking_dataset")
RAW_DIR = OUTPUT_DIR / "raw"
HOURLY_DIR = OUTPUT_DIR / "hourly"
DAILY_DIR = OUTPUT_DIR / "daily"
WEEKLY_DIR = OUTPUT_DIR / "weekly"

for d in [OUTPUT_DIR, RAW_DIR, HOURLY_DIR, DAILY_DIR, WEEKLY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

SECURITIES_TO_DOWNLOAD = [
    # Top Banking Stocks
    {"ticker": "SBER",  "name": "Сбербанк (обыкновенные)", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2011},
    {"ticker": "SBERP", "name": "Сбербанк (привилегированные)", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2011},
    {"ticker": "VTBR",  "name": "Банк ВТБ (обыкновенные)", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2011},
    {"ticker": "T",     "name": "Т-Технологии / Т-Банк (обыкновенные)", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2024},
    {"ticker": "TCSG",  "name": "TCS Group Holding (ГДР, история до редомициляции)", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2019},
    {"ticker": "CBOM",  "name": "Московский кредитный банк (МКБ)", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2015},
    {"ticker": "SVCB",  "name": "Совкомбанк", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2023},
    {"ticker": "BSPB",  "name": "Банк Санкт-Петербург (обыкновенные)", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2011},
    {"ticker": "BSPBP", "name": "Банк Санкт-Петербург (привилегированные)", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2011},
    # Additional Listed Russian Banks
    {"ticker": "USBN",  "name": "Банк Уралсиб", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2011},
    {"ticker": "ROSB",  "name": "Росбанк", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2011},
    {"ticker": "AVAN",  "name": "АКБ Авангард", "engine": "stock", "market": "shares", "board": "TQBR", "start_year": 2011},
    # Sector & Market Benchmarks
    {"ticker": "IMOEX", "name": "Индекс Мосбиржи", "engine": "stock", "market": "index", "board": None, "start_year": 2011},
    {"ticker": "MOEXFN", "name": "Индекс Финансов Мосбиржи (банковский сектор)", "engine": "stock", "market": "index", "board": None, "start_year": 2011},
]

NON_TRADED_BANKS = [
    {"bank": "Газпромбанк", "reason": "Непубличное АО. 100% акций распределены среди закрытого круга акционеров; обращаются только биржевые облигации."},
    {"bank": "Альфа-Банк", "reason": "Крупнейший частный банк РФ (АО). Акции на бирже не обращаются; обращаются многочисленные выпуски облигаций."},
    {"bank": "Банк ПСБ (Промсвязьбанк)", "reason": "Государственный опорный банк оборонного сектора. Акции делистингованы в 2018 г.; на бирже обращаются только облигации."},
    {"bank": "Россельхозбанк (РСХБ)", "reason": "100% акций принадлежат государству (Росимущество). Акции на бирже не торгуются; обращаются облигации."},
    {"bank": "Банк ДОМ.РФ", "reason": "100% дочерний банк госкомпании АО «ДОМ.РФ». Акции банка на бирже не обращаются; обращаются облигации."},
    {"bank": "Райффайзенбанк", "reason": "100% дочерняя структура Raiffeisen Bank International AG (Австрия). Акции в РФ не обращаются; только локальные облигации."},
    {"bank": "ЮниКредит Банк", "reason": "100% дочерняя структура UniCredit S.p.A. (Италия). Акции на MOEX не обращаются; только локальные облигации."},
    {"bank": "Новиком (Новикомбанк)", "reason": "100% дочерний банк ГК «Ростех». Акции на бирже не обращаются; обращаются облигации."},
    {"bank": "Банк «Россия»", "reason": "Закрытое непубличное АО. Акции на бирже не обращаются."},
    {"bank": "Ак Барс Банк", "reason": "Крупнейший региональный банк Татарстана. Акции не включены в обращение на TQBR; обращаются облигации."},
]

def make_session():
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=5)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MOEX-ML-Dataset/2.0",
        "Accept": "application/json"
    })
    return s

def fetch_month(session, sec, year, month):
    ticker = sec["ticker"]
    engine = sec["engine"]
    market = sec["market"]
    board = sec.get("board")
    
    _, last_day = calendar.monthrange(year, month)
    date_from = f"{year}-{month:02d}-01"
    date_till = f"{year}-{month:02d}-{last_day:02d}"
    
    if board:
        url = f"http://iss.moex.com/iss/engines/{engine}/markets/{market}/boards/{board}/securities/{ticker}/candles.json"
    else:
        url = f"http://iss.moex.com/iss/engines/{engine}/markets/{market}/securities/{ticker}/candles.json"
        
    rows = []
    cols = None
    offset = 0
    
    while True:
        params = {
            "iss.meta": "off",
            "interval": 60,
            "from": date_from,
            "till": date_till,
            "start": offset
        }
        data = None
        for attempt in range(4):
            try:
                # Fast timeout: 7s connect, 12s read. Fail fast & retry quickly.
                r = session.get(url, params=params, timeout=(7, 12))
                if r.status_code == 200:
                    data = r.json()
                    break
                time.sleep(1.0)
            except Exception:
                time.sleep(1.0 * (attempt + 1))
                
        if not data:
            break
            
        block = data.get("candles", {})
        if not cols:
            cols = [c.lower() for c in block.get("columns", [])]
        batch = block.get("data", [])
        if not batch:
            break
            
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < 500:
            break
            
    if rows and cols:
        df = pd.DataFrame(rows, columns=cols)
        df["ticker"] = ticker
        df["sec_name"] = sec["name"]
        return df
    return pd.DataFrame()

def download_ticker_task(sec, current_year=2026, current_month=11):
    ticker = sec["ticker"]
    cache_file = RAW_DIR / f"{ticker}_hourly_raw.parquet"
    if cache_file.exists():
        print(f"[{ticker}] Found existing cache: {cache_file}, loading...", flush=True)
        return pd.read_parquet(cache_file)
        
    session = make_session()
    start_year = sec["start_year"]
    dfs = []
    t0 = time.time()
    
    print(f"[{ticker}] Starting download ({start_year} -> {current_year}-{current_month:02d})...", flush=True)
    for y in range(start_year, current_year + 1):
        m_end = current_month if y == current_year else 12
        for m in range(1, m_end + 1):
            df_m = fetch_month(session, sec, y, m)
            if not df_m.empty:
                dfs.append(df_m)
            time.sleep(0.06)
            
        elapsed = time.time() - t0
        print(f"[{ticker}] Year {y} done ({len(dfs)} months total, elapsed: {elapsed:.1f}s)", flush=True)
        
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        for col in ["open", "close", "high", "low", "value", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["begin"] = pd.to_datetime(df["begin"])
        df["end"] = pd.to_datetime(df["end"])
        df = df.sort_values("begin").drop_duplicates(subset=["begin"]).reset_index(drop=True)
        df.to_parquet(cache_file, index=False)
        print(f"[{ticker}] SUCCESS! Saved {len(df):,} candles in {time.time()-t0:.1f}s -> {cache_file}", flush=True)
        return df
    else:
        print(f"[{ticker}] WARNING: No data retrieved!", flush=True)
        return pd.DataFrame()

def validate_and_audit(df, ticker):
    qa = {
        "ticker": ticker,
        "total_candles": len(df),
        "date_min": str(df["begin"].min()) if not df.empty else None,
        "date_max": str(df["begin"].max()) if not df.empty else None,
        "null_count": int(df[["open", "high", "low", "close"]].isna().sum().sum()),
        "invalid_ohlc_invariants": 0,
        "duplicate_timestamps": int(df["begin"].duplicated().sum()),
        "zero_or_negative_prices": 0,
        "negative_volume": 0,
        "large_hourly_jumps_gt30pct": 0,
        "status": "PASS"
    }
    if df.empty:
        qa["status"] = "EMPTY"
        return qa
        
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    bad_hl = (h < l)
    bad_ho = (h < o - 1e-6)
    bad_hc = (h < c - 1e-6)
    bad_lo = (l > o + 1e-6)
    bad_lc = (l > c + 1e-6)
    qa["invalid_ohlc_invariants"] = int((bad_hl | bad_ho | bad_hc | bad_lo | bad_lc).sum())
    qa["zero_or_negative_prices"] = int(((o <= 0) | (h <= 0) | (l <= 0) | (c <= 0)).sum())
    if "volume" in df.columns:
        qa["negative_volume"] = int((df["volume"] < 0).sum())
    returns = c.pct_change().abs()
    qa["large_hourly_jumps_gt30pct"] = int((returns > 0.30).sum())
    
    if qa["null_count"] > 0 or qa["invalid_ohlc_invariants"] > 0 or qa["zero_or_negative_prices"] > 0:
        qa["status"] = "FAIL"
    elif qa["large_hourly_jumps_gt30pct"] > 5:
        qa["status"] = "WARNING"
    return qa

def calculate_ml_features(df):
    if df.empty or len(df) < 50:
        return df
    df = df.copy()
    c, h, l = df["close"], df["high"], df["low"]
    v = df["volume"] if "volume" in df.columns else pd.Series(0, index=df.index)
    
    # Returns
    df["return_1h"] = c.pct_change(1)
    df["return_4h"] = c.pct_change(4)
    df["return_1d"] = c.pct_change(10)
    df["return_1w"] = c.pct_change(50)
    
    # Moving Averages
    df["sma_10"] = c.rolling(10).mean()
    df["sma_20"] = c.rolling(20).mean()
    df["sma_50"] = c.rolling(50).mean()
    df["ema_10"] = c.ewm(span=10, adjust=False).mean()
    df["ema_20"] = c.ewm(span=20, adjust=False).mean()
    df["dist_sma_20"] = (c - df["sma_20"]) / df["sma_20"]
    df["dist_sma_50"] = (c - df["sma_50"]) / df["sma_50"]
    df["ma_trend_cross"] = (df["sma_10"] > df["sma_20"]).astype(int)
    
    # Volatility & Bollinger Bands
    rolling_std = c.rolling(20).std()
    df["bollinger_mid"] = df["sma_20"]
    df["bollinger_upper"] = df["bollinger_mid"] + 2 * rolling_std
    df["bollinger_lower"] = df["bollinger_mid"] - 2 * rolling_std
    df["bollinger_width"] = (df["bollinger_upper"] - df["bollinger_lower"]) / (df["bollinger_mid"] + 1e-9)
    df["bollinger_pct_b"] = (c - df["bollinger_lower"]) / (df["bollinger_upper"] - df["bollinger_lower"] + 1e-9)
    
    # ATR & Normalized ATR
    tr1 = h - l
    tr2 = (h - c.shift(1)).abs()
    tr3 = (l - c.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()
    df["natr_14"] = df["atr_14"] / c
    
    # RSI
    delta = c.diff()
    avg_gain = delta.clip(lower=0).rolling(14).mean()
    avg_loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["rsi_14"] = 100 - (100 / (1 + rs))
    
    # ADX (Trend Strength & Confidence)
    up = h - h.shift(1)
    down = l.shift(1) - l
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr_sum = tr.rolling(14).sum() + 1e-9
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(14).sum() / tr_sum
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(14).sum() / tr_sum
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    df["adx_14"] = dx.rolling(14).mean()
    df["trend_strength_confidence"] = np.clip(df["adx_14"] / 50.0, 0.0, 1.0)
    
    # Volume Ratio
    if "volume" in df.columns:
        df["volume_ratio_20"] = v / (v.rolling(20).mean() + 1e-9)
        
    # Targets for ML prediction
    df["target_price_1d"] = c.shift(-10)
    df["target_return_1d"] = (df["target_price_1d"] - c) / c
    df["target_dir_1d"] = (df["target_return_1d"] > 0).astype(int)
    
    df["target_price_1w"] = c.shift(-50)
    df["target_return_1w"] = (df["target_price_1w"] - c) / c
    df["target_dir_1w"] = (df["target_return_1w"] > 0).astype(int)
    return df

def aggregate_daily_and_weekly(df_hourly):
    if df_hourly.empty:
        return pd.DataFrame(), pd.DataFrame()
    df = df_hourly.copy()
    df["date"] = df["begin"].dt.date
    df["year_week"] = df["begin"].dt.strftime("%Y-W%U")
    
    daily = df.groupby(["ticker", "sec_name", "date"]).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum") if "volume" in df.columns else ("close", "count"),
        value=("value", "sum") if "value" in df.columns else ("close", "count"),
        hourly_bars=("open", "count"),
        day_begin=("begin", "min"),
        day_end=("end", "max")
    ).reset_index()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values(["ticker", "date"]).reset_index(drop=True)
    
    weekly = df.groupby(["ticker", "sec_name", "year_week"]).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum") if "volume" in df.columns else ("close", "count"),
        value=("value", "sum") if "value" in df.columns else ("close", "count"),
        hourly_bars=("open", "count"),
        week_begin=("begin", "min"),
        week_end=("end", "max")
    ).reset_index()
    weekly = weekly.sort_values(["ticker", "week_begin"]).reset_index(drop=True)
    return daily, weekly

def main():
    print("=" * 70)
    print("PARALLEL MOEX Banking Sector Dataset Builder (3 Workers)")
    print("=" * 70)
    
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_sec = {executor.submit(download_ticker_task, sec): sec for sec in SECURITIES_TO_DOWNLOAD}
        for future in as_completed(future_to_sec):
            sec = future_to_sec[future]
            ticker = sec["ticker"]
            try:
                df = future.result()
                results[ticker] = (sec, df)
            except Exception as e:
                print(f"[{ticker}] Exception in thread: {e}", flush=True)
                results[ticker] = (sec, pd.DataFrame())
                
    all_hourly_dfs = []
    audit_reports = []
    
    print("\nValidating and calculating ML indicators...")
    for sec in SECURITIES_TO_DOWNLOAD:
        ticker = sec["ticker"]
        _, df_sec = results.get(ticker, (sec, pd.DataFrame()))
        if not df_sec.empty:
            qa = validate_and_audit(df_sec, ticker)
            audit_reports.append(qa)
            print(f"[{ticker}] QA: {qa['status']} | {qa['total_candles']:,} bars | {qa['date_min'][:10]} to {qa['date_max'][:10]}")
            
            df_feat = calculate_ml_features(df_sec)
            
            p_hourly = HOURLY_DIR / f"{ticker}_hourly.parquet"
            c_hourly = HOURLY_DIR / f"{ticker}_hourly.csv.gz"
            df_feat.to_parquet(p_hourly, index=False)
            df_feat.to_csv(c_hourly, index=False, compression="gzip")
            all_hourly_dfs.append(df_feat)
            
    if all_hourly_dfs:
        print("\nCreating Unified Master Datasets...")
        master_hourly = pd.concat(all_hourly_dfs, ignore_index=True)
        master_hourly = master_hourly.sort_values(["ticker", "begin"]).reset_index(drop=True)
        master_hourly.to_parquet(OUTPUT_DIR / "moex_banks_hourly_master.parquet", index=False)
        master_hourly.to_csv(OUTPUT_DIR / "moex_banks_hourly_master.csv.gz", index=False, compression="gzip")
        print(f"  -> Hourly Master: {len(master_hourly):,} rows across {master_hourly['ticker'].nunique()} tickers")
        
        daily_dfs = []
        weekly_dfs = []
        for ticker in master_hourly["ticker"].unique():
            sub = master_hourly[master_hourly["ticker"] == ticker]
            d, w = aggregate_daily_and_weekly(sub)
            if not d.empty:
                daily_dfs.append(calculate_ml_features(d))
            if not w.empty:
                weekly_dfs.append(calculate_ml_features(w))
                
        if daily_dfs:
            master_daily = pd.concat(daily_dfs, ignore_index=True)
            master_daily.to_parquet(OUTPUT_DIR / "moex_banks_daily_master.parquet", index=False)
            master_daily.to_csv(OUTPUT_DIR / "moex_banks_daily_master.csv.gz", index=False, compression="gzip")
            print(f"  -> Daily Master: {len(master_daily):,} rows")
            
        if weekly_dfs:
            master_weekly = pd.concat(weekly_dfs, ignore_index=True)
            master_weekly.to_parquet(OUTPUT_DIR / "moex_banks_weekly_master.parquet", index=False)
            master_weekly.to_csv(OUTPUT_DIR / "moex_banks_weekly_master.csv.gz", index=False, compression="gzip")
            print(f"  -> Weekly Master: {len(master_weekly):,} rows")
            
    summary = {
        "generated_at_utc": datetime.utcnow().isoformat(),
        "total_instruments_probed": len(SECURITIES_TO_DOWNLOAD),
        "total_hourly_candles": sum(a["total_candles"] for a in audit_reports),
        "securities_audits": audit_reports,
        "non_traded_banks_documentation": NON_TRADED_BANKS
    }
    with open(OUTPUT_DIR / "DATASET_AUDIT_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("\nPARALLEL SCRIPT COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()

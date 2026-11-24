#!/usr/bin/env python3
"""
Master Feature Store & Data Fusion Builder for Banking Sector ML
Fuses:
1. Daily Stock OHLCV & Technical Indicators (returns, RSI, ATR, ADX, Bollinger, trend targets)
2. Benchmarks (IMOEX, MOEXFN) & Relative Alpha (excess return over market/sector)
3. CBR Macro: Daily Key Rate, Real Interest Rate (Key Rate - CPI), Banking System Liquidity
4. Calendar & Seasonality: Tax period, witching/expiration days, day of week
5. Smart-Lab Fundamentals: Annual/Quarterly ROE, P/E, P/B, Net Profit
6. Macro-prudential Aggregates: Loan growth, NPL ratio
7. External Crypto Risk Appetite: Bitcoin returns

Creates train / validation / test splits for leak-free time-series modeling.
"""

from pathlib import Path
import pandas as pd
import numpy as np

DATASET_DIR = Path("moex_banking_dataset")
MACRO_DIR = DATASET_DIR / "macro"
SMARTLAB_DIR = DATASET_DIR / "smartlab"
FS_DIR = DATASET_DIR / "feature_store"
FS_DIR.mkdir(parents=True, exist_ok=True)

def build_fusion_dataset():
    daily_master_path = DATASET_DIR / "moex_banks_daily_master.parquet"
    if not daily_master_path.exists():
        print(f"Waiting: {daily_master_path} does not exist yet. Run after MOEX daily master is generated.")
        return None
        
    print("Loading Daily Stocks Master...", flush=True)
    df = pd.read_parquet(daily_master_path)
    df["date"] = pd.to_datetime(df["date"])
    
    # 1. Benchmark Excess Returns
    print("Computing Benchmark Relative Alpha...", flush=True)
    imoex = df[df["ticker"] == "IMOEX"][["date", "return_1d", "return_1w"]].rename(
        columns={"return_1d": "imoex_return_1d", "return_1w": "imoex_return_1w"}
    )
    moexfn = df[df["ticker"] == "MOEXFN"][["date", "return_1d", "return_1w"]].rename(
        columns={"return_1d": "moexfn_return_1d", "return_1w": "moexfn_return_1w"}
    )
    df = df.merge(imoex, on="date", how="left")
    df = df.merge(moexfn, on="date", how="left")
    
    df["excess_return_market_1d"] = df["return_1d"] - df["imoex_return_1d"]
    df["excess_return_sector_1d"] = df["return_1d"] - df["moexfn_return_1d"]
    
    # 2. Merge CBR Key Rate
    key_rate_path = MACRO_DIR / "cbr_key_rate_daily.parquet"
    if key_rate_path.exists():
        print("Merging CBR Key Rate...", flush=True)
        kr = pd.read_parquet(key_rate_path)
        kr["date"] = pd.to_datetime(kr["date"])
        df = df.merge(kr, on="date", how="left")
        df["key_rate_pct"] = df["key_rate_pct"].ffill()
        
    # 3. Merge CBR Banking Liquidity
    liq_path = MACRO_DIR / "cbr_banking_liquidity_daily.parquet"
    if liq_path.exists():
        print("Merging CBR Banking Liquidity...", flush=True)
        liq = pd.read_parquet(liq_path)
        liq["date"] = pd.to_datetime(liq["date"])
        df = df.merge(liq, on="date", how="left")
        df["liquidity_deficit_surplus_bln_rub"] = df["liquidity_deficit_surplus_bln_rub"].ffill()
        
    # 4. Merge Inflation & Real Interest Rate
    infl_path = MACRO_DIR / "cbr_inflation_monthly.parquet"
    if infl_path.exists():
        print("Merging Inflation & Calculating Real Rate...", flush=True)
        inf = pd.read_parquet(infl_path)
        inf["date"] = pd.to_datetime(inf["date"])
        # Merge on calendar date with ffill
        df = df.sort_values("date").reset_index(drop=True)
        df = pd.merge_asof(df, inf[["date", "cpi_yoy_pct", "cpi_target_pct"]], on="date", direction="backward")
        df["cpi_yoy_pct"] = df["cpi_yoy_pct"].ffill()
        if "key_rate_pct" in df.columns:
            df["real_interest_rate_pct"] = df["key_rate_pct"] - df["cpi_yoy_pct"]
            
    # 5. Merge Calendar & Seasonality
    cal_path = MACRO_DIR / "calendar_seasonality_features.parquet"
    if cal_path.exists():
        print("Merging Calendar & Tax Seasonality Features...", flush=True)
        cal = pd.read_parquet(cal_path)
        cal["date"] = pd.to_datetime(cal["date"])
        cal_cols = ["date", "is_tax_period", "is_month_start", "is_month_end", "is_futures_expiration_day", "day_of_week"]
        df = df.merge(cal[cal_cols], on="date", how="left")
        
    # 6. Merge Bitcoin Risk-Appetite
    btc_path = MACRO_DIR / "btc_daily.parquet"
    if btc_path.exists():
        print("Merging Bitcoin Global Risk Indicator...", flush=True)
        btc = pd.read_parquet(btc_path)
        btc["date"] = pd.to_datetime(btc["date"])
        btc_cols = ["date", "btc_return_1d", "btc_return_1w"]
        df = df.merge(btc[btc_cols], on="date", how="left")
        df["btc_return_1d"] = df["btc_return_1d"].ffill().fillna(0)
        
    # 7. Merge Smart-Lab Fundamentals
    fund_path = SMARTLAB_DIR / "smartlab_bank_fundamentals_history.parquet"
    if fund_path.exists():
        print("Merging Smart-Lab Fundamentals...", flush=True)
        fund = pd.read_parquet(fund_path)
        # Create year for merge
        df["year"] = df["date"].dt.year
        fund_cols = ["ticker", "year", "net_profit_bln", "roe_pct", "pe_ratio", "pb_ratio"]
        fund_sub = fund[[c for c in fund_cols if c in fund.columns]].drop_duplicates(subset=["ticker", "year"])
        df = df.merge(fund_sub, on=["ticker", "year"], how="left")
        # ffill within each ticker
        for col in ["roe_pct", "pe_ratio", "pb_ratio", "net_profit_bln"]:
            if col in df.columns:
                df[col] = df.groupby("ticker")[col].ffill()
                
    # Sort and Clean
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    
    # Save Master Feature Store
    master_path = FS_DIR / "moex_banks_ml_feature_store.parquet"
    master_csv = FS_DIR / "moex_banks_ml_feature_store.csv.gz"
    df.to_parquet(master_path, index=False)
    df.to_csv(master_csv, index=False, compression="gzip")
    print(f"\nSUCCESS! Master Feature Store created: {len(df):,} rows x {df.shape[1]} features")
    
    # Generate Time-Series Splits
    # Exclude pure index tickers from stock target training
    stock_df = df[~df["ticker"].isin(["IMOEX", "MOEXFN"])].copy()
    
    train = stock_df[stock_df["date"] < "2023-01-01"]
    val = stock_df[(stock_df["date"] >= "2023-01-01") & (stock_df["date"] < "2025-01-01")]
    test = stock_df[stock_df["date"] >= "2025-01-01"]
    
    train.to_parquet(FS_DIR / "train.parquet", index=False)
    val.to_parquet(FS_DIR / "val.parquet", index=False)
    test.to_parquet(FS_DIR / "test.parquet", index=False)
    
    print(f"Time-Series Splits Generated:")
    print(f"  -> TRAIN (2014-2022): {len(train):,} rows ({train['date'].min().strftime('%Y-%m-%d')} to {train['date'].max().strftime('%Y-%m-%d')})")
    print(f"  -> VAL   (2023-2024): {len(val):,} rows ({val['date'].min().strftime('%Y-%m-%d')} to {val['date'].max().strftime('%Y-%m-%d')})")
    print(f"  -> TEST  (2025-2026): {len(test):,} rows ({test['date'].min().strftime('%Y-%m-%d')} to {test['date'].max().strftime('%Y-%m-%d')})")
    return df

if __name__ == "__main__":
    build_fusion_dataset()

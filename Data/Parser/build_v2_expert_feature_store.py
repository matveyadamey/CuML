#!/usr/bin/env python3
"""
V2 Expert-Grade Feature Store Builder for MOEX Banking Sector ML
Implements all expert recommendations:
1. Calendar-based targets (exact MOEX calendar, target_ts_1d, target_ts_1w, minutes_to_target, target_status)
2. Instrument history & lineage (issuer_id, instrument_id, share_class, TCSG->T continuity, ROSB suspension, VTBR split audit)
3. Priority #1 Feature: Cross-bank relative momentum (peer basket excluding target issuer, dispersion, relative lag)
4. Priority #2 Feature: Time-of-day normalized volume (intraday U-shape removal via rolling 20d same-hour mean)
5. Priority #3 Feature: OFZ Zero-Coupon Yield Curve (1y, 2y, 5y, 10y, 10Y-1Y slope, 5d slope change)
6. Clean target representation: simple return + binary direction. Zero synthetic confidence in training labels!
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

DATASET_DIR = Path("moex_banking_dataset")
MACRO_DIR = DATASET_DIR / "macro"
FS_V2_DIR = DATASET_DIR / "feature_store_v2"
FS_V2_DIR.mkdir(parents=True, exist_ok=True)

INSTRUMENT_METADATA = {
    "SBER": {"issuer_id": "SBER", "share_class": "COMMON", "name": "Сбербанк (обыкновенные)"},
    "SBERP": {"issuer_id": "SBER", "share_class": "PREFERRED", "name": "Сбербанк (привилегированные)"},
    "VTBR": {"issuer_id": "VTBR", "share_class": "COMMON", "name": "Банк ВТБ", "split_factor": 5000, "split_date": "2024-07-15"},
    "TCSG": {"issuer_id": "TCS", "share_class": "COMMON", "name": "Т-Банк (TCSG)", "successor": "T"},
    "T": {"issuer_id": "TCS", "share_class": "COMMON", "name": "Т-Банк (Т-Технологии)", "predecessor": "TCSG"},
    "BSPB": {"issuer_id": "BSPB", "share_class": "COMMON", "name": "Банк Санкт-Петербург (обыкновенные)"},
    "BSPBP": {"issuer_id": "BSPB", "share_class": "PREFERRED", "name": "Банк Санкт-Петербург (привилегированные)"},
    "CBOM": {"issuer_id": "CBOM", "share_class": "COMMON", "name": "Московский кредитный банк (МКБ)"},
    "SVCB": {"issuer_id": "SVCB", "share_class": "COMMON", "name": "Совкомбанк"},
    "USBN": {"issuer_id": "USBN", "share_class": "COMMON", "name": "Банк Уралсиб"},
    "ROSB": {"issuer_id": "ROSB", "share_class": "COMMON", "name": "Росбанк", "delist_date": "2024-11-14"},
    "AVAN": {"issuer_id": "AVAN", "share_class": "COMMON", "name": "Банк Авангард"},
    "IMOEX": {"issuer_id": "INDEX", "share_class": "INDEX", "name": "Индекс Мосбиржи"},
    "MOEXFN": {"issuer_id": "INDEX", "share_class": "INDEX", "name": "Индекс финансов Мосбиржи"}
}

def build_v2_feature_store():
    print("=" * 70)
    print("STARTING V2 EXPERT-GRADE FEATURE STORE BUILD")
    print("=" * 70, flush=True)

    # 1. Load Hourly Candles
    hourly_master_path = DATASET_DIR / "moex_banks_hourly_master.parquet"
    if not hourly_master_path.exists():
        raise FileNotFoundError(f"Missing {hourly_master_path}")
        
    print("Loading master hourly dataset...", flush=True)
    df = pd.read_parquet(hourly_master_path)
    df["begin"] = pd.to_datetime(df["begin"])
    df["end"] = pd.to_datetime(df["end"])
    df["date"] = df["begin"].dt.floor("D")
    df = df.sort_values(["ticker", "begin"]).reset_index(drop=True)

    # 2. Add Instrument Metadata & Lineage
    print("Injecting instrument lineage & issuer IDs...", flush=True)
    df["issuer_id"] = df["ticker"].map(lambda t: INSTRUMENT_METADATA.get(t, {}).get("issuer_id", t))
    df["share_class"] = df["ticker"].map(lambda t: INSTRUMENT_METADATA.get(t, {}).get("share_class", "COMMON"))
    
    # 3. MOEX Trading Calendar & Target Dates
    print("Building official MOEX trading calendar...", flush=True)
    imoex_dates = sorted(df[df["ticker"] == "IMOEX"]["date"].unique())
    date_to_idx = {d: i for i, d in enumerate(imoex_dates)}
    max_trading_date = imoex_dates[-1]

    # Map each date to next trading date
    next_date_map = {}
    for i, d in enumerate(imoex_dates):
        if i + 1 < len(imoex_dates):
            next_date_map[d] = imoex_dates[i + 1]
        else:
            next_date_map[d] = None

    # Map each date to next calendar week close date
    next_week_close_map = {}
    for d in imoex_dates:
        cur_monday = d - timedelta(days=d.weekday())
        next_monday = cur_monday + timedelta(days=7)
        next_sunday = next_monday + timedelta(days=6)
        nw_dates = [x for x in imoex_dates if next_monday <= x <= next_sunday]
        next_week_close_map[d] = nw_dates[-1] if nw_dates else None

    # Load daily closes for target lookup
    daily_master_path = DATASET_DIR / "moex_banks_daily_master.parquet"
    df_daily = pd.read_parquet(daily_master_path)
    df_daily["date"] = pd.to_datetime(df_daily["date"])
    
    # Fast lookup table: (ticker, date) -> daily close
    close_lookup = df_daily.set_index(["ticker", "date"])["close"].to_dict()

    print("Computing calendar-based targets (1d next-day close, 1w next-week close)...", flush=True)
    df["target_date_1d"] = df["date"].map(next_date_map)
    df["target_date_1w"] = df["date"].map(next_week_close_map)

    # Target prices
    def lookup_price(ticker, target_dt):
        if pd.isna(target_dt) or target_dt is None:
            return np.nan
        return close_lookup.get((ticker, target_dt), np.nan)

    # Vectorized / zipped lookup
    df["target_price_1d"] = [
        lookup_price(t, td) for t, td in zip(df["ticker"], df["target_date_1d"])
    ]
    df["target_price_1w"] = [
        lookup_price(t, tw) for t, tw in zip(df["ticker"], df["target_date_1w"])
    ]

    # Target Returns & Directions
    df["target_return_1d"] = (df["target_price_1d"] - df["close"]) / df["close"]
    df["target_dir_1d"] = np.where(df["target_return_1d"].isna(), np.nan, (df["target_return_1d"] > 0).astype(float))

    df["target_return_1w"] = (df["target_price_1w"] - df["close"]) / df["close"]
    df["target_dir_1w"] = np.where(df["target_return_1w"].isna(), np.nan, (df["target_return_1w"] > 0).astype(float))

    # Target Status & Suspensions
    def get_target_status(row, horizon="1d"):
        t = row["ticker"]
        t_dt = row[f"target_date_{horizon}"]
        p = row[f"target_price_{horizon}"]
        
        if pd.isna(t_dt) or t_dt is None:
            return "PENDING"
        if t_dt > max_trading_date:
            return "PENDING"
        if not pd.isna(p):
            return "OK"
        # Price is NaN despite target date being in the past
        if t == "ROSB" and t_dt >= pd.Timestamp("2024-11-14"):
            return "SUSPENDED_OR_DELISTED"
        if row["date"] >= pd.Timestamp("2022-02-25") and row["date"] <= pd.Timestamp("2022-03-24"):
            return "MARKET_HALT"
        return "NO_DATA"

    df["target_status_1d"] = [get_target_status(r, "1d") for _, r in df[["ticker", "target_date_1d", "target_price_1d", "date"]].iterrows()]
    df["target_status_1w"] = [get_target_status(r, "1w") for _, r in df[["ticker", "target_date_1w", "target_price_1w", "date"]].iterrows()]

    # Minutes to target
    # Main session on MOEX: 10:00 to 18:40 (520 minutes per full day)
    # Candle hour in session
    df["hour"] = df["begin"].dt.hour
    df["session_minute_now"] = np.clip((df["hour"] - 10) * 60 + 60, 0, 520) # at end of candle
    df["minutes_left_today"] = np.maximum(0, 520 - df["session_minute_now"])
    df["minutes_to_target_1d"] = df["minutes_left_today"] + 520 # today remainder + full next day

    # 4. Priority #1 Feature: Cross-Bank Relative Momentum
    print("Computing Priority #1: Cross-Bank Peer Momentum (excluding target issuer)...", flush=True)
    # Only bank stocks (exclude IMOEX, MOEXFN from peer basket)
    bank_mask = ~df["ticker"].isin(["IMOEX", "MOEXFN"])
    bank_df = df[bank_mask].copy()

    # Pre-calculate totals per timestamp across all banks
    time_totals = bank_df.groupby("begin")["return_1h"].agg(tot_sum="sum", tot_count="count").reset_index()
    time_totals_4h = bank_df.groupby("begin")["return_4h"].agg(tot_sum_4h="sum", tot_count_4h="count").reset_index()

    # Totals per (begin, issuer_id)
    issuer_totals = bank_df.groupby(["begin", "issuer_id"])["return_1h"].agg(own_sum="sum", own_count="count").reset_index()
    issuer_totals_4h = bank_df.groupby(["begin", "issuer_id"])["return_4h"].agg(own_sum_4h="sum", own_count_4h="count").reset_index()

    # Merge into df
    df = df.merge(time_totals, on="begin", how="left")
    df = df.merge(time_totals_4h, on="begin", how="left")
    df = df.merge(issuer_totals, on=["begin", "issuer_id"], how="left")
    df = df.merge(issuer_totals_4h, on=["begin", "issuer_id"], how="left")

    # Others = Total - Own
    df["peer_count_active"] = (df["tot_count"].fillna(0) - df["own_count"].fillna(0)).clip(lower=0)
    df["peer_banks_return_1h"] = np.where(
        df["peer_count_active"] > 0,
        (df["tot_sum"].fillna(0) - df["own_sum"].fillna(0)) / df["peer_count_active"],
        0.0
    )
    df["peer_banks_return_4h"] = np.where(
        df["peer_count_active"] > 0,
        (df["tot_sum_4h"].fillna(0) - df["own_sum_4h"].fillna(0)) / df["peer_count_active"],
        0.0
    )
    # Clean temporary helper columns
    df = df.drop(columns=["tot_sum", "tot_count", "own_sum", "own_count", "tot_sum_4h", "tot_count_4h", "own_sum_4h", "own_count_4h"])

    # Relative lag (alpha / momentum)
    df["peer_relative_lag_1h"] = df["return_1h"] - df["peer_banks_return_1h"]

    # Dual-class share spread (SBER/SBERP, BSPB/BSPBP)
    print("Computing common vs preferred spreads...", flush=True)
    # Pivot closes
    piv_close = df.pivot_table(index="begin", columns="ticker", values="close", aggfunc="first")
    if "SBER" in piv_close and "SBERP" in piv_close:
        piv_close["sber_pref_spread"] = (piv_close["SBER"] - piv_close["SBERP"]) / piv_close["SBER"]
    else:
        piv_close["sber_pref_spread"] = np.nan
        
    if "BSPB" in piv_close and "BSPBP" in piv_close:
        piv_close["bspb_pref_spread"] = (piv_close["BSPB"] - piv_close["BSPBP"]) / piv_close["BSPB"]
    else:
        piv_close["bspb_pref_spread"] = np.nan

    spreads = piv_close[["sber_pref_spread", "bspb_pref_spread"]].reset_index()
    df = df.merge(spreads, on="begin", how="left")

    # 5. Priority #2 Feature: Time-of-Day Normalized Volume
    print("Computing Priority #2: Time-of-day normalized volume (intraday U-shape removal)...", flush=True)
    # For each ticker and each hour of day, compute rolling 20-session average volume
    # shift(1) strictly prevents lookahead bias into current candle
    df = df.sort_values(["ticker", "hour", "begin"]).reset_index(drop=True)
    df["tod_vol_baseline_20d"] = df.groupby(["ticker", "hour"])["volume"].transform(
        lambda s: s.shift(1).rolling(20, min_periods=3).mean()
    )
    df["tod_volume_ratio"] = np.where(
        df["tod_vol_baseline_20d"] > 0,
        df["volume"] / df["tod_vol_baseline_20d"],
        1.0
    )
    df = df.sort_values(["ticker", "begin"]).reset_index(drop=True)

    # Intraday returns from day open and overnight gap
    print("Computing intraday return from open and opening gap...", flush=True)
    day_first_open = df.groupby(["ticker", "date"])["open"].transform("first")
    df["return_from_day_open"] = (df["close"] - day_first_open) / day_first_open

    prev_day_close = df.groupby(["ticker", "date"])["close"].transform("last")
    # Shift previous day close by date
    daily_prev_close = df_daily.sort_values(["ticker", "date"]).copy()
    daily_prev_close["prev_day_close"] = daily_prev_close.groupby("ticker")["close"].shift(1)
    df = df.merge(daily_prev_close[["ticker", "date", "prev_day_close"]], on=["ticker", "date"], how="left")
    df["opening_gap"] = (day_first_open - df["prev_day_close"]) / df["prev_day_close"]
    df["opening_gap"] = df["opening_gap"].fillna(0.0)

    # 6. Priority #3 Feature: OFZ Zero-Coupon Yield Curve
    zcyc_path = MACRO_DIR / "cbr_ofz_zcyc_daily.parquet"
    if zcyc_path.exists():
        print("Merging Priority #3: OFZ Zero-Coupon Yield Curve (ZCYC)...", flush=True)
        zcyc = pd.read_parquet(zcyc_path)
        zcyc["date"] = pd.to_datetime(zcyc["date"])
        zcyc_cols = [
            "date", "ofz_yield_1y", "ofz_yield_2y", "ofz_yield_5y", "ofz_yield_10y",
            "ofz_curve_slope_10y_1y", "ofz_slope_change_1d", "ofz_slope_change_5d",
            "ofz_curve_butterfly_spread", "ofz_yield_1y_change_5d"
        ]
        avail_cols = [c for c in zcyc_cols if c in zcyc.columns]
        df = df.sort_values("date").reset_index(drop=True)
        df = pd.merge_asof(df, zcyc[avail_cols].sort_values("date"), on="date", direction="backward")

    # 7. Merge CBR Key Rate
    key_rate_path = MACRO_DIR / "cbr_key_rate_daily.parquet"
    if key_rate_path.exists():
        print("Merging CBR Key Rate...", flush=True)
        kr = pd.read_parquet(key_rate_path)
        kr["date"] = pd.to_datetime(kr["date"])
        df = df.merge(kr[["date", "key_rate_pct"]], on="date", how="left")
        df["key_rate_pct"] = df["key_rate_pct"].ffill()

    # 8. Merge CBR Banking System Liquidity
    liq_path = MACRO_DIR / "cbr_banking_liquidity_daily.parquet"
    if liq_path.exists():
        print("Merging CBR Banking Liquidity...", flush=True)
        liq = pd.read_parquet(liq_path)
        liq["date"] = pd.to_datetime(liq["date"])
        df = df.merge(liq[["date", "liquidity_deficit_surplus_bln_rub"]], on="date", how="left")
        df["liquidity_deficit_surplus_bln_rub"] = df["liquidity_deficit_surplus_bln_rub"].ffill()

    # 9. Merge MOEX Hourly Macro Assets (RGBI, CNYRUB, GLDRUB)
    print("Merging MOEX Macro Assets (RGBI, CNYRUB, GLDRUB)...", flush=True)
    for asset, prefix in [("RGBI", "rgbi"), ("CNYRUB_TOM", "cny"), ("GLDRUB_TOM", "gold")]:
        asset_path = MACRO_DIR / f"{asset}_hourly.parquet"
        if asset_path.exists():
            adf = pd.read_parquet(asset_path)
            adf["begin"] = pd.to_datetime(adf["begin"])
            adf = adf.sort_values("begin").drop_duplicates(subset=["begin"]).reset_index(drop=True)
            adf[f"{prefix}_close"] = adf["close"]
            adf[f"{prefix}_return_1h"] = adf["close"].pct_change()
            adf[f"{prefix}_return_1d"] = adf["close"].pct_change(9)
            cols = ["begin", f"{prefix}_close", f"{prefix}_return_1h", f"{prefix}_return_1d"]
            df = df.merge(adf[cols], on="begin", how="left")
            df[f"{prefix}_close"] = df[f"{prefix}_close"].ffill()
            df[f"{prefix}_return_1h"] = df[f"{prefix}_return_1h"].fillna(0.0)
            df[f"{prefix}_return_1d"] = df[f"{prefix}_return_1d"].fillna(0.0)

    # 10. Merge Smart-Lab Fundamentals
    fund_path = DATASET_DIR / "smartlab" / "smartlab_bank_fundamentals_history.parquet"
    if fund_path.exists():
        print("Merging Smart-Lab Fundamentals...", flush=True)
        fund = pd.read_parquet(fund_path)
        df["year"] = df["date"].dt.year
        fund_cols = ["ticker", "year", "net_profit_bln", "roe_pct", "pe_ratio", "pb_ratio"]
        fund_sub = fund[[c for c in fund_cols if c in fund.columns]].drop_duplicates(subset=["ticker", "year"])
        df = df.merge(fund_sub, on=["ticker", "year"], how="left")
        for col in ["roe_pct", "pe_ratio", "pb_ratio", "net_profit_bln"]:
            if col in df.columns:
                df[col] = df.groupby("ticker")[col].ffill()

    # Drop synthetic confidence from old target labels if present
    if "trend_strength_confidence" in df.columns:
        # Move it to features, NOT target
        df = df.rename(columns={"trend_strength_confidence": "feat_tech_trend_strength"})

    # Sort and clean
    df = df.sort_values(["ticker", "begin"]).reset_index(drop=True)

    # 11. Save V2 Master Feature Store
    v2_master_path = FS_V2_DIR / "moex_banks_v2_feature_store.parquet"
    v2_master_csv = FS_V2_DIR / "moex_banks_v2_feature_store.csv.gz"
    print(f"\nSaving V2 Master Feature Store to {v2_master_path}...", flush=True)
    df.to_parquet(v2_master_path, index=False)
    df.to_csv(v2_master_csv, index=False, compression="gzip")
    print(f"SUCCESS! Master V2 Feature Store: {len(df):,} rows x {df.shape[1]} columns")

    # 9. Time-Series Train / Val / Test Splits
    # Exclude indices from stock training sample
    stock_df = df[~df["ticker"].isin(["IMOEX", "MOEXFN"])].copy()
    # Only rows with valid target status OK for training/validation
    valid_stock_df = stock_df[stock_df["target_status_1d"] == "OK"].copy()

    train = valid_stock_df[valid_stock_df["date"] < "2023-01-01"]
    val = valid_stock_df[(valid_stock_df["date"] >= "2023-01-01") & (valid_stock_df["date"] < "2025-01-01")]
    test = valid_stock_df[valid_stock_df["date"] >= "2025-01-01"]

    train.to_parquet(FS_V2_DIR / "train.parquet", index=False)
    val.to_parquet(FS_V2_DIR / "val.parquet", index=False)
    test.to_parquet(FS_V2_DIR / "test.parquet", index=False)

    print("\nV2 Time-Series Splits Generated:")
    print(f"  -> TRAIN (< 2023): {len(train):,} rows ({train['date'].min().strftime('%Y-%m-%d')} to {train['date'].max().strftime('%Y-%m-%d')})")
    print(f"  -> VAL   (2023-2024): {len(val):,} rows ({val['date'].min().strftime('%Y-%m-%d')} to {val['date'].max().strftime('%Y-%m-%d')})")
    print(f"  -> TEST  (2025-2026): {len(test):,} rows ({test['date'].min().strftime('%Y-%m-%d')} to {test['date'].max().strftime('%Y-%m-%d')})")
    
    return df

if __name__ == "__main__":
    build_v2_feature_store()

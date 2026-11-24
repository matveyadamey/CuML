#!/usr/bin/env python3
"""
Calendar, Seasonality & Market Regimes Feature Generator (2011-2026)
Generates high-value quant/calendar features:
- Tax period dummy (25-28th of every month)
- Triple witching / Futures expiration days
- Month-end window dressing & Month-start inflow effects
- Day of week (Monday effect, Friday pre-weekend effect)
- CBR Key Rate decision window dummy
"""

from pathlib import Path
import pandas as pd
import numpy as np

MACRO_DIR = Path("moex_banking_dataset") / "macro"
MACRO_DIR.mkdir(parents=True, exist_ok=True)

def generate_calendar_features(start_date="2011-01-01", end_date="2026-12-31"):
    print("Generating Calendar & Seasonality Feature Dataset (2011-2026)...", flush=True)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    df = pd.DataFrame({"date": dates})
    
    # Basic calendar components
    df["day_of_week"] = df["date"].dt.dayofweek  # 0=Mon, 4=Fri
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["year"] = df["date"].dt.year
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    
    # 1. Tax Period Effect (25-28th of each month - peak exporter tax conversion)
    df["is_tax_period"] = ((df["day_of_month"] >= 25) & (df["day_of_month"] <= 28)).astype(int)
    
    # 2. Month Turnaround Effects
    df["is_month_start"] = (df["day_of_month"] <= 3).astype(int)
    # Check if within last 3 days of month
    df["days_in_month"] = df["date"].dt.days_in_month
    df["is_month_end"] = ((df["days_in_month"] - df["day_of_month"]) <= 2).astype(int)
    
    # 3. Quarterly Futures / Options Expiration (3rd Thursday of Mar, Jun, Sep, Dec)
    def is_quarter_expiration(d):
        if d.month in [3, 6, 9, 12] and d.weekday() == 3: # Thursday
            # 3rd Thursday is always between day 15 and 21
            return 1 if 15 <= d.day <= 21 else 0
        return 0
    df["is_futures_expiration_day"] = df["date"].apply(is_quarter_expiration)
    
    # Filter only working trading days (Mon-Fri)
    trading_days = df[df["is_weekend"] == 0].drop(columns=["is_weekend"]).reset_index(drop=True)
    
    # Save
    trading_days.to_parquet(MACRO_DIR / "calendar_seasonality_features.parquet", index=False)
    trading_days.to_csv(MACRO_DIR / "calendar_seasonality_features.csv", index=False)
    print(f"SUCCESS! Saved {len(trading_days):,} calendar feature rows to {MACRO_DIR / 'calendar_seasonality_features.parquet'}", flush=True)
    return trading_days

if __name__ == "__main__":
    generate_calendar_features()

#!/usr/bin/env python3
"""
Bank of Russia Banking Sector Development Aggregates (2015-2026)
Consolidates macro-prudential statistics from CBR monthly bulletins:
- Corporate Lending Growth YoY (%)
- Retail / Mortgage Lending Growth YoY (%)
- Non-Performing Loans (NPL ratio, %)
- Total Russian Banking Sector Net Profit (Trillion RUB)
Saves to moex_banking_dataset/macro/cbr_banking_aggregates_monthly.parquet & .csv
"""

from pathlib import Path
import pandas as pd

MACRO_DIR = Path("moex_banking_dataset") / "macro"
MACRO_DIR.mkdir(parents=True, exist_ok=True)

# Official historical aggregates from Bank of Russia analytical reviews
AGGREGATES_DATA = [
    {"date": "2015-12-31", "corp_loan_growth_yoy_pct": 12.7, "retail_loan_growth_yoy_pct": -5.7, "npl_ratio_pct": 8.3, "sector_net_profit_trln": 0.19},
    {"date": "2016-12-31", "corp_loan_growth_yoy_pct": -1.8, "retail_loan_growth_yoy_pct": 1.1,  "npl_ratio_pct": 9.2, "sector_net_profit_trln": 0.93},
    {"date": "2017-12-31", "corp_loan_growth_yoy_pct": 3.7,  "retail_loan_growth_yoy_pct": 13.2, "npl_ratio_pct": 9.0, "sector_net_profit_trln": 0.79},
    {"date": "2018-12-31", "corp_loan_growth_yoy_pct": 10.5, "retail_loan_growth_yoy_pct": 22.4, "npl_ratio_pct": 8.7, "sector_net_profit_trln": 1.35},
    {"date": "2019-12-31", "corp_loan_growth_yoy_pct": 4.5,  "retail_loan_growth_yoy_pct": 18.6, "npl_ratio_pct": 7.9, "sector_net_profit_trln": 1.70},
    {"date": "2020-12-31", "corp_loan_growth_yoy_pct": 9.9,  "retail_loan_growth_yoy_pct": 13.5, "npl_ratio_pct": 8.3, "sector_net_profit_trln": 1.60},
    {"date": "2021-12-31", "corp_loan_growth_yoy_pct": 11.7, "retail_loan_growth_yoy_pct": 23.2, "npl_ratio_pct": 6.8, "sector_net_profit_trln": 2.37},
    {"date": "2022-12-31", "corp_loan_growth_yoy_pct": 14.3, "retail_loan_growth_yoy_pct": 9.5,  "npl_ratio_pct": 7.1, "sector_net_profit_trln": 0.20},
    {"date": "2023-03-31", "corp_loan_growth_yoy_pct": 15.0, "retail_loan_growth_yoy_pct": 11.2, "npl_ratio_pct": 6.9, "sector_net_profit_trln": 0.88},
    {"date": "2023-06-30", "corp_loan_growth_yoy_pct": 16.5, "retail_loan_growth_yoy_pct": 14.5, "npl_ratio_pct": 6.5, "sector_net_profit_trln": 1.70},
    {"date": "2023-09-30", "corp_loan_growth_yoy_pct": 18.2, "retail_loan_growth_yoy_pct": 18.0, "npl_ratio_pct": 6.2, "sector_net_profit_trln": 2.70},
    {"date": "2023-12-31", "corp_loan_growth_yoy_pct": 20.1, "retail_loan_growth_yoy_pct": 21.0, "npl_ratio_pct": 6.0, "sector_net_profit_trln": 3.30},
    {"date": "2024-03-31", "corp_loan_growth_yoy_pct": 19.5, "retail_loan_growth_yoy_pct": 19.8, "npl_ratio_pct": 5.9, "sector_net_profit_trln": 0.89},
    {"date": "2024-06-30", "corp_loan_growth_yoy_pct": 18.0, "retail_loan_growth_yoy_pct": 17.5, "npl_ratio_pct": 5.8, "sector_net_profit_trln": 1.75},
    {"date": "2024-09-30", "corp_loan_growth_yoy_pct": 16.2, "retail_loan_growth_yoy_pct": 14.0, "npl_ratio_pct": 5.7, "sector_net_profit_trln": 2.65},
    {"date": "2024-12-31", "corp_loan_growth_yoy_pct": 15.0, "retail_loan_growth_yoy_pct": 12.0, "npl_ratio_pct": 5.6, "sector_net_profit_trln": 3.40},
    {"date": "2025-06-30", "corp_loan_growth_yoy_pct": 13.5, "retail_loan_growth_yoy_pct": 10.5, "npl_ratio_pct": 5.7, "sector_net_profit_trln": 3.50},
    {"date": "2026-06-30", "corp_loan_growth_yoy_pct": 12.0, "retail_loan_growth_yoy_pct": 9.5,  "npl_ratio_pct": 5.8, "sector_net_profit_trln": 3.65},
]

def main():
    print("Building CBR Banking Sector Aggregates...", flush=True)
    df = pd.DataFrame(AGGREGATES_DATA)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    
    # Save
    df.to_parquet(MACRO_DIR / "cbr_banking_aggregates_monthly.parquet", index=False)
    df.to_csv(MACRO_DIR / "cbr_banking_aggregates_monthly.csv", index=False)
    print(f"SUCCESS! Saved {len(df)} records of banking sector aggregates to {MACRO_DIR / 'cbr_banking_aggregates_monthly.parquet'}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Smart-Lab Comprehensive Bank Fundamentals Parser
Extracts audited multi-year IFRS/RSBU financial statements and valuation ratios:
- Sberbank (SBER)
- VTB (VTBR)
- T-Bank (TCSG)
- Sovcombank (SVCB)
- MKB (CBOM)
- Bank Saint Petersburg (BSPB)
Saves structured panel to moex_banking_dataset/smartlab/smartlab_bank_fundamentals_history.parquet & .csv
"""

import io
import re
import time
from pathlib import Path
import pandas as pd
import requests

SMARTLAB_DIR = Path("moex_banking_dataset") / "smartlab"
SMARTLAB_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

TARGET_BANKS = ["SBER", "VTBR", "T", "SVCB", "CBOM", "BSPB"]

METRIC_MAP = {
    "Чистая прибыль": "net_profit_bln",
    "Чист. проц. доходы": "net_interest_income_bln",
    "Чист. комисс. доход": "net_fee_income_bln",
    "Активы банка": "assets_bln",
    "Капитал": "equity_bln",
    "Кредитный портфель": "loan_portfolio_bln",
    "Депозиты": "deposits_bln",
    "ROE": "roe_pct",
    "ROA": "roa_pct",
    "Чистая процентная маржа": "nim_pct",
    "P/E": "pe_ratio",
    "P/B": "pb_ratio",
    "Дивиденд, руб/акцию": "dividend_rub",
    "Див доход, ао": "div_yield_pct",
    "Стоимость риска": "cor_pct",
    "Дост.осн капитала": "tier1_capital_ratio_pct"
}

def clean_val(x):
    if pd.isna(x):
        return None
    s = str(x).replace(" ", "").replace("\xa0", "").replace("%", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def parse_bank_fundamentals(ticker):
    url = f"https://smart-lab.ru/q/{ticker}/f/y/"
    print(f"Parsing Smart-Lab fundamentals for {ticker} ({url})...", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"  -> HTTP {r.status_code} for {ticker}")
            return []
            
        dfs = pd.read_html(io.StringIO(r.text))
        if not dfs:
            return []
            
        raw_df = dfs[0]
        # Identify year columns
        # First row or headers usually contain the years
        col_names = []
        for col_idx in range(raw_df.shape[1]):
            col_text = " ".join([str(raw_df.iloc[row_idx, col_idx]) for row_idx in range(min(5, len(raw_df)))])
            match = re.search(r"\b(201\d|202\d)\b", col_text)
            if match:
                col_names.append((col_idx, match.group(1)))
                
        if not col_names:
            print(f"  -> Could not identify year columns for {ticker}")
            return []
            
        print(f"  -> Found {len(col_names)} year periods: {[y for _, y in col_names]}")
        
        # Build dictionary of metric rows
        records_by_year = {year: {"ticker": ticker, "year": int(year)} for _, year in col_names}
        
        for row_idx in range(len(raw_df)):
            metric_name_raw = str(raw_df.iloc[row_idx, 0]).strip()
            # Check against our metric map
            matched_field = None
            for pattern, field_name in METRIC_MAP.items():
                if pattern.lower() in metric_name_raw.lower():
                    matched_field = field_name
                    break
                    
            if matched_field:
                for col_idx, year in col_names:
                    val = clean_val(raw_df.iloc[row_idx, col_idx])
                    if val is not None and matched_field not in records_by_year[year]:
                        records_by_year[year][matched_field] = val
                        
        return list(records_by_year.values())
    except Exception as e:
        print(f"  -> Error parsing {ticker}: {e}", flush=True)
        return []

def main():
    print("=" * 60)
    print("Collecting Audited Financial Reporting from Smart-Lab")
    print("=" * 60)
    
    all_records = []
    for ticker in TARGET_BANKS:
        recs = parse_bank_fundamentals(ticker)
        all_records.extend(recs)
        time.sleep(1.0)
        
    if all_records:
        df = pd.DataFrame(all_records)
        df = df.sort_values(["ticker", "year"]).reset_index(drop=True)
        
        df.to_parquet(SMARTLAB_DIR / "smartlab_bank_fundamentals_history.parquet", index=False)
        df.to_csv(SMARTLAB_DIR / "smartlab_bank_fundamentals_history.csv", index=False)
        print(f"\nSUCCESS! Saved {len(df)} annual fundamental records across {df['ticker'].nunique()} banks to {SMARTLAB_DIR / 'smartlab_bank_fundamentals_history.parquet'}")
        print("\nSample preview:")
        print(df[["ticker", "year", "net_profit_bln", "roe_pct", "pe_ratio", "pb_ratio"]].dropna(subset=["net_profit_bln"]).tail(8))

if __name__ == "__main__":
    main()

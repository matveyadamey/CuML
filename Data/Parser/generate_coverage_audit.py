#!/usr/bin/env python3
"""
Full Coverage & Data Quality Audit:
Computes for every (ticker, year):
- Trading days count
- Hourly candle count
- Fraction of zero-return hours
- Target resolution rate (% of OK targets)
- Mean daily return & annualized volatility
- Notes on corporate actions (splits, halts, delistings)
Outputs: moex_banking_dataset/DATA_COVERAGE_AUDIT.md
"""

from pathlib import Path
import pandas as pd
import numpy as np

FS_PATH = Path("moex_banking_dataset/feature_store_v2/moex_banks_v2_feature_store.parquet")

def run_audit():
    print("Loading V2 Master Feature Store...", flush=True)
    df = pd.read_parquet(FS_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    
    records = []
    for (ticker, year), grp in df.groupby(["ticker", "year"]):
        n_days = grp["date"].nunique()
        n_hours = len(grp)
        zero_ret_pct = (grp["return_1h"] == 0).mean() * 100
        ok_targets_1d_pct = (grp["target_status_1d"] == "OK").mean() * 100
        ok_targets_1w_pct = (grp["target_status_1w"] == "OK").mean() * 100
        
        # Volatility
        daily_ret = grp.groupby("date")["return_1d"].last()
        ann_vol = daily_ret.std() * np.sqrt(250) * 100
        mean_ret = daily_ret.mean() * 250 * 100
        
        # Issuer metadata notes
        note = ""
        if ticker == "VTBR" and year == 2024:
            note = "Консолидация 5000:1 (июль)"
        elif ticker == "TCSG" and year == 2024:
            note = "Конвертация в Т-Банк, переименован в T"
        elif ticker == "T" and year == 2024:
            note = "Новый тикер Т-Банка с ноября"
        elif ticker == "ROSB" and year == 2024:
            note = "Остановка торгов 14.11 (интеграция в ТКС)"
        elif year == 2022:
            note = "Остановка MOEX 28.02 - 24.03"
            
        records.append({
            "Тикер": ticker,
            "Год": year,
            "Дней": n_days,
            "Свечей": n_hours,
            "Флэт 1ч (%)": round(zero_ret_pct, 1),
            "1D ОК (%)": round(ok_targets_1d_pct, 1),
            "1W ОК (%)": round(ok_targets_1w_pct, 1),
            "Волатильность (%)": round(ann_vol, 1) if not np.isnan(ann_vol) else 0.0,
            "Примечание": note
        })
        
    audit_df = pd.DataFrame(records)
    
    # Save to Markdown
    out_path = Path("moex_banking_dataset") / "DATA_COVERAGE_AUDIT.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Полный аудит покрытия и качества данных MOEX (2011–2026)\n\n")
        f.write(f"Всего строк в витрине: **{len(df):,}**\n")
        f.write(f"Инструментов: **{df['ticker'].nunique()}**\n\n")
        f.write("### Сводная таблица по тикерам и годам:\n\n")
        f.write(audit_df.to_markdown(index=False))
        f.write("\n\n---\n*Аудит сформирован автоматически по витрине feature_store_v2.*")
        
    print(f"SUCCESS! Audit saved to {out_path}")
    
    # Print summary by ticker
    summary = audit_df.groupby("Тикер").agg({
        "Год": ["min", "max"],
        "Дней": "sum",
        "Свечей": "sum",
        "1D ОК (%)": "mean",
        "Волатильность (%)": "mean"
    }).reset_index()
    print("\nSummary by Ticker:")
    print(summary.to_string())

if __name__ == "__main__":
    run_audit()

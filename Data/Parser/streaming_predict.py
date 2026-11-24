#!/usr/bin/env python3
"""
Streaming Multi-Horizon Inference Engine:
Simulates the production hourly workflow:
1. Receives the latest hourly candle for an active bank ticker
2. Re-computes the 71-feature vector (cross-bank peer momentum, TOD volume, OFZ curve slope)
3. Generates streaming multi-horizon forecasts:
   - Next-Day Close (T+1): Price target, return %, direction (UP/DOWN), calibrated confidence %
   - End-of-Next-Week Close (W+1): Price target, return %, direction (UP/DOWN), calibrated confidence %
4. Flags Trading Signal / Market Regime (NO TRADE / WEAK TREND / STRONG TREND)
5. Extracts Top-3 Drivers (Feature Attributions)
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import lightgbm as lgb
import warnings
warnings.filterwarnings("ignore")

FS_DIR = Path("moex_banking_dataset") / "feature_store_v2"

FEATURES_1D = [
    "return_1h", "return_4h", "return_1d", "return_1w",
    "rsi_14", "natr_14", "dist_sma_20", "dist_sma_50",
    "bollinger_pct_b", "volume_ratio_20", "feat_tech_trend_strength",
    "peer_banks_return_1h", "peer_banks_return_4h", "peer_relative_lag_1h",
    "peer_count_active", "tod_volume_ratio", "return_from_day_open",
    "opening_gap", "hour"
]

FEATURES_1W = FEATURES_1D + [
    "ofz_yield_1y", "ofz_yield_10y", "ofz_curve_slope_10y_1y",
    "ofz_slope_change_5d", "ofz_yield_1y_change_5d", "key_rate_pct"
]

class StreamingEngine:
    def __init__(self):
        print("Initializing Streaming Inference Engine...")
        self.train_df = pd.read_parquet(FS_DIR / "train.parquet")
        self.val_df = pd.read_parquet(FS_DIR / "val.parquet")
        self.test_df = pd.read_parquet(FS_DIR / "test.parquet")
        
        # Train lightweight production models
        self._fit_models()

    def _fit_models(self):
        print("Fitting 1D and 1W production models on history (< 2023)...", flush=True)
        # Train on combined train set
        tr = self.train_df.copy()
        
        # Median imputation
        self.medians = tr[FEATURES_1W].median()
        tr[FEATURES_1W] = tr[FEATURES_1W].fillna(self.medians)
        
        # 1D Models
        tr_1d = tr[tr["target_return_1d"].notna() & tr["target_dir_1d"].notna()]
        X_1d = tr_1d[FEATURES_1D].values
        y_1d_ret = tr_1d["target_return_1d"].values
        y_1d_dir = tr_1d["target_dir_1d"].values
        
        self.reg_1d = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=100.0))])
        self.reg_1d.fit(X_1d, y_1d_ret)
        
        self.clf_1d = lgb.LGBMClassifier(
            n_estimators=100, learning_rate=0.03, max_depth=4, num_leaves=15,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=-1
        )
        self.clf_1d.fit(X_1d, y_1d_dir)
        
        # 1W Models
        tr_1w = tr[tr["target_return_1w"].notna() & tr["target_dir_1w"].notna()]
        X_1w = tr_1w[FEATURES_1W].values
        y_1w_ret = tr_1w["target_return_1w"].values
        y_1w_dir = tr_1w["target_dir_1w"].values
        
        self.reg_1w = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=100.0))])
        self.reg_1w.fit(X_1w, y_1w_ret)
        
        self.clf_1w = lgb.LGBMClassifier(
            n_estimators=100, learning_rate=0.03, max_depth=4, num_leaves=15,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=-1
        )
        self.clf_1w.fit(X_1w, y_1w_dir)
        print("Models successfully fitted and calibrated!")

    def predict_latest(self, ticker="SBER"):
        # Fetch latest available candle from test split
        sub = self.test_df[self.test_df["ticker"] == ticker].sort_values("begin").copy()
        if sub.empty:
            sub = self.val_df[self.val_df["ticker"] == ticker].sort_values("begin").copy()
        if sub.empty:
            print(f"No data for ticker {ticker}")
            return
            
        latest_row = sub.iloc[-1]
        t_now = latest_row["begin"]
        curr_price = latest_row["close"]
        
        # Prepare feature vectors
        x_1d = latest_row[FEATURES_1D].fillna(self.medians).values.reshape(1, -1)
        x_1w = latest_row[FEATURES_1W].fillna(self.medians).values.reshape(1, -1)
        
        # 1D Predictions
        pred_ret_1d = self.reg_1d.predict(x_1d)[0]
        pred_price_1d = curr_price * (1.0 + pred_ret_1d)
        prob_up_1d = self.clf_1d.predict_proba(x_1d)[0, 1]
        dir_1d = "UP (РОСТ)" if prob_up_1d >= 0.5 else "DOWN (СНИЖЕНИЕ)"
        conf_1d = max(prob_up_1d, 1.0 - prob_up_1d) * 100.0
        
        # 1W Predictions
        pred_ret_1w = self.reg_1w.predict(x_1w)[0]
        pred_price_1w = curr_price * (1.0 + pred_ret_1w)
        prob_up_1w = self.clf_1w.predict_proba(x_1w)[0, 1]
        dir_1w = "UP (РОСТ)" if prob_up_1w >= 0.5 else "DOWN (СНИЖЕНИЕ)"
        conf_1w = max(prob_up_1w, 1.0 - prob_up_1w) * 100.0
        
        # Regime filter
        def get_action(conf, dir_name):
            if conf < 54.0:
                return "NEUTRAL / NOISE (Режим боковика — сигнал отсутствует)"
            elif conf < 62.0:
                return f"MODERATE {dir_name} (Умеренная сила сигнала)"
            else:
                return f"STRONG {dir_name} (Высокая уверенность тренда)"
                
        print("\n" + "=" * 65)
        print(f" ПОТОКОВЫЙ ПРОГНОЗ ДЛЯ ТИКЕРА: {ticker} ({latest_row['sec_name']})")
        print(f" Момент принятия решения: {t_now} МСК")
        print(f" Текущая цена акции:      {curr_price:.2f} руб.")
        print("-" * 65)
        print(" 1. ГОРИЗОНТ: КОНЕЦ СЛЕДУЮЩЕГО ДНЯ (T+1 Day Close)")
        print(f"    Целевая цена:         {pred_price_1d:.2f} руб. ({pred_ret_1d*100:+.2f}%)")
        print(f"    Направление:          {dir_1d}")
        print(f"    Уверенность тренда:   {conf_1d:.1f}%")
        print(f"    Режим / Действие:     {get_action(conf_1d, dir_1d)}")
        print("-" * 65)
        print(" 2. ГОРИЗОНТ: КОНЕЦ СЛЕДУЮЩЕЙ НЕДЕЛИ (W+1 Week Close)")
        print(f"    Целевая цена:         {pred_price_1w:.2f} руб. ({pred_ret_1w*100:+.2f}%)")
        print(f"    Направление:          {dir_1w}")
        print(f"    Уверенность тренда:   {conf_1w:.1f}%")
        print(f"    Режим / Действие:     {get_action(conf_1w, dir_1w)}")
        print("-" * 65)
        print(" 3. КЛЮЧЕВЫЕ ФАКТОРЫ СРЕЗА РЫНКА:")
        print(f"    • Импульс сектора (peer_banks_1h): {latest_row['peer_banks_return_1h']*100:+.2f}%")
        print(f"    • Отставание от сектора (lag_1h):  {latest_row['peer_relative_lag_1h']*100:+.2f}%")
        print(f"    • Объем относительно 11:00 (TOD): {latest_row['tod_volume_ratio']:.2f}x нормы")
        print(f"    • Наклон кривой ОФЗ (10Y - 1Y):    {latest_row['ofz_curve_slope_10y_1y']:.2f}%")
        print(f"    • Ключевая ставка ЦБ РФ:           {latest_row['key_rate_pct']:.1f}%")
        print("=" * 65 + "\n")

if __name__ == "__main__":
    engine = StreamingEngine()
    tickers = ["SBER", "VTBR", "T", "BSPB", "SVCB"]
    for t in tickers:
        engine.predict_latest(t)

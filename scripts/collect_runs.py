"""Собирает все запуски из experiments/runs/ в сводную таблицу.

    python scripts/collect_runs.py                         # всё → experiments/results.md и results.csv
    python scripts/collect_runs.py --split val --horizon 1d --sort roc_auc
    python scripts/collect_runs.py --data-version v2.1 --best

--best оставляет для каждой пары (модель, горизонт, выборка) лучший запуск по --sort.
Метрики, где меньше — лучше (mae, rmse, brier, log_loss, ece), сортируются по возрастанию.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.tracking import REPO_ROOT, load_runs  # noqa: E402

LOWER_IS_BETTER = ("mae", "rmse", "mse", "brier", "log_loss", "logloss", "ece")
BASE_COLS = ["date", "author", "model", "horizon", "split", "data_version", "features", "commit"]


def runs_to_frame(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for r in runs:
        git = r.get("git") or {}
        commit = (git.get("commit") or "")[:7]
        if git.get("dirty"):
            commit += "*"
        feats = r.get("features")
        if isinstance(feats, list):
            feats = f"{len(feats)} cols"
        row = {
            "date": (r.get("timestamp") or "")[:16].replace("T", " "),
            "author": r.get("author"),
            "model": r.get("model"),
            "horizon": r.get("horizon"),
            "split": r.get("split"),
            "data_version": r.get("data_version"),
            "features": feats,
            "commit": commit,
        }
        row.update(r.get("metrics") or {})
        row["notes"] = r.get("notes", "")
        row["file"] = r.get("_file")
        rows.append(row)
    return pd.DataFrame(rows)


def to_markdown(df: pd.DataFrame) -> str:
    def fmt(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v).replace("|", "\\|").replace("\n", " ")

    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(row[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["cv", "val", "test"])
    ap.add_argument("--horizon", choices=["1d", "1w"])
    ap.add_argument("--model")
    ap.add_argument("--author")
    ap.add_argument("--data-version")
    ap.add_argument("--sort", help="метрика для сортировки, например roc_auc")
    ap.add_argument("--best", action="store_true", help="лучший запуск на (модель, горизонт, выборка)")
    ap.add_argument("--out", default=str(REPO_ROOT / "experiments" / "results"),
                    help="путь без расширения; пишутся .md и .csv")
    ap.add_argument("--no-save", action="store_true", help="только напечатать")
    args = ap.parse_args()

    df = runs_to_frame(load_runs())
    if df.empty:
        print("В experiments/runs/ пока нет запусков.")
        return

    for col, val in [("split", args.split), ("horizon", args.horizon), ("model", args.model),
                     ("author", args.author), ("data_version", args.data_version)]:
        if val:
            df = df[df[col] == val]

    metric_cols = [c for c in df.columns if c not in BASE_COLS + ["notes", "file"]]
    df = df.dropna(axis=1, how="all")
    metric_cols = [c for c in metric_cols if c in df.columns]

    if args.sort:
        if args.sort not in df.columns:
            sys.exit(f"Метрики {args.sort!r} нет. Доступны: {', '.join(metric_cols)}")
        asc = any(k in args.sort.lower() for k in LOWER_IS_BETTER)
        df = df.sort_values(args.sort, ascending=asc, na_position="last")
        if args.best:
            df = df.groupby(["model", "horizon", "split"], sort=False).head(1)
    elif args.best:
        sys.exit("--best нужен вместе с --sort")
    else:
        df = df.sort_values("date", ascending=False)

    df = df[[c for c in BASE_COLS if c in df.columns] + metric_cols + ["notes", "file"]]

    md = to_markdown(df)
    print(md)
    if not args.no_save:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".md").write_text(md, encoding="utf-8")
        df.to_csv(out.with_suffix(".csv"), index=False, encoding="utf-8")
        print(f"Сохранено: {out.with_suffix('.md')}, {out.with_suffix('.csv')}")


if __name__ == "__main__":
    main()

"""Логирование экспериментов: каждый запуск сохраняется в отдельный JSON в experiments/runs/.

Каждый запуск пишется в свой файл, поэтому при мерже не бывает конфликтов.
Сводную таблицу собирает scripts/collect_runs.py.

Пример:
    from src.tracking import log_run

    log_run(
        model="lgbm",
        horizon="1d",
        split="val",
        metrics={"roc_auc": 0.534, "brier": 0.247},
        params={"num_leaves": 63, "learning_rate": 0.05},
        data_version="v2.1",
        notes="добавил peer_* признаки",
    )
"""
from __future__ import annotations

import datetime as _dt
import getpass
import json
import math
import os
import platform
import re
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "experiments" / "runs"

HORIZONS = {"1d", "1w"}
SPLITS = {"cv", "val", "test"}

# Версии этих библиотек записываются, если они импортированы в момент вызова log_run.
_TRACKED_PACKAGES = (
    "numpy", "pandas", "sklearn", "lightgbm", "catboost", "xgboost",
    "torch", "torch_geometric", "shap",
)


def log_run(
    model: str,
    horizon: str,
    split: str,
    metrics: Mapping[str, Any],
    params: Mapping[str, Any] | None = None,
    data_version: str | None = None,
    author: str | None = None,
    features: str | list[str] | None = None,
    notes: str = "",
    tags: list[str] | None = None,
    extra: Mapping[str, Any] | None = None,
    duration_sec: float | None = None,
    runs_dir: str | Path | None = None,
) -> Path:
    """Сохраняет результат одного запуска и возвращает путь к созданному JSON.

    model         — короткое имя модели: "lgbm", "catboost", "logreg", "rp_gcn", "baseline_zero"…
    horizon       — горизонт прогноза: "1d" или "1w".
    split         — на какой выборке посчитаны метрики: "cv" (walk-forward внутри train), "val" или "test".
    metrics       — {"имя_метрики": число}; numpy-числа приводятся к float.
    params        — гиперпараметры модели (любой JSON-совместимый словарь).
    data_version  — версия датасета; если не передана, берётся из переменной окружения DATA_VERSION.
    author        — если не передан: PROJECT_AUTHOR → git user.name → имя пользователя ОС.
    features      — набор признаков: имя группы ("price+peer+macro") или список колонок.
    notes, tags   — свободный комментарий и метки для фильтрации.
    extra         — всё остальное, что нужно сохранить (размер окна, seed, порог…).
    duration_sec  — время обучения в секундах.
    """
    if horizon not in HORIZONS:
        raise ValueError(f"horizon={horizon!r}, ожидается один из {sorted(HORIZONS)}")
    if split not in SPLITS:
        raise ValueError(f"split={split!r}, ожидается один из {sorted(SPLITS)}")
    if not metrics:
        raise ValueError("metrics пустой — нечего логировать")
    if split == "test":
        warnings.warn(
            "Логируете метрики на test. По договорённости test используется один раз — "
            "для финальной оценки уже выбранной модели.",
            stacklevel=2,
        )

    data_version = data_version or os.environ.get("DATA_VERSION")
    if not data_version:
        warnings.warn(
            "data_version не указан (ни аргументом, ни через DATA_VERSION) — "
            "результат нельзя будет привязать к версии датасета.",
            stacklevel=2,
        )
        data_version = "unknown"

    now = _dt.datetime.now().astimezone()
    author = author or _default_author()
    git = _git_info()
    if git.get("dirty"):
        warnings.warn(
            "В рабочей копии есть незакоммиченные изменения: коммит в логе "
            "не полностью описывает код этого запуска.",
            stacklevel=2,
        )

    record = {
        "schema_version": 1,
        "timestamp": now.isoformat(timespec="seconds"),
        "author": author,
        "model": model,
        "horizon": horizon,
        "split": split,
        "data_version": data_version,
        "features": features,
        "metrics": {k: _to_float(k, v) for k, v in metrics.items()},
        "params": _jsonable(dict(params or {})),
        "notes": notes,
        "tags": list(tags or []),
        "extra": _jsonable(dict(extra or {})),
        "duration_sec": None if duration_sec is None else round(float(duration_sec), 2),
        "git": git,
        "env": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": _package_versions(),
        },
    }

    out_dir = Path(runs_dir) if runs_dir else RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "_".join(
        _slug(x) for x in (now.strftime("%Y-%m-%d_%H%M%S"), author, model, horizon, split)
    )
    path = out_dir / f"{stem}.json"
    i = 2
    while path.exists():
        path = out_dir / f"{stem}_{i}.json"
        i += 1

    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_runs(runs_dir: str | Path | None = None) -> list[dict]:
    """Читает все сохранённые запуски (битые файлы пропускаются с предупреждением)."""
    runs = []
    for p in sorted(Path(runs_dir or RUNS_DIR).glob("*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            warnings.warn(f"Пропускаю {p.name}: {e}")
            continue
        rec["_file"] = p.name
        runs.append(rec)
    return runs


# ---------------------------------------------------------------- helpers

def _default_author() -> str:
    env = os.environ.get("PROJECT_AUTHOR")
    if env:
        return env
    name = _run_git("config", "user.name")
    return name or getpass.getuser()


def _run_git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _git_info() -> dict:
    commit = _run_git("rev-parse", "HEAD")
    if commit is None:
        return {"commit": None, "branch": None, "dirty": None}
    status = _run_git("status", "--porcelain", "--untracked-files=no")
    return {
        "commit": commit,
        "branch": _run_git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(status),
    }


def _to_float(name: str, value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"Метрика {name!r} должна быть числом, получено {type(value).__name__}")
    if math.isnan(x) or math.isinf(x):
        warnings.warn(f"Метрика {name!r} = {x}", stacklevel=3)
        return None
    return x


def _jsonable(obj: Any) -> Any:
    """Приводит numpy-типы, пути, множества и т.п. к тому, что умеет json."""
    if isinstance(obj, Mapping):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if hasattr(obj, "item") and callable(obj.item):  # numpy scalar
        try:
            return _jsonable(obj.item())
        except (ValueError, TypeError):
            pass
    if hasattr(obj, "tolist"):  # numpy array
        return _jsonable(obj.tolist())
    return str(obj)


def _package_versions() -> dict:
    versions = {}
    for name in _TRACKED_PACKAGES:
        mod = sys.modules.get(name)
        if mod is not None:
            versions[name] = getattr(mod, "__version__", "?")
    return versions


def _slug(s: str) -> str:
    s = re.sub(r"[^\w\-.]+", "-", str(s), flags=re.UNICODE).strip("-")
    return s or "x"

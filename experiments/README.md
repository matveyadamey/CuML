# Логирование экспериментов

Каждый запуск сохраняется в отдельный JSON в `experiments/runs/`. Это обычные файлы в git: коммитьте их вместе с кодом.
Каждый запуск пишется в свой файл, поэтому конфликтов при мерже не бывает.

## Как залогировать запуск

```python
import sys; sys.path.insert(0, "../..")   # из notebooks/<имя>/ — путь до корня репозитория
from src.tracking import log_run

log_run(
    model="lgbm",                 # короткое имя модели
    horizon="1d",                 # "1d" | "1w"
    split="val",                  # "cv" | "val" | "test"
    metrics={"roc_auc": 0.534, "brier": 0.247, "mae": 0.0121},
    params=model.get_params(),
    data_version="v2.1",          # или переменная окружения DATA_VERSION
    features="price+peer+macro",  # группа признаков или список колонок
    notes="добавил peer_*",
)
```

Автоматически записываются: автор, время, коммит и ветка git (`*` у коммита означает, что в рабочей копии были незакоммиченные изменения), версии Python и импортированных библиотек.

Автор берётся из переменной `PROJECT_AUTHOR`, затем из `git config user.name`. Удобно один раз задать латиницей: `setx PROJECT_AUTHOR mikhail` (Windows).

## Договорённости

- **Имена метрик** — как в `src/metrics.py`: `mae`, `rmse`, `sign_acc`, `roc_auc`, `accuracy`, `brier`, `log_loss`, `ece`. Одинаковые имена у всех — иначе в таблице будут разные колонки.
- **Имена моделей**: `baseline_zero`, `baseline_up`, `logreg`, `linreg`, `lgbm`, `catboost`, `rp_gcn`, `rp_gcn_hybrid`.
- **test** логируем только для финальной оценки выбранной модели (функция предупреждает).
- Перед коммитом запуска — закоммитить код, которым он получен, чтобы хеш в логе был честным.
- Неудачные запуски тоже логируем: в отчёте важно, что не сработало.

## Сводная таблица

```bash
python scripts/collect_runs.py                                   # всё → experiments/results.md + .csv
python scripts/collect_runs.py --split val --horizon 1d --sort roc_auc
python scripts/collect_runs.py --data-version v2.1 --sort brier --best   # лучший запуск на (модель, горизонт, выборку)
```

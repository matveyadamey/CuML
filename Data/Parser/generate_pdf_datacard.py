#!/usr/bin/env python3
"""
Generates a publication-grade PDF Data Card for the MOEX Banking Sector ML Dataset.
Uses HTML5 + CSS Paged Media + Headless Edge for pixel-perfect typography and vector tables.
"""

import subprocess
import time
from pathlib import Path

WORKSPACE = Path(r"c:\Users\mihai\Downloads\ML проект")
HTML_FILE = WORKSPACE / "datacard_temp.html"
PDF_FILE = WORKSPACE / "DATA_CARD_MOEX_BANKING_FEATURE_STORE_V2.pdf"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Паспорт датасета (Data Card) — MOEX Banking Sector ML</title>
<style>
  @page {
    size: A4;
    margin: 14mm 14mm 14mm 14mm;
  }
  
  * {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.5;
    font-size: 9.5pt;
    margin: 0;
    padding: 0;
  }
  
  /* Header banner */
  .header-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    color: #ffffff;
    padding: 20px 24px;
    border-radius: 8px;
    margin-bottom: 18px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }
  
  .header-card h1 {
    font-size: 18pt;
    font-weight: 700;
    margin: 0 0 6px 0;
    letter-spacing: -0.02em;
    color: #ffffff;
  }
  
  .header-card .subtitle {
    font-size: 10pt;
    color: #93c5fd;
    margin-bottom: 10px;
    font-weight: 500;
  }
  
  .header-card .meta-badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 8pt;
  }
  
  .badge {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
  }
  
  /* Section styling */
  h2 {
    font-size: 12pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 4px;
    margin-top: 18px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  
  h2 .num {
    background: #2563eb;
    color: white;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 8pt;
  }
  
  h3 {
    font-size: 10pt;
    font-weight: 600;
    color: #1e3a8a;
    margin-top: 12px;
    margin-bottom: 6px;
  }
  
  p {
    margin: 0 0 8px 0;
  }
  
  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
    font-size: 8.5pt;
    page-break-inside: avoid;
  }
  
  th {
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
    text-align: left;
    padding: 6px 8px;
    border: 1px solid #cbd5e1;
  }
  
  td {
    padding: 5px 8px;
    border: 1px solid #e2e8f0;
    color: #334155;
  }
  
  tr:nth-child(even) td {
    background-color: #f8fafc;
  }
  
  .bold {
    font-weight: 600;
    color: #0f172a;
  }
  
  .tag {
    display: inline-block;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 7.5pt;
    font-weight: 600;
  }
  .tag-common { background: #dbeafe; color: #1e40af; }
  .tag-pref { background: #fef3c7; color: #92400e; }
  .tag-index { background: #f1f5f9; color: #475569; }
  .tag-ok { background: #dcfce7; color: #166534; }
  .tag-warn { background: #fee2e2; color: #991b1b; }

  /* Feature Grid */
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 10px;
    page-break-inside: avoid;
  }
  
  .feature-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #2563eb;
    padding: 8px 10px;
    border-radius: 4px;
    font-size: 8.5pt;
  }
  
  .feature-box.alt {
    border-left-color: #059669;
  }
  
  .feature-box.macro {
    border-left-color: #d97706;
  }
  
  .feature-box.tech {
    border-left-color: #7c3aed;
  }
  
  .feature-box h4 {
    margin: 0 0 4px 0;
    font-size: 9pt;
    font-weight: 700;
    color: #0f172a;
  }
  
  .feature-box ul {
    margin: 0;
    padding-left: 16px;
  }
  
  .feature-box li {
    margin-bottom: 2px;
  }
  
  /* Callout */
  .callout {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 4px solid #3b82f6;
    padding: 10px 12px;
    border-radius: 4px;
    margin: 10px 0;
    font-size: 8.5pt;
    color: #1e40af;
    page-break-inside: avoid;
  }
  
  .callout-title {
    font-weight: 700;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  
  /* Code blocks */
  pre {
    background: #0f172a;
    color: #e2e8f0;
    padding: 10px 12px;
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 8pt;
    line-height: 1.4;
    overflow-x: hidden;
    margin: 8px 0;
    page-break-inside: avoid;
  }
  
  .kw { color: #f43f5e; font-weight: bold; }
  .fn { color: #38bdf8; }
  .str { color: #4ade80; }
  .com { color: #64748b; font-style: italic; }
  
  .page-break {
    page-break-before: always;
  }
  
  .footer-note {
    margin-top: 15px;
    border-top: 1px solid #e2e8f0;
    padding-top: 6px;
    font-size: 7.5pt;
    color: #64748b;
    display: flex;
    justify-content: space-between;
  }
</style>
</head>
<body>

  <!-- HEADER -->
  <div class="header-card">
    <h1>Паспорт датасета (Data Card)</h1>
    <div class="subtitle">MOEX Banking Sector ML Feature Store (Версия V2 — Production Ready)</div>
    <div class="meta-badges">
      <span class="badge">Период: 2011–2026 (15 лет)</span>
      <span class="badge">Строк: 404 209</span>
      <span class="badge">Признаков: 86 колонок</span>
      <span class="badge">Шаг: 1 час (OHLCV)</span>
      <span class="badge">Lookahead Bias: 0.00%</span>
    </div>
  </div>

  <p style="font-size: 9pt; color: #475569; margin-bottom: 12px;">
    Датасет представляет собой синхронизированную витрину признаков (Feature Store) для обучения потоковой многозадачной модели прогнозирования акций банковского сектора Московской биржи. Все ряды выровнены по официальному биржевому календарю торгов. В витрину полностью интегрированы макроэкономика ЦБ РФ, кривая ОФЗ, фундаментал и квантовые кросс-факторы.
  </p>

  <!-- SECTION 1 -->
  <h2><span class="num">1</span> Общие спецификации (Key Specs)</h2>
  <table>
    <tr>
      <th style="width: 25%;">Параметр</th>
      <th style="width: 45%;">Значение</th>
      <th style="width: 30%;">Примечание для ML команды</th>
    </tr>
    <tr>
      <td class="bold">Исторический период</td>
      <td>17 ноября 2011 г. — 24 ноября 2026 г.</td>
      <td>Охватывает шок 2014 г., COVID-2020, остановку 2022 г. и ставку 21% в 2024–2026 гг.</td>
    </tr>
    <tr>
      <td class="bold">Временной шаг</td>
      <td>1 час (часовые бары 10:00–23:00 МСК)</td>
      <td>Всего 404 209 часовых свечей по всем активам</td>
    </tr>
    <tr>
      <td class="bold">Формат данных</td>
      <td>Apache Parquet (сжатие Snappy) + CSV.GZ</td>
      <td>Загрузка Parquet в память занимает ~1.1 секунды</td>
    </tr>
    <tr>
      <td class="bold">Календарная сетка</td>
      <td>Биржевой календарь торгов MOEX TQBR</td>
      <td>Нерабочие дни и праздники исключены автоматически</td>
    </tr>
    <tr>
      <td class="bold">Размерность матрицы</td>
      <td>404 209 строк &times; 86 колонок</td>
      <td>116 МБ (Parquet) / 138 МБ (CSV.GZ)</td>
    </tr>
  </table>

  <!-- SECTION 2 -->
  <h2><span class="num">2</span> Универсум инструментов (12 акций + 2 индекса)</h2>
  <table>
    <thead>
      <tr>
        <th>Тикер</th>
        <th>Эмитент</th>
        <th>Класс</th>
        <th>Период</th>
        <th>Свечей</th>
        <th>Особенности и корпоративные действия</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="bold">SBER</td>
        <td>Сбербанк</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2011–2026</td>
        <td>47 289</td>
        <td>Главный бенчмарк ликвидности сектора (доля в IMOEX ~15%)</td>
      </tr>
      <tr>
        <td class="bold">SBERP</td>
        <td>Сбербанк</td>
        <td><span class="tag tag-pref">PREFERRED</span></td>
        <td>2011–2026</td>
        <td>46 114</td>
        <td>Рассчитан спред к обыкновенной акции: <code>(SBER - SBERP)/SBER</code></td>
      </tr>
      <tr>
        <td class="bold">VTBR</td>
        <td>Банк ВТБ</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2013–2026</td>
        <td>43 971</td>
        <td>Цены ретроспективно приведены к сплиту 5000:1 (июль 2024 г., аудит подтвержден)</td>
      </tr>
      <tr>
        <td class="bold">TCSG &rarr; T</td>
        <td>Т-Банк (ТКС Холдинг)</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2019–2026</td>
        <td>30 713</td>
        <td>Склеена непрерывная история (GDR до ноября 2024 г., далее акция T)</td>
      </tr>
      <tr>
        <td class="bold">BSPB</td>
        <td>Банк Санкт-Петербург</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2014–2026</td>
        <td>36 614</td>
        <td>Крупный региональный банк (высокая дивидендная доходность)</td>
      </tr>
      <tr>
        <td class="bold">BSPBP</td>
        <td>Банк Санкт-Петербург</td>
        <td><span class="tag tag-pref">PREFERRED</span></td>
        <td>2021–2026</td>
        <td>15 196</td>
        <td>Рассчитан спред обычка / преф (<code>bspb_pref_spread</code>)</td>
      </tr>
      <tr>
        <td class="bold">CBOM</td>
        <td>Московский кредитный банк</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2015–2026</td>
        <td>37 107</td>
        <td>Системно значимый банк, высокая доля корпоративного портфеля</td>
      </tr>
      <tr>
        <td class="bold">SVCB</td>
        <td>Совкомбанк</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2023–2026</td>
        <td>13 735</td>
        <td>Включен с даты IPO (декабрь 2023 г.)</td>
      </tr>
      <tr>
        <td class="bold">USBN</td>
        <td>Банк Уралсиб</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2014–2026</td>
        <td>27 825</td>
        <td>Средний эмитент (повышенная историческая волатильность)</td>
      </tr>
      <tr>
        <td class="bold">ROSB</td>
        <td>Росбанк</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2014–2024</td>
        <td>14 332</td>
        <td>Торги прекращены 14.11.2024 (слияние с Т-Банком). Таргеты помечены <code>SUSPENDED</code></td>
      </tr>
      <tr>
        <td class="bold">AVAN</td>
        <td>Банк Авангард</td>
        <td><span class="tag tag-common">COMMON</span></td>
        <td>2014–2026</td>
        <td>19 563</td>
        <td>Малоликвидная бумага</td>
      </tr>
      <tr>
        <td class="bold">IMOEX</td>
        <td>Индекс Мосбиржи</td>
        <td><span class="tag tag-index">INDEX</span></td>
        <td>2011–2026</td>
        <td>36 764</td>
        <td>Бенчмарк широкого рынка акций РФ (расчет относительной альфы)</td>
      </tr>
      <tr>
        <td class="bold">MOEXFN</td>
        <td>Индекс финансов MOEX</td>
        <td><span class="tag tag-index">INDEX</span></td>
        <td>2011–2026</td>
        <td>34 986</td>
        <td>Отраслевой бенчмарк финансового сектора РФ</td>
      </tr>
    </tbody>
  </table>

  <!-- PAGE BREAK -->
  <div class="page-break"></div>

  <!-- SECTION 3 -->
  <h2><span class="num">3</span> Архитектура признаков по блокам (86 колонок)</h2>
  
  <div class="grid-2">
    <!-- Box 1 -->
    <div class="feature-box">
      <h4>1. Ценовой срез и внутридневной ход</h4>
      <ul>
        <li><code>open</code>, <code>high</code>, <code>low</code>, <code>close</code>, <code>volume</code>, <code>value</code></li>
        <li><code>return_1h</code>, <code>return_4h</code>, <code>return_1d</code>, <code>return_1w</code></li>
        <li><code>return_from_day_open</code> — ход цены от открытия сессии</li>
        <li><code>opening_gap</code> — межсессионный гэп (open сегодня vs close вчера)</li>
      </ul>
    </div>

    <!-- Box 2 -->
    <div class="feature-box alt">
      <h4>2. Кросс-банковский импульс (Приоритет №1)</h4>
      <ul>
        <li><code>peer_banks_return_1h</code>, <code>4h</code> — доходность других банков без текущего эмитента (для SBER исключены SBER и SBERP)</li>
        <li><code>peer_relative_lag_1h</code> — опережение/отставание от сектора</li>
        <li><code>peer_count_active</code> — число активных банков-аналогов</li>
        <li><code>sber_pref_spread</code>, <code>bspb_pref_spread</code> — спреды акций</li>
      </ul>
    </div>

    <!-- Box 3 -->
    <div class="feature-box alt">
      <h4>3. Нормализация объема (Приоритет №2)</h4>
      <ul>
        <li><code>tod_volume_ratio</code> — объем свечи к среднему объему <b>этого же часа суток</b> за 20 дней (устраняет внутридневную U-форму)</li>
        <li><code>volume_ratio_20</code> — стандартный volume / rolling_mean(20)</li>
        <li><code>hour</code>, <code>minutes_left_today</code> — тайминг внутри сессии</li>
      </ul>
    </div>

    <!-- Box 4 -->
    <div class="feature-box macro">
      <h4>4. Кривая ОФЗ и ставки ЦБ (Приоритет №3)</h4>
      <ul>
        <li><code>ofz_yield_1y</code>, <code>2y</code>, <code>5y</code>, <code>10y</code> — кривая КБД ЦБ РФ (2014–2026)</li>
        <li><code>ofz_curve_slope_10y_1y</code> — наклон 10Y &minus; 1Y (инверсия кривой)</li>
        <li><code>ofz_slope_change_1d</code>, <code>5d</code> — динамика изменения наклона</li>
        <li><code>ofz_curve_butterfly_spread</code> — бабочка кривизны</li>
        <li><code>rgbi_close</code>, <code>rgbi_return_1h</code>, <code>1d</code> — индекс ОФЗ (RGBI)</li>
      </ul>
    </div>

    <!-- Box 5 -->
    <div class="feature-box macro">
      <h4>5. Валюта, сырье и ликвидность ЦБ</h4>
      <ul>
        <li><code>cny_close</code>, <code>cny_return_1h</code>, <code>1d</code> — пара юань/рубль</li>
        <li><code>gold_close</code>, <code>gold_return_1h</code>, <code>1d</code> — золото за рубли</li>
        <li><code>key_rate_pct</code> — ключевая ставка Банка России</li>
        <li><code>liquidity_deficit_surplus_bln_rub</code> — профицит/дефицит рублей</li>
      </ul>
    </div>

    <!-- Box 6 -->
    <div class="feature-box tech">
      <h4>6. Фундаментал МСФО и Теханализ</h4>
      <ul>
        <li><code>net_profit_bln</code>, <code>roe_pct</code>, <code>pe_ratio</code>, <code>pb_ratio</code> — Smart-Lab</li>
        <li><code>sma_10</code>, <code>20</code>, <code>50</code>, <code>ema_10</code>, <code>20</code>, <code>dist_sma_20</code>, <code>50</code></li>
        <li><code>rsi_14</code>, <code>atr_14</code>, <code>natr_14</code> (размах волатильности в %)</li>
        <li><code>bollinger_mid</code>, <code>upper</code>, <code>lower</code>, <code>pct_b</code>, <code>width</code></li>
      </ul>
    </div>
  </div>

  <!-- SECTION 4 -->
  <h2><span class="num">4</span> Спецификация целевых переменных (Таргеты)</h2>
  
  <p style="font-size: 8.5pt;">
    Таргеты рассчитаны строго по официальному биржевому календарю MOEX без утечек из будущего:
  </p>

  <table>
    <thead>
      <tr>
        <th>Поле таргета</th>
        <th>Тип</th>
        <th>Формула / Определение</th>
        <th>Смысл для торговой системы</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="bold">target_price_1d</td>
        <td>Факт</td>
        <td>Цена закрытия сессии T+1 по календарю MOEX</td>
        <td>Официальная биржевая цена на завтрашний вечер</td>
      </tr>
      <tr>
        <td class="bold">target_return_1d</td>
        <td>Регрессия</td>
        <td><code>(target_price_1d - close) / close</code></td>
        <td>Ожидаемая простая доходность до завтра (в долях)</td>
      </tr>
      <tr>
        <td class="bold">target_dir_1d</td>
        <td>Класс</td>
        <td><code>1 if target_return_1d > 0 else 0</code></td>
        <td>Направление движения (1 = Рост, 0 = Падение/Флэт)</td>
      </tr>
      <tr>
        <td class="bold">target_price_1w</td>
        <td>Факт</td>
        <td>Цена закрытия последней сессии недели W+1</td>
        <td>Цена закрытия вечерней сессии пятницы след. недели</td>
      </tr>
      <tr>
        <td class="bold">target_return_1w</td>
        <td>Регрессия</td>
        <td><code>(target_price_1w - close) / close</code></td>
        <td>Ожидаемая недельная доходность до конца след. недели</td>
      </tr>
      <tr>
        <td class="bold">target_dir_1w</td>
        <td>Класс</td>
        <td><code>1 if target_return_1w > 0 else 0</code></td>
        <td>Направление недельного тренда (1 = Up, 0 = Down)</td>
      </tr>
      <tr>
        <td class="bold">target_status_1d / 1w</td>
        <td>Фильтр</td>
        <td><code>OK</code>, <code>MARKET_HALT</code>, <code>SUSPENDED</code>, <code>PENDING</code></td>
        <td>Флаг валидности цены (исключает остановки и слияния)</td>
      </tr>
    </tbody>
  </table>

  <div class="callout">
    <div class="callout-title">&#9888; Важное методическое правило:</div>
    Синтетическая «уверенность» строго исключена из обучающих таргетов. Модель обучается предсказывать доходность (регрессия) и вероятность роста <code>p_up &isin; [0, 1]</code> (классификация). Калиброванная уверенность вычисляется на этапе инференса: <code>confidence = max(p_up, 1 - p_up) &times; 100%</code>.
  </div>

  <!-- SECTION 5 -->
  <h2><span class="num">5</span> Хронологические выборки для обучения (Splits)</h2>
  
  <table>
    <thead>
      <tr>
        <th>Выборка</th>
        <th>Период дат</th>
        <th>Строк</th>
        <th>Доля</th>
        <th>Рыночный режим в данных</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="bold">train.parquet</td>
        <td>17.11.2011 &mdash; 30.12.2022</td>
        <td>166 404</td>
        <td>~53%</td>
        <td>Кризис 2014 г. (ставка 17%), COVID-2020 (ставка 4.25%), шок февраля 2022 г.</td>
      </tr>
      <tr>
        <td class="bold">val.parquet</td>
        <td>03.01.2023 &mdash; 30.12.2024</td>
        <td>70 553</td>
        <td>~22%</td>
        <td>Восстановление рынка, цикл жесткой ДКП (рост ключевой ставки с 7.5% до 21.0%)</td>
      </tr>
      <tr>
        <td class="bold">test.parquet</td>
        <td>03.01.2025 &mdash; 23.11.2026</td>
        <td>76 675</td>
        <td>~25%</td>
        <td>Чистый Out-of-Sample контроль в условиях сверхвысоких ставок</td>
      </tr>
    </tbody>
  </table>

  <!-- SECTION 6 -->
  <h2><span class="num">6</span> Быстрый старт: загрузка данных в Python</h2>

  <pre><span class="kw">import</span> pandas <span class="kw">as</span> pd

<span class="com"># 1. Загрузка готовой обучающей выборки</span>
train = pd.<span class="fn">read_parquet</span>(<span class="str">r"moex_banking_dataset\feature_store_v2\train.parquet"</span>)

<span class="com"># 2. Оставляем только строки с подтвержденными целями (без остановок торгов)</span>
train_clean = train[train[<span class="str">"target_status_1d"</span>] == <span class="str">"OK"</span>]

<span class="com"># 3. Список проверенных признаков для модели 1D</span>
features = [
    <span class="str">"return_1h"</span>, <span class="str">"return_4h"</span>, <span class="str">"return_1d"</span>,
    <span class="str">"peer_banks_return_1h"</span>, <span class="str">"peer_relative_lag_1h"</span>,
    <span class="str">"tod_volume_ratio"</span>, <span class="str">"return_from_day_open"</span>, <span class="str">"opening_gap"</span>,
    <span class="str">"ofz_curve_slope_10y_1y"</span>, <span class="str">"key_rate_pct"</span>, <span class="str">"rsi_14"</span>, <span class="str">"natr_14"</span>
]

X_train = train_clean[features]
y_return = train_clean[<span class="str">"target_return_1d"</span>]  <span class="com"># Для регрессии цены P_t * (1 + r)</span>
y_direction = train_clean[<span class="str">"target_dir_1d"</span>] <span class="com"># Для классификатора направления (0/1)</span>
</pre>

  <div class="footer-note">
    <span>Проект: Machine Learning на Московской бирже &bull; Сектор: Финансы и банки</span>
    <span>Дата формирования документа: 24 ноября 2026 г. &bull; Версия 2.0</span>
  </div>

</body>
</html>
"""

def generate_pdf():
    print("Writing HTML template...", flush=True)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)
        
    print(f"Compiling PDF via Headless Edge to {PDF_FILE}...", flush=True)
    cmd = [
        EDGE_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_FILE}",
        HTML_FILE.resolve().as_uri()
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    time.sleep(2)
    
    if PDF_FILE.exists() and PDF_FILE.stat().st_size > 1000:
        print(f"SUCCESS! PDF created: {PDF_FILE} ({PDF_FILE.stat().st_size:,} bytes)")
        # Clean temp html
        HTML_FILE.unlink(missing_ok=True)
        return True
    else:
        print(f"Error creating PDF: {res.stderr}")
        return False

if __name__ == "__main__":
    generate_pdf()

# market-base-rates

Reproducible base rates for the US stock market, computed from primary data
with plain pandas: long-run returns, what followed high CAPE readings, the cost
of missing the best days, what happened to people who waited in cash,
drawdown frequency, buying at all-time highs, the real yield on cash, and
lump sum vs dollar-cost averaging.

Every number in this README is produced by `python run_all.py` from the files
in `data/` and lands first in `results/*.csv`; nothing is typed in by hand.
There are no forecasts and no recommendations here, only distributions and
counts, with the caveats spelled out in
[What this does and does not show](#what-this-does-and-does-not-show).

## Reproduce

```bash
git clone https://github.com/poyraz-demir/market-base-rates.git && cd market-base-rates
python -m venv .venv && . .venv/bin/activate
pip install pandas openpyxl xlrd          # or: pip install -e ".[dev]"
python fetch.py                           # downloads the Yahoo Finance daily series into data/cache/
python run_all.py                         # writes results/*.csv, results/SUMMARY.md and refreshes this README
python docs/build_site.py                 # rebuilds the static page docs/index.html from results/
pytest                                    # smoke tests + a few known numbers with tolerances
```

Python 3.10+. Dependencies: `pandas`, `openpyxl` (xlsx), `xlrd` (Shiller's .xls).
`yfinance` is optional (`python fetch.py --yfinance`).

Each script also runs on its own and prints its tables:
`python scripts/05_drawdowns.py`.

## Data

| Data | Used by | In the repo? |
|---|---|---|
| Robert Shiller, `ie_data.xls` (monthly S&P composite, dividends, earnings, CPI, CAPE; 1871-) | 02 | yes, `data/raw/ie_data.xls` |
| Aswath Damodaran, `histretSP.xlsx` (annual returns on stocks, bills, bonds, gold, real estate; 1928-) | 01 | yes, `data/raw/histretSP.xlsx` |
| FRED: `DGS3MO`, `DGS30`, `T10YIE`, `ECBDFR`, `ECBMRRFR`, `CPIAUCSL`, `CPIAUCNS` | 04, 07, 08 | yes, `data/raw/fred/` |
| Yahoo Finance daily: `^GSPC` (price, 1927-), `^SP500TR` (total return, 1988-), `SPY` (adjusted close, 1993-) | 03, 04, 05, 06, 08 | **no** - `python fetch.py` puts them in `data/cache/` |

Sources, download dates and redistribution terms: [`data/SOURCES.md`](data/SOURCES.md).
Yahoo Finance series are not redistributed; only derived tables are committed.
Daily series are truncated at `DATA_END` (see `scripts/common.py`) so a fresh
download reproduces the published tables.

## Scripts

| Script | What it computes |
|---|---|
| `01_long_run_returns.py` | S&P 500 CAGR over 10/20/30/50/98 years, nominal and real; rolling 10-year distribution; other asset classes |
| `02_cape_forward_returns.py` | Forward 1/3/5/10-year real and nominal returns after CAPE 25-30, >30, >35, >40; independent-episode count; 1929 & 1997-2002 vs 2017-2021 |
| `03_missing_best_days.py` | CAGR without the 10/20/30/50/100 best days, without the worst days, without both; where the best days sit |
| `04_waiting_in_cash.py` | Cash vs buy & hold from 1996-12, 2014-01, 2018-01, 2021-01, 2025-01; was cash ever ahead; "wait for a 10/20/30 % dip" |
| `05_drawdowns.py` | Frequency of 5/10/20/30/50 % declines, peak-to-peak durations, every >=20 % episode, intra-year drawdowns |
| `06_near_ath.py` | Share of days near the all-time high; forward returns after buying at a high vs any day |
| `07_cash_real_yield.py` | Real 3-month T-bill yield now vs 2021 and by decade; share of months with negative real yield |
| `08_lump_sum_vs_dca.py` | Lump sum vs 3/6/12-month DCA over rolling 12-month windows, with and without interest on the uninvested cash |

## Results

<!-- generated:start -->
_Daily series end 2026-09-18; Shiller monthly data through 2026-09 (September price = 1 September close, recent CPI months estimated by Shiller); Damodaran annual data through 2025; FRED CPI through 2026-08. Generated 2026-09-21 by `python run_all.py`._

### 1. Long-run returns

#### S&P 500 CAGR by window (Damodaran annual data)

| window | years | nominal_cagr | real_cagr | inflation_cagr |
|---|---|---|---|---|
| 2016-2025 | 10 | 14.68% | 11.12% | 3.20% |
| 2006-2025 | 20 | 10.90% | 8.17% | 2.53% |
| 1996-2025 | 30 | 10.26% | 7.54% | 2.52% |
| 1976-2025 | 50 | 11.92% | 8.04% | 3.59% |
| 1928-2025 | 98 | 10.02% | 6.78% | 3.04% |

#### Rolling 10-year nominal CAGR, all windows

| windows | median | min | min_window | max | max_window | share_negative | share_negative_real |
|---|---|---|---|---|---|---|---|
| 89 | 10.96% | -1.67% | 1929-1938 | 20.11% | 1949-1958 | 5.62% | 12.36% |

#### Calendar-year returns

| years | negative_years | share_negative | worst_year | worst_return | best_year | best_return |
|---|---|---|---|---|---|---|
| 98 | 26 | 26.53% | 1931 | -43.84% | 1954 | 52.56% |


### 2. CAPE and forward returns

#### Where CAPE stands

| month | cape | cape_median_all | cape_mean_all | percentile | months_above_current | months_with_cape | peak_cape | peak_month |
|---|---|---|---|---|---|---|---|---|
| 2026-09 | 40.58 | 16.61 | 17.79 | 98.80% | 20 | 1,749 | 44.20 | 1999-12 |

#### Forward REAL annualised return by CAPE bucket (overlapping monthly windows)

| bucket | months_in_bucket | horizon_years | n | median | mean | worst | best | p25 | p75 | share_negative |
|---|---|---|---|---|---|---|---|---|---|---|
| all | 1,749 | 1 | 1,737 | 8.69% | 8.46% | -58.12% | 151.31% | -3.79% | 20.09% | 31.61% |
| all | 1,749 | 3 | 1,713 | 7.31% | 7.20% | -35.21% | 39.23% | 1.09% | 13.31% | 22.42% |
| all | 1,749 | 5 | 1,689 | 7.21% | 6.98% | -13.23% | 33.35% | 1.79% | 11.71% | 19.83% |
| all | 1,749 | 10 | 1,629 | 6.61% | 6.73% | -5.92% | 19.96% | 3.50% | 10.38% | 11.85% |
| cape_25_30 | 147 | 1 | 147 | 8.97% | 8.05% | -39.29% | 46.38% | 0.60% | 17.42% | 23.81% |
| cape_25_30 | 147 | 3 | 146 | 8.38% | 5.06% | -35.21% | 26.84% | -1.44% | 12.01% | 26.71% |
| cape_25_30 | 147 | 5 | 133 | 5.19% | 4.16% | -10.98% | 15.61% | -1.93% | 10.61% | 39.85% |
| cape_25_30 | 147 | 10 | 108 | 5.57% | 5.81% | -1.15% | 11.75% | 4.90% | 6.45% | 4.63% |
| cape_gt30 | 137 | 1 | 125 | 7.85% | 4.02% | -29.79% | 31.17% | -11.85% | 17.88% | 35.20% |
| cape_gt30 | 137 | 3 | 102 | 3.56% | 1.56% | -26.86% | 18.18% | -4.99% | 10.21% | 38.24% |
| cape_gt30 | 137 | 5 | 91 | -0.88% | 1.22% | -13.23% | 11.14% | -4.05% | 6.94% | 53.85% |
| cape_gt30 | 137 | 10 | 57 | -1.13% | -1.02% | -5.92% | 4.49% | -3.13% | 0.61% | 59.65% |
| cape_gt35 | 71 | 1 | 59 | 4.57% | 0.24% | -29.79% | 23.82% | -14.99% | 14.02% | 45.76% |
| cape_gt35 | 71 | 3 | 47 | -4.81% | -4.62% | -17.11% | 8.18% | -12.86% | 3.52% | 61.70% |
| cape_gt35 | 71 | 5 | 42 | -3.98% | -1.57% | -5.80% | 8.93% | -4.57% | -2.08% | 80.95% |
| cape_gt35 | 71 | 10 | 34 | -3.03% | -2.58% | -5.92% | 1.08% | -3.54% | -1.29% | 85.29% |
| cape_gt40 | 26 | 1 | 21 | -3.12% | -4.29% | -29.79% | 12.50% | -16.94% | 7.85% | 52.38% |
| cape_gt40 | 26 | 3 | 21 | -13.27% | -12.06% | -17.11% | -4.19% | -14.29% | -9.71% | 100.00% |
| cape_gt40 | 26 | 5 | 21 | -4.53% | -4.35% | -5.41% | -2.75% | -4.66% | -4.20% | 100.00% |
| cape_gt40 | 26 | 10 | 21 | -3.45% | -3.69% | -5.92% | -2.55% | -4.41% | -3.03% | 100.00% |

#### How many INDEPENDENT episodes are behind those n (months with a full 10-year outcome)

| bucket | run_start | run_end | months | median_real_10y | median_nom_10y |
|---|---|---|---|---|---|
| cape_gt30 | 1929-08 | 1929-09 | 2 | -1.62% | -3.72% |
| cape_gt30 | 1997-06 | 2001-08 | 51 | -1.79% | 0.98% |
| cape_gt30 | 2001-11 | 2002-01 | 3 | 0.32% | 2.79% |
| cape_gt30 | 2002-03 | 2002-03 | 1 | 1.32% | 3.88% |
| cape_gt35 | 1998-03 | 1998-08 | 6 | 0.69% | 3.60% |
| cape_gt35 | 1998-11 | 2001-02 | 28 | -3.15% | -0.78% |
| cape_gt40 | 1999-01 | 2000-09 | 21 | -3.45% | -0.97% |

#### CAPE > 30 entries split by regime, REAL annualised

| regime | horizon_years | n | median | mean | worst | best | share_negative |
|---|---|---|---|---|---|---|---|
| 1929 & 1997-2002 | 1 | 57 | 4.13% | -0.39% | -29.79% | 29.35% | 49.12% |
| 1929 & 1997-2002 | 3 | 57 | -4.19% | -4.22% | -26.86% | 17.36% | 68.42% |
| 1929 & 1997-2002 | 5 | 57 | -3.04% | -2.89% | -13.23% | 3.55% | 85.96% |
| 2017-2021 | 1 | 68 | 9.87% | 7.72% | -21.30% | 31.17% | 23.53% |
| 2017-2021 | 3 | 45 | 6.77% | 8.88% | 3.01% | 18.18% | 0.00% |
| 2017-2021 | 5 | 34 | 7.91% | 8.11% | 5.09% | 11.14% | 0.00% |

#### Every stretch of months with CAPE > 40

| run_start | run_end | months |
|---|---|---|
| 1999-01 | 2000-09 | 21 |
| 2026-05 | 2026-09 | 5 |


### 3. Missing the best days

#### Missing the best / worst days (CAGR over the same calendar span)

| series | scenario | multiple | cagr |
|---|---|---|---|
| S&P 500 price (no dividends) | buy and hold | 433.21x | 6.34% |
| S&P 500 price (no dividends) | without 10 best days | 143.24x | 5.16% |
| S&P 500 price (no dividends) | without 20 best days | 59.72x | 4.23% |
| S&P 500 price (no dividends) | without 30 best days | 27.96x | 3.43% |
| S&P 500 price (no dividends) | without 50 best days | 7.50x | 2.06% |
| S&P 500 price (no dividends) | without 50 worst days | 29327.97x | 10.98% |
| S&P 500 price (no dividends) | without 100 best days | 0.61x | -0.51% |
| S&P 500 price (no dividends) | without 50 best and 50 worst days | 507.90x | 6.51% |
| S&P 500 total return | buy and hold | 67.00x | 11.48% |
| S&P 500 total return | without 10 best days | 29.81x | 9.17% |
| S&P 500 total return | without 20 best days | 17.28x | 7.64% |
| S&P 500 total return | without 30 best days | 10.85x | 6.35% |
| S&P 500 total return | without 50 best days | 4.85x | 4.17% |
| S&P 500 total return | without 50 worst days | 1197.10x | 20.10% |
| S&P 500 total return | without 100 best days | 0.93x | -0.18% |
| S&P 500 total return | without 50 best and 50 worst days | 86.72x | 12.22% |
| SPY ETF adjusted close (after fees) | buy and hold | 31.67x | 10.82% |
| SPY ETF adjusted close (after fees) | without 10 best days | 13.74x | 8.10% |
| SPY ETF adjusted close (after fees) | without 20 best days | 7.94x | 6.35% |
| SPY ETF adjusted close (after fees) | without 30 best days | 4.97x | 4.88% |
| SPY ETF adjusted close (after fees) | without 50 best days | 2.22x | 2.40% |
| SPY ETF adjusted close (after fees) | without 50 worst days | 534.70x | 20.53% |
| SPY ETF adjusted close (after fees) | without 100 best days | 0.43x | -2.45% |
| SPY ETF adjusted close (after fees) | without 50 best and 50 worst days | 37.55x | 11.38% |

#### Where the 50 best days sit

| series | best_days | in_drawdown_gt20 | in_drawdown_gt10 | within_5_days_of_a_worst_day |
|---|---|---|---|---|
| S&P 500 price (no dividends) | 50 | 47 | 49 | 27 |
| S&P 500 total return | 50 | 30 | 44 | 31 |
| SPY ETF adjusted close (after fees) | 50 | 28 | 42 | 30 |


### 4. Waiting in cash

#### Moved to 3-month T-bills on that date vs invested the same day (S&P 500 TR), nominal

| start | reason | years | stocks_multiple | stocks_cagr | cash_multiple | cash_cagr | cash_shortfall |
|---|---|---|---|---|---|---|---|
| 1996-12-05 | Greenspan 'irrational exuberance' speech | 29.79 | 17.55x | 10.10% | 1.96x | 2.28% | 88.86% |
| 2014-01-02 |  | 12.71 | 5.22x | 13.88% | 1.28x | 1.97% | 75.45% |
| 2018-01-02 |  | 8.71 | 3.26x | 14.55% | 1.26x | 2.73% | 61.27% |
| 2021-01-04 |  | 5.70 | 2.24x | 15.22% | 1.21x | 3.40% | 46.08% |
| 2025-01-02 |  | 1.71 | 1.33x | 18.24% | 1.07x | 4.02% | 19.66% |

#### Same, CPI-deflated

| start | inflation_multiple | stocks_real_multiple | stocks_real_cagr | cash_real_multiple | cash_real_cagr |
|---|---|---|---|---|---|
| 1996-12-05 | 2.10x | 8.36x | 7.39% | 0.93x | -0.24% |
| 2014-01-02 | 1.42x | 3.68x | 10.78% | 0.90x | -0.81% |
| 2018-01-02 | 1.34x | 2.43x | 10.74% | 0.94x | -0.69% |
| 2021-01-04 | 1.27x | 1.76x | 10.46% | 0.95x | -0.88% |
| 2025-01-02 | 1.05x | 1.27x | 15.07% | 1.02x | 1.23% |

#### Was cash ever ahead?

| start | min_stocks_to_cash | min_date | last_day_cash_ahead | share_of_days_cash_ahead |
|---|---|---|---|---|
| 1996-12-05 | 0.74 | 2009-03-09 | 2009-07-14 | 3.52% |
| 2014-01-02 | 0.95 | 2014-02-03 | 2014-04-11 | 0.59% |
| 2018-01-02 | 0.83 | 2020-03-23 | 2020-04-07 | 4.79% |
| 2021-01-04 | 0.98 | 2022-10-12 | 2022-10-14 | 0.49% |
| 2025-01-02 | 0.84 | 2025-04-08 | 2025-06-05 | 15.38% |

#### Stay in T-bills until the index is X % below its running high since the start date, then go all in (final multiple; blank entry = never triggered)

| start | invest_immediately | wait_for_10pct | wait_for_10pct_vs_immediate | wait_for_20pct | wait_for_20pct_vs_immediate | wait_for_30pct | wait_for_30pct_vs_immediate |
|---|---|---|---|---|---|---|---|
| 1996-12-05 | 17.55x | 15.34x | -12.59% | 12.94x | -26.27% | 14.88x | -15.23% |
| 2014-01-02 | 5.22x | 4.89x | -6.39% | 3.59x | -31.16% | 3.86x | -25.96% |
| 2018-01-02 | 3.26x | 3.41x | 4.44% | 3.54x | 8.61% | 3.81x | 16.83% |
| 2021-01-04 | 2.24x | 1.90x | -15.35% | 2.18x | -3.06% | 1.21x | -46.08% |
| 2025-01-02 | 1.33x | 1.42x | 6.88% | 1.07x | -19.66% | 1.07x | -19.66% |


### 5. Drawdowns

#### Drawdown base rates, S&P 500 price index (calendar days)

| threshold | episodes | years_per_episode | median_depth | worst_depth | median_peak_to_trough_days | median_trough_to_recovery_days | median_full_cycle_days | mean_full_cycle_years | max_full_cycle_years |
|---|---|---|---|---|---|---|---|---|---|
| 5.0% | 73 | 1.4 | -8.2% | -86.2% | 34 | 49 | 84 | 1.1 | 25.0 |
| 10.0% | 26 | 3.8 | -19.8% | -86.2% | 179 | 150 | 433 | 2.6 | 25.0 |
| 20.0% | 12 | 8.2 | -33.7% | -86.2% | 481 | 532 | 764 | 5.0 | 25.0 |
| 30.0% | 7 | 14.1 | -48.2% | -86.2% | 543 | 1,480 | 1,997 | 7.3 | 25.0 |
| 50.0% | 2 | 49.4 | -71.5% | -86.2% | 753 | 4,814 | 5,567 | 15.2 | 25.0 |

#### Every decline of 20 % or more

| peak | trough | depth | peak_to_trough_days | recovery | full_cycle_years |
|---|---|---|---|---|---|
| 1929-09-16 | 1932-06-01 | -86.2% | 989 | 1954-09-22 | 25.0 |
| 1956-08-03 | 1957-10-22 | -21.5% | 445 | 1958-09-24 | 2.1 |
| 1961-12-12 | 1962-06-26 | -28.0% | 196 | 1963-09-03 | 1.7 |
| 1966-02-09 | 1966-10-07 | -22.2% | 240 | 1967-05-04 | 1.2 |
| 1968-11-29 | 1970-05-26 | -36.1% | 543 | 1972-03-06 | 3.3 |
| 1973-01-11 | 1974-10-03 | -48.2% | 630 | 1980-07-17 | 7.5 |
| 1980-11-28 | 1982-08-12 | -27.1% | 622 | 1982-11-03 | 1.9 |
| 1987-08-25 | 1987-12-04 | -33.5% | 101 | 1989-07-26 | 1.9 |
| 2000-03-24 | 2002-10-09 | -49.1% | 929 | 2007-05-30 | 7.2 |
| 2007-10-09 | 2009-03-09 | -56.8% | 517 | 2013-03-28 | 5.5 |
| 2020-02-19 | 2020-03-23 | -33.9% | 33 | 2020-08-18 | 0.5 |
| 2022-01-03 | 2022-10-12 | -25.4% | 282 | 2024-01-19 | 2.0 |

#### Share of trading days spent below the running high

| period | days | below_high_by_10pct_or_more | below_high_by_20pct_or_more | below_high_by_30pct_or_more |
|---|---|---|---|---|
| full history | 24,796 | 52.0% | 36.4% | 25.5% |
| last 50 years | 12,603 | 38.5% | 18.4% | 6.2% |
| last 30 years | 7,547 | 42.0% | 24.3% | 10.1% |
| last 20 years | 5,031 | 32.8% | 14.8% | 7.0% |

#### Intra-year drawdowns (complete calendar years)

| period | years | mean_intra_year_drawdown | median_intra_year_drawdown | positive_calendar_years | share_years_dd_ge_5pct | share_years_dd_ge_10pct | share_years_dd_ge_15pct | share_years_dd_ge_20pct |
|---|---|---|---|---|---|---|---|---|
| 1928-2025 | 98 | -16.3% | -13.1% | 66 | 93.9% | 62.2% | 39.8% | 25.5% |
| 1980-2025 | 46 | -14.1% | -10.2% | 35 | 93.5% | 52.2% | 37.0% | 15.2% |


### 6. Buying at all-time highs

#### How often the price index sits near its all-time high

| period | days | new_high_days | share_new_high | within_1pct | within_2pct | within_5pct | within_10pct | below_high_gt20pct |
|---|---|---|---|---|---|---|---|---|
| full history | 24,796 | 1,463 | 5.9% | 15.9% | 22.8% | 36.1% | 48.0% | 36.4% |
| last 50 years | 12,603 | 982 | 7.8% | 21.4% | 31.0% | 48.1% | 61.5% | 18.4% |
| last 30 years | 7,547 | 630 | 8.3% | 23.1% | 31.5% | 45.2% | 58.0% | 24.3% |
| last 20 years | 5,031 | 478 | 9.5% | 28.2% | 37.9% | 52.3% | 67.2% | 14.8% |

#### Forward 1-year return after buying at an all-time high vs any day (S&P 500 total return, 1988-)

| entry | n | mean | median | share_negative | p5 | p95 | worst |
|---|---|---|---|---|---|---|---|
| random day | 9,499 | 12.66% | 14.38% | 16.81% | -18.73% | 35.73% | -47.50% |
| new all-time high day | 764 | 13.78% | 15.85% | 14.40% | -9.75% | 32.09% | -35.70% |
| within 1% of high | 2,154 | 13.23% | 14.96% | 13.83% | -9.63% | 31.88% | -40.90% |
| within 5% of high | 4,676 | 12.71% | 14.04% | 15.18% | -12.76% | 33.40% | -43.49% |
| 10%+ below high | 3,605 | 12.60% | 14.60% | 16.59% | -22.64% | 37.35% | -47.50% |
| 20%+ below high | 1,987 | 12.87% | 13.30% | 14.75% | -20.76% | 38.90% | -33.36% |

#### Same, price index 1928- (no dividends)

| entry | n | mean | median | share_negative | p5 | p95 | worst |
|---|---|---|---|---|---|---|---|
| random day | 24,544 | 8.21% | 9.55% | 30.13% | -24.72% | 37.70% | -71.07% |
| new all-time high day | 1,422 | 8.23% | 9.85% | 28.97% | -17.41% | 31.21% | -37.07% |
| within 1% of high | 3,817 | 8.14% | 9.22% | 28.79% | -16.05% | 30.98% | -42.15% |
| within 5% of high | 8,719 | 8.07% | 8.57% | 29.30% | -16.03% | 32.08% | -44.71% |
| 10%+ below high | 12,891 | 8.40% | 10.44% | 30.40% | -32.03% | 41.20% | -71.07% |
| 20%+ below high | 9,035 | 8.00% | 9.67% | 31.38% | -34.71% | 44.67% | -71.07% |


### 7. Real yield on cash

#### Real yield on cash now vs 2021

| as_of | basis | nominal | cpi_yoy | real |
|---|---|---|---|---|
| 2026-09-17 | latest daily 3m yield, latest CPI y/y | 4.12% | 3.35% | 0.74% |
| 2026-08 | monthly average 3m yield, same-month CPI y/y | 3.88% | 3.35% | 0.51% |
| 2021 average | monthly averages | 0.05% | 4.68% | -4.40% |
| 2010-2019 average | monthly averages | 0.58% | 1.77% | -1.17% |

#### Real yield on 3-month T-bills by period (monthly, 1982-)

| period | months | mean_nominal | mean_cpi_yoy | mean_real | min_real | max_real | share_months_real_negative |
|---|---|---|---|---|---|---|---|
| 1982-1989 | 96 | 8.13% | 3.96% | 4.02% | 1.30% | 7.11% | 0.00% |
| 1990-1999 | 120 | 4.99% | 3.01% | 1.93% | -0.34% | 3.74% | 5.83% |
| 2000-2009 | 120 | 2.76% | 2.57% | 0.19% | -3.64% | 3.59% | 41.67% |
| 2010-2019 | 120 | 0.58% | 1.77% | -1.17% | -3.66% | 0.92% | 86.67% |
| 2009-2021 | 156 | 0.49% | 1.80% | -1.27% | -6.64% | 2.19% | 83.33% |
| 2021 | 12 | 0.05% | 4.68% | -4.40% | -6.64% | -1.27% | 100.00% |
| 2022 | 12 | 2.08% | 8.00% | -5.47% | -7.48% | -1.92% | 100.00% |
| 2023-2026-08 | 43 | 4.70% | 3.28% | 1.38% | -1.54% | 2.62% | 11.63% |
| 1982-2026-08 | 535 | 3.76% | 2.94% | 0.80% | -7.48% | 7.11% | 37.76% |

#### Share of months with a negative real cash yield

| period | months | share_months_real_negative | mean_real |
|---|---|---|---|
| 1982-1989 | 96 | 0.00% | 4.02% |
| 1990-1999 | 120 | 5.83% | 1.93% |
| 2000-2008 | 108 | 44.44% | 0.16% |
| 2009-2021 | 156 | 83.33% | -1.27% |
| 2010-2019 | 120 | 86.67% | -1.17% |
| 2022-2026-08 | 55 | 30.91% | -0.11% |
| 1982-2008 | 324 | 16.98% | 1.96% |


### 8. Lump sum vs dollar-cost averaging

#### Lump sum vs spreading the purchase (S&P 500 TR, monthly entries 1988-, wealth after 12 months)

| dca_months | uninvested_cash | windows | ls_beats_dca | median_ls_minus_dca | ls_p5 | dca_p5 | ls_median | dca_median | dca_beats_all_cash |
|---|---|---|---|---|---|---|---|---|---|
| 3 | cash earns 3m T-bill | 453 | 64.9% | 1.2% | 0.815x | 0.828x | 1.144x | 1.129x | 80.1% |
| 3 | cash earns 0% | 453 | 66.9% | 1.5% | 0.815x | 0.827x | 1.144x | 1.127x | 80.1% |
| 6 | cash earns 3m T-bill | 453 | 70.4% | 2.4% | 0.815x | 0.862x | 1.144x | 1.117x | 79.5% |
| 6 | cash earns 0% | 453 | 74.8% | 3.0% | 0.815x | 0.860x | 1.144x | 1.108x | 77.7% |
| 12 | cash earns 3m T-bill | 453 | 76.6% | 4.9% | 0.815x | 0.905x | 1.144x | 1.089x | 77.7% |
| 12 | cash earns 0% | 453 | 80.4% | 6.3% | 0.815x | 0.887x | 1.144x | 1.077x | 74.4% |

<!-- generated:end -->

## What this does and does not show

- **Overlapping windows.** All forward-return tables (scripts 02, 06, 08) use
  monthly or daily start dates, so consecutive windows share almost their whole
  path. `n` counts windows, not independent observations. Script 02 lists the
  contiguous runs behind each CAPE bucket: the CAPE > 30 ten-year statistics
  come from four runs, the CAPE > 35 ones from two runs inside the dot-com
  bubble, and **CAPE > 40 is a single episode (1999-2000) counted 21 times**.
  Non-overlapping variants (e.g. January entries only) leave too few
  observations to describe a distribution, which is why the overlapping
  tables are shown together with the episode count.
- **Two regimes, one bucket.** CAPE > 30 entries in 1929 and 1997-2002 were
  followed by negative real returns; CAPE > 30 entries in 2017-2021 were
  followed by strongly positive ones. The pooled median describes neither.
  58 % of CAPE > 30 months (entries from mid-2017 on) do not have a ten-year
  outcome yet.
- **Daily total return only from 1988.** Scripts 03, 05 and 06 use the
  price-only `^GSPC` series before 1988 (no dividends), which understates
  absolute returns by roughly 3-4 percentage points a year but barely affects
  comparisons within one series. The 1929-1954 "25-year recovery" is
  nominal, price-only; with dividends reinvested and 1930s deflation the real
  recovery came earlier.
- **Cash series only from September 1981** (start of FRED `DGS3MO`), so the
  real-cash-yield history (07) starts in 1982 and the waiting-in-cash cases
  (04) cannot go back further. `TB3MS`/`DTB3` were not obtained.
- **Missing best days vs missing worst days** are symmetric calculations;
  the asymmetry people quote exists because best and worst days cluster in
  the same crashes (27-31 of the 50 best days sit within 5 trading days of
  one of the 50 worst, depending on the series).
- **No taxes, no fees, no slippage** anywhere except the SPY series (which is
  net of the fund's expense ratio).
- **Recent CPI in Shiller's file is estimated by the author** for the last
  few months; the September price is the 1 September close. FRED CPI runs
  through August 2026.
- **Lump sum vs DCA (08)** follows the design of Vanguard's 2023 paper but on
  a different index and period (S&P 500 total return from 1988 vs Russell 3000
  and MSCI World from 1976-79), so hit ratios are comparable in spirit, not
  identical.
- **Not obtained**, so not reproduced here: Vanguard 2012 "Dollar-Cost
  Averaging Just Means Taking Risk Later" (links dead), DALBAR QAIB and
  Morningstar "Mind the Gap" (paywalled / blocked), Hartford Funds / Ned
  Davis "missing the best days" tables (403), S&P Dow Jones Indices' own
  100-year total-return series (403).

## Layout

```
fetch.py            downloads what is not committed (Yahoo daily series; --raw refreshes the rest)
run_all.py          runs every script, writes results/ and the README block above
scripts/common.py   loaders, DATA_END, cash index, markdown table helper
scripts/0N_*.py     one topic per script, each runnable on its own
data/raw/           committed source snapshots (see data/SOURCES.md)
data/cache/         Yahoo Finance series, git-ignored
results/            CSV tables + SUMMARY.md (all tables, including the ones not shown above)
docs/               build_site.py renders docs/index.html, a static page, from results/ (python docs/build_site.py)
tests/              smoke tests and a few pinned numbers
```

## License

Code: MIT (see `LICENSE`). Data: each source keeps its own terms, listed in
`data/SOURCES.md`. This repository is not investment advice.

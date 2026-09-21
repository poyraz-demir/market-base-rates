"""04 - "I'll wait for a pullback": cash vs buy & hold from specific dates.

Outputs (results/):
  04_waiting_nominal.csv   stocks vs cash from each start date, nominal
  04_waiting_real.csv      same deflated by CPI
  04_was_cash_ever_ahead.csv  minimum of stocks/cash ratio, last day cash was ahead, share of days
  04_wait_for_dip.csv      "stay in T-bills until the index is X% below its running high, then go all in"

Method: stocks = S&P 500 total return index (dividends reinvested, no taxes/fees).
Cash = daily index compounded from the 3-month T-bill yield (FRED DGS3MO):
cash[i] = cash[i-1] * (1 + y[i-1]/100) ** (days/365). Real values deflate by
CPIAUCSL (start month -> last available month). End date = DATA_END.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_END, cash_index, load_daily, load_fred, print_table, save, years_between  # noqa: E402

STARTS = {"1996-12-05": "Greenspan 'irrational exuberance' speech",
          "2014-01-02": "", "2018-01-02": "", "2021-01-04": "", "2025-01-02": ""}
DIPS = [0.10, 0.20, 0.30]


def main(verbose=True) -> dict:
    tr = load_daily("SP500TR")
    cash = cash_index(load_fred("DGS3MO"))
    cash = cash.reindex(tr.index, method="ffill")     # align to trading days
    cpi = load_fred("CPIAUCSL")
    end = tr.index[-1]
    cpi_end = cpi.iloc[-1]

    nominal, real, ahead, dips = [], [], [], []
    for s, why in STARTS.items():
        s = pd.Timestamp(s)
        s = tr.index[tr.index.searchsorted(s)]           # first trading day on/after
        yrs = years_between(s, end)
        mx = tr[end] / tr[s]
        mc = cash[end] / cash[s]
        nominal.append({"start": s, "reason": why, "years": yrs,
                        "stocks_multiple": mx, "stocks_cagr": mx ** (1 / yrs) - 1,
                        "cash_multiple": mc, "cash_cagr": mc ** (1 / yrs) - 1,
                        "stocks_100k": 100_000 * mx, "cash_100k": 100_000 * mc,
                        "cash_shortfall": 1 - mc / mx})
        infl = cpi_end / cpi[cpi.index <= s].iloc[-1]
        real.append({"start": s, "inflation_multiple": infl,
                     "stocks_real_multiple": mx / infl, "stocks_real_cagr": (mx / infl) ** (1 / yrs) - 1,
                     "cash_real_multiple": mc / infl, "cash_real_cagr": (mc / infl) ** (1 / yrs) - 1})
        ratio = (tr[s:] / tr[s]) / (cash[s:] / cash[s])
        was_ahead = ratio < 1
        ahead.append({"start": s, "min_stocks_to_cash": ratio.min(), "min_date": ratio.idxmin(),
                      "last_day_cash_ahead": ratio[was_ahead].index[-1] if was_ahead.any() else pd.NaT,
                      "share_of_days_cash_ahead": was_ahead.mean()})
        row = {"start": s, "invest_immediately": mx}
        path = tr[s:]
        dd = path / path.cummax() - 1
        for d in DIPS:
            hit = dd[dd <= -d]
            if hit.empty:
                row[f"wait_for_{int(d*100)}pct"] = mc
                row[f"wait_for_{int(d*100)}pct_entry"] = pd.NaT
            else:
                e = hit.index[0]
                m = (cash[e] / cash[s]) * (tr[end] / tr[e])
                row[f"wait_for_{int(d*100)}pct"] = m
                row[f"wait_for_{int(d*100)}pct_entry"] = e
            row[f"wait_for_{int(d*100)}pct_vs_immediate"] = row[f"wait_for_{int(d*100)}pct"] / mx - 1
        dips.append(row)

    nominal, real, ahead, dips = map(pd.DataFrame, (nominal, real, ahead, dips))
    out = {"04_waiting_nominal": nominal, "04_waiting_real": real,
           "04_was_cash_ever_ahead": ahead, "04_wait_for_dip": dips}
    for name, df in out.items():
        save(df, name + ".csv")
    if verbose:
        print(f"S&P 500 TR {tr.index[0]:%Y-%m-%d} -> {end:%Y-%m-%d}; CPI through {cpi.index[-1]:%Y-%m}")
        print_table("Cash vs stocks, nominal", nominal,
                    {"start": "date", "years": "num", "stocks_multiple": "x", "cash_multiple": "x",
                     "stocks_100k": "num", "cash_100k": "num"})
        print_table("Cash vs stocks, real (CPI-deflated)", real,
                    {"start": "date", "inflation_multiple": "x", "stocks_real_multiple": "x", "cash_real_multiple": "x"})
        print_table("Was cash ever ahead?", ahead,
                    {"start": "date", "min_stocks_to_cash": "num", "min_date": "date", "last_day_cash_ahead": "date"})
        print_table("Wait for a dip, then go all in (final multiples)", dips,
                    {"start": "date", "invest_immediately": "x",
                     **{f"wait_for_{int(d*100)}pct": "x" for d in DIPS},
                     **{f"wait_for_{int(d*100)}pct_entry": "date" for d in DIPS}})
    return out


if __name__ == "__main__":
    main()

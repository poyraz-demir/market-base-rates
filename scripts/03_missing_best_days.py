"""03 - What happens to CAGR if you miss the best (or worst) days.

Outputs (results/):
  03_missing_days.csv        buy & hold vs. without the K best / K worst / both, per series
  03_best_days_location.csv  where the 50 best days sit: inside drawdowns, next to worst days
  03_best_days_by_year.csv   calendar-year counts of the 50 best days
  03_best_days_list.csv      the 50 best and 50 worst days themselves

Method: daily returns r[i] = P[i]/P[i-1] - 1. "Missing K best days" removes the K
largest r from the product of (1 + r) and re-annualises over the SAME calendar
span. Drawdown for a day is measured from the running all-time high of closes
up to and including that day.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_daily, print_table, save, years_between  # noqa: E402

SERIES = {"GSPC": "S&P 500 price (no dividends)",
          "SP500TR": "S&P 500 total return",
          "SPY": "SPY ETF adjusted close (after fees)"}
KS = [10, 20, 30, 50, 100]
N_LOC = 50
NEAR_DAYS = 5


def scenario_rows(px: pd.Series, label: str) -> list:
    r = px.pct_change().dropna()
    yrs = years_between(px.index[0], px.index[-1])
    total = float(np.prod(1 + r))
    sorted_r = r.sort_values()

    def mult_without(idx):
        keep = r.drop(idx)
        return float(np.prod(1 + keep))

    rows = [{"series": label, "start": px.index[0], "end": px.index[-1], "years": yrs,
             "trading_days": len(r), "scenario": "buy and hold", "multiple": total,
             "cagr": total ** (1 / yrs) - 1, "growth_of_10k": 10_000 * total}]
    for k in KS:
        for which, idx in (("best", sorted_r.index[-k:]), ("worst", sorted_r.index[:k])):
            m = mult_without(idx)
            rows.append({"series": label, "start": px.index[0], "end": px.index[-1], "years": yrs,
                         "trading_days": len(r), "scenario": f"without {k} {which} days",
                         "multiple": m, "cagr": m ** (1 / yrs) - 1, "growth_of_10k": 10_000 * m})
    both = mult_without(sorted_r.index[-50:].union(sorted_r.index[:50]))
    rows.append({"series": label, "start": px.index[0], "end": px.index[-1], "years": yrs,
                 "trading_days": len(r), "scenario": "without 50 best and 50 worst days",
                 "multiple": both, "cagr": both ** (1 / yrs) - 1, "growth_of_10k": 10_000 * both})
    return rows


def location_rows(px: pd.Series, label: str):
    r = px.pct_change().dropna()
    dd = px / px.cummax() - 1
    best = r.nlargest(N_LOC)
    worst = r.nsmallest(N_LOC)
    pos = pd.Series(np.arange(len(px)), index=px.index)
    worst_pos = pos[worst.index].to_numpy()
    near = sum(np.min(np.abs(worst_pos - pos[d])) <= NEAR_DAYS for d in best.index)
    loc = {"series": label, "best_days": N_LOC,
           "in_drawdown_gt20": int((dd[best.index] < -0.20).sum()),
           "in_drawdown_gt10": int((dd[best.index] < -0.10).sum()),
           f"within_{NEAR_DAYS}_days_of_a_worst_day": int(near)}
    years = best.index.year.value_counts().sort_values(ascending=False)
    by_year = [{"series": label, "year": int(y), "best_days": int(n)} for y, n in years.items()]
    lst = pd.concat([
        pd.DataFrame({"series": label, "rank": range(1, N_LOC + 1), "kind": "best",
                      "date": best.index, "return": best.to_numpy(), "drawdown_at_close": dd[best.index].to_numpy()}),
        pd.DataFrame({"series": label, "rank": range(1, N_LOC + 1), "kind": "worst",
                      "date": worst.index, "return": worst.to_numpy(), "drawdown_at_close": dd[worst.index].to_numpy()}),
    ])
    return loc, by_year, lst


def main(verbose=True) -> dict:
    rows, locs, years, lists = [], [], [], []
    for key, label in SERIES.items():
        px = load_daily(key)
        rows += scenario_rows(px, label)
        loc, by_year, lst = location_rows(px, label)
        locs.append(loc)
        years += by_year
        lists.append(lst)
    missing = pd.DataFrame(rows)
    location = pd.DataFrame(locs)
    by_year = pd.DataFrame(years)
    lists = pd.concat(lists, ignore_index=True)

    out = {"03_missing_days": missing, "03_best_days_location": location,
           "03_best_days_by_year": by_year, "03_best_days_list": lists}
    for name, df in out.items():
        save(df, name + ".csv")
    if verbose:
        kinds = {"start": "date", "end": "date", "years": "num", "trading_days": "int",
                 "multiple": "x", "growth_of_10k": "num"}
        for label in SERIES.values():
            sub = missing[missing["series"] == label]
            print_table(f"{label}: {sub['start'].iloc[0]:%Y-%m-%d} -> {sub['end'].iloc[0]:%Y-%m-%d} "
                        f"({sub['years'].iloc[0]:.2f} years)", sub.drop(columns=["series", "start", "end", "years", "trading_days"]),
                        kinds)
        print_table("Where the 50 best days are", location,
                    {c: "int" for c in location.columns if c != "series"})
        print_table("Best days by year", by_year, {"year": "year", "best_days": "int"})
    return out


if __name__ == "__main__":
    main()

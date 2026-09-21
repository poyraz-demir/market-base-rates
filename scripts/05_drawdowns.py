"""05 - Base rates of drawdowns, S&P 500 daily price index (1927-12-30 -> DATA_END).

Outputs (results/):
  05_drawdown_frequency.csv  episodes >= 5/10/20/30/50 %, "one every N years", median/worst depth,
                             median and mean durations (calendar days)
  05_episodes_ge20.csv       every episode with a >= 20 % decline, by name
  05_time_below_high.csv     share of trading days more than 10/20/30 % below the running high
  05_intra_year.csv          average and median intra-year max drawdown, share of years by depth

Method: an episode runs from an all-time closing high to the next all-time closing
high; it counts for a threshold if the decline within it reached that threshold.
Episodes therefore never nest. An episode still open at DATA_END is listed with
no recovery date and excluded from duration statistics. Intra-year drawdown =
largest peak-to-trough decline within the calendar year using that year's
closes only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_daily, print_table, save, years_between  # noqa: E402

THRESHOLDS = [0.05, 0.10, 0.20, 0.30, 0.50]


def episodes(px: pd.Series) -> pd.DataFrame:
    """One row per peak-to-new-peak episode with a decline > 0."""
    high = px.cummax()
    is_high = px >= high
    rows = []
    peak_i = 0
    idx = px.index
    vals = px.to_numpy()
    n = len(px)
    i = 1
    while i < n:
        if is_high.iloc[i]:
            peak_i = i
            i += 1
            continue
        # a drawdown starts after peak_i; find the recovery
        j = i
        while j < n and not is_high.iloc[j]:
            j += 1
        seg = vals[peak_i:j]
        trough_rel = int(np.argmin(seg))
        trough_i = peak_i + trough_rel
        depth = vals[trough_i] / vals[peak_i] - 1
        rec = idx[j] if j < n else pd.NaT
        rows.append({"peak": idx[peak_i], "trough": idx[trough_i], "depth": depth,
                     "recovery": rec,
                     "peak_to_trough_days": (idx[trough_i] - idx[peak_i]).days,
                     "trough_to_recovery_days": (rec - idx[trough_i]).days if j < n else np.nan,
                     "full_cycle_days": (rec - idx[peak_i]).days if j < n else np.nan,
                     "recovered": j < n})
        i = j
    return pd.DataFrame(rows)


def intra_year(px: pd.Series) -> pd.DataFrame:
    rows = []
    for y, s in px.groupby(px.index.year):
        dd = (s / s.cummax() - 1).min()
        rows.append({"year": int(y), "intra_year_max_drawdown": dd,
                     "calendar_return": s.iloc[-1] / s.iloc[0] - 1})
    return pd.DataFrame(rows)


def main(verbose=True) -> dict:
    px = load_daily("GSPC")
    yrs = years_between(px.index[0], px.index[-1])
    ep = episodes(px)

    rows = []
    for t in THRESHOLDS:
        sub = ep[ep["depth"] <= -t]
        done = sub[sub["recovered"]]
        rows.append({"threshold": t, "episodes": len(sub), "years_per_episode": yrs / len(sub),
                     "median_depth": sub["depth"].median(), "worst_depth": sub["depth"].min(),
                     "median_peak_to_trough_days": done["peak_to_trough_days"].median(),
                     "median_trough_to_recovery_days": done["trough_to_recovery_days"].median(),
                     "median_full_cycle_days": done["full_cycle_days"].median(),
                     "mean_full_cycle_years": done["full_cycle_days"].mean() / 365.25,
                     "max_full_cycle_years": done["full_cycle_days"].max() / 365.25,
                     "open_episodes": int((~sub["recovered"]).sum())})
    freq = pd.DataFrame(rows)

    ge20 = ep[ep["depth"] <= -0.20].copy()
    ge20["full_cycle_years"] = ge20["full_cycle_days"] / 365.25
    ge20 = ge20[["peak", "trough", "depth", "peak_to_trough_days", "recovery", "full_cycle_years"]]

    dd = px / px.cummax() - 1
    rows = []
    for label, start in (("full history", px.index[0]),
                         ("last 50 years", px.index[-1] - pd.DateOffset(years=50)),
                         ("last 30 years", px.index[-1] - pd.DateOffset(years=30)),
                         ("last 20 years", px.index[-1] - pd.DateOffset(years=20))):
        w = dd[dd.index > start] if label != "full history" else dd
        rows.append({"period": label, "days": len(w),
                     **{f"below_high_by_{int(t*100)}pct_or_more": (w <= -t).mean() for t in (0.10, 0.20, 0.30)}})
    below = pd.DataFrame(rows)

    iy = intra_year(px)
    # complete calendar years only (1927 has a single trading day in the file)
    iy_full = iy[(iy["year"] > px.index[0].year) & (iy["year"] < px.index[-1].year)]
    rows = []
    for label, sub in ((f"{iy_full['year'].min()}-{iy_full['year'].max()}", iy_full),
                       (f"1980-{iy_full['year'].max()}", iy_full[iy_full["year"] >= 1980])):
        rows.append({"period": label, "years": len(sub),
                     "mean_intra_year_drawdown": sub["intra_year_max_drawdown"].mean(),
                     "median_intra_year_drawdown": sub["intra_year_max_drawdown"].median(),
                     "positive_calendar_years": int((sub["calendar_return"] > 0).sum()),
                     **{f"share_years_dd_ge_{int(t*100)}pct": (sub["intra_year_max_drawdown"] <= -t).mean()
                        for t in (0.05, 0.10, 0.15, 0.20)}})
    intra = pd.DataFrame(rows)

    out = {"05_drawdown_frequency": freq, "05_episodes_ge20": ge20, "05_time_below_high": below,
           "05_intra_year": intra, "05_intra_year_by_year": iy}
    for name, df in out.items():
        save(df, name + ".csv")
    if verbose:
        print(f"S&P 500 price {px.index[0]:%Y-%m-%d} -> {px.index[-1]:%Y-%m-%d} ({yrs:.2f} years, {len(px)} days)")
        print_table("Drawdown frequency", freq,
                    {"threshold": "pct", "episodes": "int", "years_per_episode": "num",
                     "median_peak_to_trough_days": "int", "median_trough_to_recovery_days": "int",
                     "median_full_cycle_days": "int", "mean_full_cycle_years": "num",
                     "max_full_cycle_years": "num", "open_episodes": "int"}, digits=1)
        print_table("Episodes >= 20 %", ge20, {"peak": "date", "trough": "date", "recovery": "date",
                                             "peak_to_trough_days": "int", "full_cycle_years": "num"}, digits=1)
        print_table("Share of days below the running high", below, {"days": "int"}, digits=1)
        print_table("Intra-year drawdowns (complete years)", intra, {"years": "int", "positive_calendar_years": "int"}, digits=1)
    return out


if __name__ == "__main__":
    main()

"""01 - Long-run S&P 500 returns from Damodaran's annual table (1928-2025).

Outputs (results/):
  01_cagr_windows.csv        nominal / real CAGR and inflation for 10/20/30/50/98-year windows
  01_asset_classes.csv       nominal CAGR of every asset class in the file, same windows
  01_annual_distribution.csv summary of calendar-year returns (share negative, worst, best)
  01_rolling_10y.csv         every rolling 10-year nominal CAGR window
  01_rolling_10y_summary.csv median / min / max / share negative of those windows

Method: CAGR over a window = (product of (1 + annual return)) ** (1/years) - 1.
"Real" uses Damodaran's own real-return columns (deflated with CPI-U).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_damodaran, print_table, save  # noqa: E402

WINDOWS = [10, 20, 30, 50, None]  # None = full sample
ASSETS = {"sp500": "S&P 500 (total return)", "gold": "Gold", "baa": "Baa corporate bonds",
          "real_estate": "US home prices (price index)", "tbond": "10-year T-bond",
          "tbill": "3-month T-bill"}


def window_cagr(returns: pd.Series) -> float:
    return float(np.prod(1 + returns.to_numpy()) ** (1 / len(returns)) - 1)


def main(verbose=True) -> dict:
    d = load_damodaran()
    last = int(d["year"].max())
    first = int(d["year"].min())

    rows = []
    for w in WINDOWS:
        start = first if w is None else last - w + 1
        sub = d[d["year"] >= start]
        rows.append({
            "window": f"{start}-{last}", "years": len(sub),
            "nominal_cagr": window_cagr(sub["sp500"]),
            "real_cagr": window_cagr(sub["sp500_real"]),
            "inflation_cagr": window_cagr(sub["inflation"]),
            "growth_of_100": 100 * float(np.prod(1 + sub["sp500"])),
        })
    cagr = pd.DataFrame(rows)

    rows = []
    for key, label in ASSETS.items():
        r = {"asset": label}
        for w in WINDOWS:
            start = first if w is None else last - w + 1
            sub = d[d["year"] >= start]
            r[f"{len(sub)}y"] = window_cagr(sub[key])
        r["real_30y"] = window_cagr(d[d["year"] >= last - 29][f"{key}_real"])
        rows.append(r)
    assets = pd.DataFrame(rows)

    r = d["sp500"]
    dist = pd.DataFrame([{
        "years": len(r), "negative_years": int((r < 0).sum()),
        "share_negative": (r < 0).mean(),
        "worst_year": int(d.loc[r.idxmin(), "year"]), "worst_return": r.min(),
        "best_year": int(d.loc[r.idxmax(), "year"]), "best_return": r.max(),
        "arithmetic_mean": r.mean(), "geometric_mean": window_cagr(r),
    }])

    roll = []
    for i in range(len(d) - 9):
        sub = d.iloc[i:i + 10]
        roll.append({"start": int(sub["year"].iloc[0]), "end": int(sub["year"].iloc[-1]),
                     "cagr_10y_nominal": window_cagr(sub["sp500"]),
                     "cagr_10y_real": window_cagr(sub["sp500_real"])})
    roll = pd.DataFrame(roll)
    rs = pd.DataFrame([{
        "windows": len(roll),
        "median": roll["cagr_10y_nominal"].median(),
        "min": roll["cagr_10y_nominal"].min(),
        "min_window": f"{roll.loc[roll['cagr_10y_nominal'].idxmin(), 'start']}-{roll.loc[roll['cagr_10y_nominal'].idxmin(), 'end']}",
        "max": roll["cagr_10y_nominal"].max(),
        "max_window": f"{roll.loc[roll['cagr_10y_nominal'].idxmax(), 'start']}-{roll.loc[roll['cagr_10y_nominal'].idxmax(), 'end']}",
        "share_negative": (roll["cagr_10y_nominal"] < 0).mean(),
        "share_negative_real": (roll["cagr_10y_real"] < 0).mean(),
    }])

    out = {"01_cagr_windows": cagr, "01_asset_classes": assets,
           "01_annual_distribution": dist, "01_rolling_10y": roll,
           "01_rolling_10y_summary": rs}
    for name, df in out.items():
        save(df, name + ".csv")
    if verbose:
        print(f"Damodaran annual data {first}-{last}")
        print_table("S&P 500 CAGR by window", cagr, {"years": "int", "growth_of_100": "num"})
        print_table("Asset classes, nominal CAGR", assets)
        print_table("Calendar-year distribution", dist,
                    {"years": "int", "negative_years": "int", "worst_year": "year", "best_year": "year"})
        print_table("Rolling 10-year CAGR summary", rs, {"windows": "int"})
    return out


if __name__ == "__main__":
    main()

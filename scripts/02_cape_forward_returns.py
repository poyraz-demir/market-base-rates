"""02 - Forward real returns after high CAPE (Shiller monthly data, 1881-).

Outputs (results/):
  02_cape_now.csv              where CAPE stands at the last month of the file
  02_forward_by_bucket.csv     1/3/5/10-year forward real & nominal returns for all months,
                               CAPE 25-30, >30, >35, >40 (median, mean, worst, best, p25, p75, share<0)
  02_independent_episodes.csv  contiguous runs of months per bucket (how many independent episodes)
  02_regime_split.csv          CAPE>30 entries: 1929 & 1997-2002 vs 2017-2021
  02_cape_gt40_episodes.csv    every stretch of months with CAPE > 40

Method: forward annualised return over H years from month t
  (TR[t+12H] / TR[t]) ** (1/H) - 1
using Shiller's "Real Total Return Price" (real, dividends reinvested) and
its nominal counterpart (real_tr * CPI). Windows OVERLAP: consecutive months
share almost all of their forward path, so n is not a count of independent
observations - see the episodes table.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_shiller, print_table, save, summarize  # noqa: E402

HORIZONS = [1, 3, 5, 10]
BUCKETS = {
    "all": lambda c: c.notna(),
    "cape_25_30": lambda c: (c > 25) & (c <= 30),
    "cape_gt30": lambda c: c > 30,
    "cape_gt35": lambda c: c > 35,
    "cape_gt40": lambda c: c > 40,
}
REGIME_CUT = pd.Timestamp("2017-07-01")  # first CAPE>30 month of the 2017-2021 stretch


def add_forward(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for h in HORIZONS:
        for col, name in (("real_tr", "real"), ("nom_tr", "nom")):
            df[f"{name}_{h}y"] = (df[col].shift(-12 * h) / df[col]) ** (1 / h) - 1
    return df


def bucket_stats(df, mask, label):
    rows = []
    for h in HORIZONS:
        for kind in ("real", "nom"):
            s = summarize(df.loc[mask, f"{kind}_{h}y"])
            rows.append({"bucket": label, "months_in_bucket": int(mask.sum()),
                         "horizon_years": h, "kind": kind, **s})
    return rows


def runs(dates: pd.Series) -> list:
    """Split a sorted list of month-start dates into contiguous monthly runs."""
    out, start, prev = [], None, None
    for d in dates:
        if prev is None or (d.year - prev.year) * 12 + d.month - prev.month != 1:
            if start is not None:
                out.append((start, prev))
            start = d
        prev = d
    if start is not None:
        out.append((start, prev))
    return out


def main(verbose=True) -> dict:
    sh = add_forward(load_shiller())
    c = sh["cape"]
    valid = sh[c.notna()]
    last = sh.iloc[-1]
    now = pd.DataFrame([{
        "month": last["date"].strftime("%Y-%m"), "cape": last["cape"],
        "cape_median_all": valid["cape"].median(), "cape_mean_all": valid["cape"].mean(),
        "percentile": (valid["cape"] < last["cape"]).mean(),
        "months_above_current": int((valid["cape"] > last["cape"]).sum()),
        "months_with_cape": len(valid),
        "peak_cape": valid["cape"].max(),
        "peak_month": valid.loc[valid["cape"].idxmax(), "date"].strftime("%Y-%m"),
    }])

    rows = []
    for label, f in BUCKETS.items():
        rows += bucket_stats(sh, f(c), label)
    fwd = pd.DataFrame(rows)

    # Independent episodes: contiguous runs among months that have a full 10y outcome.
    ep = []
    for label in ("cape_gt30", "cape_gt35", "cape_gt40"):
        m = BUCKETS[label](c) & sh["real_10y"].notna()
        for a, b in runs(list(sh.loc[m, "date"])):
            sub = sh[(sh["date"] >= a) & (sh["date"] <= b)]
            ep.append({"bucket": label, "run_start": a.strftime("%Y-%m"), "run_end": b.strftime("%Y-%m"),
                       "months": len(sub), "median_real_10y": sub["real_10y"].median(),
                       "median_nom_10y": sub["nom_10y"].median()})
    episodes = pd.DataFrame(ep)

    # Regime split for CAPE>30: old episodes vs the 2017-2021 stretch.
    m30 = c > 30
    split = []
    for regime, mask in (("1929 & 1997-2002", m30 & (sh["date"] < REGIME_CUT)),
                         ("2017-2021", m30 & (sh["date"] >= REGIME_CUT))):
        for h in (1, 3, 5):
            for kind in ("real", "nom"):
                s = summarize(sh.loc[mask, f"{kind}_{h}y"])
                split.append({"regime": regime, "horizon_years": h, "kind": kind, **s})
    split = pd.DataFrame(split)
    no_outcome = int((m30 & sh["real_10y"].isna()).sum())

    g40 = [{"run_start": a.strftime("%Y-%m"), "run_end": b.strftime("%Y-%m"),
            "months": (b.year - a.year) * 12 + b.month - a.month + 1}
           for a, b in runs(list(sh.loc[c > 40, "date"]))]
    g40 = pd.DataFrame(g40)

    out = {"02_cape_now": now, "02_forward_by_bucket": fwd, "02_independent_episodes": episodes,
           "02_regime_split": split, "02_cape_gt40_episodes": g40}
    for name, df in out.items():
        save(df, name + ".csv")
    if verbose:
        print(f"Shiller monthly data {sh['date'].iloc[0]:%Y-%m} -> {sh['date'].iloc[-1]:%Y-%m}; "
              f"CAPE available for {len(valid)} months from {valid['date'].iloc[0]:%Y-%m}")
        print_table("CAPE now", now, {"cape": "num", "cape_median_all": "num", "cape_mean_all": "num",
                                     "months_above_current": "int", "months_with_cape": "int", "peak_cape": "num"})
        print_table("Forward returns by CAPE bucket (real)", fwd[fwd["kind"] == "real"],
                    {"months_in_bucket": "int", "horizon_years": "int", "n": "int"})
        print_table("Forward returns by CAPE bucket (nominal)", fwd[fwd["kind"] == "nom"],
                    {"months_in_bucket": "int", "horizon_years": "int", "n": "int"})
        print_table("Independent episodes (months with a full 10y outcome)", episodes, {"months": "int"})
        print(f"\nCAPE>30 months without a 10-year outcome yet: {no_outcome}")
        print_table("CAPE>30: regime split (real)", split[split["kind"] == "real"], {"horizon_years": "int", "n": "int"})
        print_table("CAPE>30: regime split (nominal)", split[split["kind"] == "nom"], {"horizon_years": "int", "n": "int"})
        print_table("CAPE>40 stretches", g40, {"months": "int"})
    return out


if __name__ == "__main__":
    main()

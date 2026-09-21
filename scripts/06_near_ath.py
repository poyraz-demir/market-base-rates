"""06 - How often the market sits near its all-time high, and what follows a purchase there.

Outputs (results/):
  06_share_near_high.csv     share of days at a new high / within 1,2,5,10 % / >20 % below, per period
  06_forward_after_entry.csv forward 1/3/5-year returns after buying on an ATH day vs a random day
                             (total return 1988-, and price-only 1928-)

Method: "within X % of the high" = close >= (1 - X) * running max of PRICE-index
closes up to that day (running max over the FULL history, even for the
sub-periods; the total-return series also uses the price index's high as the
entry condition). Forward return over N years = 252*N trading days ahead,
annualised. Windows overlap.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_daily, print_table, save, summarize  # noqa: E402

BANDS = [0.01, 0.02, 0.05, 0.10]
HORIZONS = {1: 252, 3: 756, 5: 1260}


def share_rows(px: pd.Series) -> pd.DataFrame:
    dd = px / px.cummax() - 1
    rows = []
    for label, start in (("full history", None),
                         ("last 50 years", px.index[-1] - pd.DateOffset(years=50)),
                         ("last 30 years", px.index[-1] - pd.DateOffset(years=30)),
                         ("last 20 years", px.index[-1] - pd.DateOffset(years=20))):
        w = dd if start is None else dd[dd.index > start]
        rows.append({"period": label, "days": len(w), "new_high_days": int((w >= 0).sum()),
                     "share_new_high": (w >= 0).mean(),
                     **{f"within_{int(b*100)}pct": (w >= -b).mean() for b in BANDS},
                     "below_high_gt20pct": (w < -0.20).mean()})
    return pd.DataFrame(rows)


def forward_rows(px: pd.Series, price: pd.Series, label: str) -> list:
    """Entry conditions use the PRICE index's running high (that is what "the
    market's all-time high" means in practice); forward returns use `px`."""
    dd = (price / price.cummax() - 1).reindex(px.index)
    rows = []
    for h, days in HORIZONS.items():
        fwd = (px.shift(-days) / px) ** (1 / h) - 1
        conds = {"random day": dd.notna(), "new all-time high day": dd >= 0,
                 "within 1% of high": dd >= -0.01, "within 5% of high": dd >= -0.05,
                 "10%+ below high": dd <= -0.10, "20%+ below high": dd <= -0.20}
        for name, m in conds.items():
            s = summarize(fwd[m], extra_pct=(5, 95))
            rows.append({"series": label, "horizon_years": h, "entry": name, **s})
    return rows


def main(verbose=True) -> dict:
    gspc = load_daily("GSPC")
    tr = load_daily("SP500TR")
    share = share_rows(gspc)
    fwd = pd.DataFrame(forward_rows(tr, gspc, "S&P 500 total return (1988-)")
                       + forward_rows(gspc, gspc, "S&P 500 price (1928-)"))
    out = {"06_share_near_high": share, "06_forward_after_entry": fwd}
    for name, df in out.items():
        save(df, name + ".csv")
    if verbose:
        print(f"S&P 500 price {gspc.index[0]:%Y-%m-%d} -> {gspc.index[-1]:%Y-%m-%d}; "
              f"total return {tr.index[0]:%Y-%m-%d} -> {tr.index[-1]:%Y-%m-%d}")
        print_table("Share of days near the all-time high (price index)", share,
                    {"days": "int", "new_high_days": "int"}, digits=1)
        for lab in fwd["series"].unique():
            for h in HORIZONS:
                sub = fwd[(fwd["series"] == lab) & (fwd["horizon_years"] == h)]
                print_table(f"{lab}: forward {h}-year annualised return by entry point",
                            sub.drop(columns=["series", "horizon_years"]), {"n": "int"})
    return out


if __name__ == "__main__":
    main()

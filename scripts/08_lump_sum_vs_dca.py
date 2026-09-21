"""08 - Lump sum vs. spreading the purchase over 3 / 6 / 12 months.

Outputs (results/):
  08_lump_sum_vs_dca.csv   hit ratio and wealth percentiles, LS vs DCA, per DCA length and cash assumption
  08_windows.csv           every monthly window (start, LS wealth, DCA wealth per variant)

Method (mirrors Vanguard 2023, "Cost averaging: Invest now or temporarily hold
your cash?"): entry on the first trading day of every month from 1988-01;
horizon = 12 months; LS invests everything at entry; DCA over N months invests
1/N at entry and 1/N on the first trading day of each of the next N-1 months;
the uninvested remainder earns either the 3-month T-bill (cash index) or 0 %.
Wealth is compared at entry + 12 months. Windows overlap. Stocks = S&P 500
total return index. No taxes or fees.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import cash_index, load_daily, load_fred, print_table, save  # noqa: E402

DCA_MONTHS = [3, 6, 12]
HORIZON_MONTHS = 12


def main(verbose=True) -> dict:
    tr = load_daily("SP500TR")
    cash = cash_index(load_fred("DGS3MO")).reindex(tr.index, method="ffill")
    first_days = tr.groupby([tr.index.year, tr.index.month]).apply(lambda s: s.index[0]).tolist()

    rows = []
    for i, t0 in enumerate(first_days):
        if i + HORIZON_MONTHS >= len(first_days):
            break
        end = first_days[i + HORIZON_MONTHS]
        row = {"start": t0, "end": end, "lump_sum": tr[end] / tr[t0],
               "all_cash_tbill": cash[end] / cash[t0]}
        for n in DCA_MONTHS:
            dates = first_days[i:i + n]
            row[f"dca_{n}m_tbill"] = sum((cash[d] / cash[t0]) * (tr[end] / tr[d]) for d in dates) / n
            row[f"dca_{n}m_zero"] = sum(tr[end] / tr[d] for d in dates) / n
        rows.append(row)
    win = pd.DataFrame(rows)

    summary = []
    for n in DCA_MONTHS:
        for variant, label in (("tbill", "cash earns 3m T-bill"), ("zero", "cash earns 0%")):
            dca = win[f"dca_{n}m_{variant}"]
            ls = win["lump_sum"]
            diff = ls - dca
            summary.append({"dca_months": n, "uninvested_cash": label, "windows": len(win),
                            "ls_beats_dca": (ls > dca).mean(),
                            "median_ls_minus_dca": diff.median(), "mean_ls_minus_dca": diff.mean(),
                            "ls_p5": ls.quantile(0.05), "dca_p5": dca.quantile(0.05),
                            "ls_median": ls.median(), "dca_median": dca.median(),
                            "ls_p95": ls.quantile(0.95), "dca_p95": dca.quantile(0.95),
                            "dca_beats_all_cash": (dca > win["all_cash_tbill"]).mean()})
    summary = pd.DataFrame(summary)
    summary.attrs["ls_beats_all_cash"] = float((win["lump_sum"] > win["all_cash_tbill"]).mean())

    out = {"08_lump_sum_vs_dca": summary, "08_windows": win}
    for name, df in out.items():
        save(df, name + ".csv")
    if verbose:
        print(f"Monthly entries {win['start'].iloc[0]:%Y-%m} -> {win['start'].iloc[-1]:%Y-%m}, "
              f"{len(win)} overlapping 12-month windows; LS beats all-cash in "
              f"{summary.attrs['ls_beats_all_cash']*100:.1f}% of windows")
        print_table("Lump sum vs DCA, wealth after 12 months (1.00 = starting amount)", summary,
                    {"dca_months": "int", "windows": "int",
                     **{c: ("x", 3) for c in ("ls_p5", "dca_p5", "ls_median", "dca_median", "ls_p95", "dca_p95")}}, digits=1)
    return out


if __name__ == "__main__":
    main()

"""Run every script, write results/*.csv, results/SUMMARY.md and refresh the
generated block of README.md.

  python run_all.py
"""
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from common import DATA_END, RESULTS, MissingDataError, md_table  # noqa: E402

SCRIPTS = ["01_long_run_returns", "02_cape_forward_returns", "03_missing_best_days",
           "04_waiting_in_cash", "05_drawdowns", "06_near_ath", "07_cash_real_yield",
           "08_lump_sum_vs_dca"]


def run(name: str) -> dict:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main(verbose=False)


# ----------------------------------------------------------------------------- table specs
# Each entry: results key, title, columns to keep (optional), renames, kinds, digits,
# row filter (optional), note, readme (include in README or only in SUMMARY).
def T(key, title, cols=None, rename=None, kinds=None, digits=2, where=None, note="", readme=True):
    return dict(key=key, title=title, cols=cols, rename=rename or {}, kinds=kinds or {},
                digits=digits, where=where, note=note, readme=readme)


PCT_COLS = {"median", "mean", "worst", "best", "share_negative", "p5", "p25", "p75", "p95"}
SPECS = [
    # 01
    T("01_cagr_windows", "S&P 500 CAGR by window (Damodaran annual data)",
      ["window", "years", "nominal_cagr", "real_cagr", "inflation_cagr"],
      kinds={"years": "int"}),
    T("01_rolling_10y_summary", "Rolling 10-year nominal CAGR, all windows",
      ["windows", "median", "min", "min_window", "max", "max_window", "share_negative", "share_negative_real"],
      kinds={"windows": "int"}),
    T("01_annual_distribution", "Calendar-year returns",
      ["years", "negative_years", "share_negative", "worst_year", "worst_return", "best_year", "best_return"],
      kinds={"years": "int", "negative_years": "int", "worst_year": "year", "best_year": "year"}),
    T("01_asset_classes", "Other asset classes, nominal CAGR to end-2025 (same file)", readme=False),
    # 02
    T("02_cape_now", "Where CAPE stands",
      ["month", "cape", "cape_median_all", "cape_mean_all", "percentile", "months_above_current", "months_with_cape", "peak_cape", "peak_month"],
      kinds={"cape": "num", "cape_median_all": "num", "cape_mean_all": "num", "months_above_current": "int",
             "months_with_cape": "int", "peak_cape": "num"}),
    T("02_forward_by_bucket", "Forward REAL annualised return by CAPE bucket (overlapping monthly windows)",
      ["bucket", "months_in_bucket", "horizon_years", "n", "median", "mean", "worst", "best", "p25", "p75", "share_negative"],
      kinds={"months_in_bucket": "int", "horizon_years": "int", "n": "int"},
      where=lambda d: d["kind"] == "real"),
    T("02_forward_by_bucket", "Forward NOMINAL annualised return by CAPE bucket",
      ["bucket", "months_in_bucket", "horizon_years", "n", "median", "mean", "worst", "best", "p25", "p75", "share_negative"],
      kinds={"months_in_bucket": "int", "horizon_years": "int", "n": "int"},
      where=lambda d: d["kind"] == "nom", readme=False),
    T("02_independent_episodes", "How many INDEPENDENT episodes are behind those n (months with a full 10-year outcome)",
      kinds={"months": "int"}),
    T("02_regime_split", "CAPE > 30 entries split by regime, REAL annualised",
      ["regime", "horizon_years", "n", "median", "mean", "worst", "best", "share_negative"],
      kinds={"horizon_years": "int", "n": "int"}, where=lambda d: d["kind"] == "real"),
    T("02_regime_split", "CAPE > 30 entries split by regime, NOMINAL annualised",
      ["regime", "horizon_years", "n", "median", "mean", "worst", "best", "share_negative"],
      kinds={"horizon_years": "int", "n": "int"}, where=lambda d: d["kind"] == "nom", readme=False),
    T("02_cape_gt40_episodes", "Every stretch of months with CAPE > 40", kinds={"months": "int"}),
    # 03
    T("03_missing_days", "Missing the best / worst days (CAGR over the same calendar span)",
      ["series", "scenario", "multiple", "cagr"], kinds={"multiple": "x"},
      where=lambda d: d["scenario"].isin(["buy and hold", "without 10 best days", "without 20 best days",
                                          "without 30 best days", "without 50 best days", "without 100 best days",
                                          "without 50 worst days", "without 50 best and 50 worst days"])),
    T("03_missing_days", "Missing the worst days, all scenarios",
      ["series", "scenario", "multiple", "cagr"], kinds={"multiple": "x"},
      where=lambda d: d["scenario"].str.contains("worst"), readme=False),
    T("03_best_days_location", "Where the 50 best days sit",
      kinds={"best_days": "int", "in_drawdown_gt20": "int", "in_drawdown_gt10": "int", "within_5_days_of_a_worst_day": "int"}),
    T("03_best_days_by_year", "The 50 best days by calendar year", kinds={"year": "year", "best_days": "int"}, readme=False),
    # 04
    T("04_waiting_nominal", "Moved to 3-month T-bills on that date vs invested the same day (S&P 500 TR), nominal",
      ["start", "reason", "years", "stocks_multiple", "stocks_cagr", "cash_multiple", "cash_cagr", "cash_shortfall"],
      kinds={"start": "date", "years": "num", "stocks_multiple": "x", "cash_multiple": "x"}),
    T("04_waiting_real", "Same, CPI-deflated",
      kinds={"start": "date", "inflation_multiple": "x", "stocks_real_multiple": "x", "cash_real_multiple": "x"}),
    T("04_was_cash_ever_ahead", "Was cash ever ahead?",
      kinds={"start": "date", "min_stocks_to_cash": "num", "min_date": "date", "last_day_cash_ahead": "date"}),
    T("04_wait_for_dip", "Stay in T-bills until the index is X % below its running high since the start date, then go all in (final multiple; blank entry = never triggered)",
      ["start", "invest_immediately", "wait_for_10pct", "wait_for_10pct_vs_immediate", "wait_for_20pct",
       "wait_for_20pct_vs_immediate", "wait_for_30pct", "wait_for_30pct_vs_immediate"],
      kinds={"start": "date", "invest_immediately": "x", "wait_for_10pct": "x", "wait_for_20pct": "x", "wait_for_30pct": "x"}),
    T("04_wait_for_dip", "Entry dates for the wait-for-a-dip strategy",
      ["start", "wait_for_10pct_entry", "wait_for_20pct_entry", "wait_for_30pct_entry"],
      kinds={"start": "date", "wait_for_10pct_entry": "date", "wait_for_20pct_entry": "date", "wait_for_30pct_entry": "date"},
      readme=False),
    # 05
    T("05_drawdown_frequency", "Drawdown base rates, S&P 500 price index (calendar days)",
      ["threshold", "episodes", "years_per_episode", "median_depth", "worst_depth", "median_peak_to_trough_days",
       "median_trough_to_recovery_days", "median_full_cycle_days", "mean_full_cycle_years", "max_full_cycle_years"],
      kinds={"episodes": "int", "years_per_episode": "num", "median_peak_to_trough_days": "int",
             "median_trough_to_recovery_days": "int", "median_full_cycle_days": "int",
             "mean_full_cycle_years": "num", "max_full_cycle_years": "num"}, digits=1),
    T("05_episodes_ge20", "Every decline of 20 % or more",
      kinds={"peak": "date", "trough": "date", "recovery": "date", "peak_to_trough_days": "int", "full_cycle_years": "num"}, digits=1),
    T("05_time_below_high", "Share of trading days spent below the running high", kinds={"days": "int"}, digits=1),
    T("05_intra_year", "Intra-year drawdowns (complete calendar years)",
      kinds={"years": "int", "positive_calendar_years": "int"}, digits=1),
    # 06
    T("06_share_near_high", "How often the price index sits near its all-time high",
      kinds={"days": "int", "new_high_days": "int"}, digits=1),
    T("06_forward_after_entry", "Forward 1-year return after buying at an all-time high vs any day (S&P 500 total return, 1988-)",
      ["entry", "n", "mean", "median", "share_negative", "p5", "p95", "worst"], kinds={"n": "int"},
      where=lambda d: (d["series"].str.startswith("S&P 500 total")) & (d["horizon_years"] == 1)),
    T("06_forward_after_entry", "Same, price index 1928- (no dividends)",
      ["entry", "n", "mean", "median", "share_negative", "p5", "p95", "worst"], kinds={"n": "int"},
      where=lambda d: (d["series"].str.startswith("S&P 500 price")) & (d["horizon_years"] == 1)),
    T("06_forward_after_entry", "Forward 3- and 5-year annualised returns by entry point (both series)",
      ["series", "horizon_years", "entry", "n", "mean", "median", "share_negative", "p5", "worst"],
      kinds={"horizon_years": "int", "n": "int"}, where=lambda d: d["horizon_years"] > 1, readme=False),
    # 07
    T("07_current", "Real yield on cash now vs 2021", kinds={"as_of": "str", "basis": "str"}),
    T("07_real_cash_by_period", "Real yield on 3-month T-bills by period (monthly, 1982-)", kinds={"months": "int"}),
    T("07_negative_months_by_decade", "Share of months with a negative real cash yield", kinds={"months": "int"}),
    T("07_worst_months", "Worst months for real cash yield", kinds={"month": "str"}, readme=False),
    T("07_calendar_years", "Calendar-year cash return vs CPI (Dec/Dec), last 12 years",
      kinds={"year": "year"}, where=lambda d: d["year"] >= d["year"].max() - 11, readme=False),
    T("07_rates_snapshot", "Other rates in data/raw/fred, last value", kinds={"date": "date", "value": "num"}, readme=False),
    # 08
    T("08_lump_sum_vs_dca", "Lump sum vs spreading the purchase (S&P 500 TR, monthly entries 1988-, wealth after 12 months)",
      ["dca_months", "uninvested_cash", "windows", "ls_beats_dca", "median_ls_minus_dca", "ls_p5", "dca_p5",
       "ls_median", "dca_median", "dca_beats_all_cash"],
      kinds={"dca_months": "int", "windows": "int", "ls_p5": ("x", 3), "dca_p5": ("x", 3),
             "ls_median": ("x", 3), "dca_median": ("x", 3)}, digits=1),
]


def render(spec: dict, results: dict) -> str:
    df = results[spec["key"]]
    if spec["where"] is not None:
        df = df[spec["where"](df)]
    if spec["cols"]:
        df = df[spec["cols"]]
    df = df.rename(columns=spec["rename"])
    kinds = {spec["rename"].get(k, k): v for k, v in spec["kinds"].items()}
    body = md_table(df, kinds, spec["digits"])
    note = f"\n\n{spec['note']}" if spec["note"] else ""
    return f"#### {spec['title']}\n\n{body}{note}\n"


SECTION_OF = {"01": "1. Long-run returns", "02": "2. CAPE and forward returns", "03": "3. Missing the best days",
              "04": "4. Waiting in cash", "05": "5. Drawdowns", "06": "6. Buying at all-time highs",
              "07": "7. Real yield on cash", "08": "8. Lump sum vs dollar-cost averaging"}


def build(results: dict, readme_only: bool) -> str:
    out, current = [], None
    for spec in SPECS:
        if readme_only and not spec["readme"]:
            continue
        if spec["key"] not in results:
            continue
        sec = spec["key"][:2]
        if sec != current:
            out.append(f"\n### {SECTION_OF[sec]}\n")
            current = sec
        out.append(render(spec, results))
    return "\n".join(out)


def update_readme(block: str):
    path = ROOT / "README.md"
    text = path.read_text()
    start, end = "<!-- generated:start -->", "<!-- generated:end -->"
    a, b = text.index(start) + len(start), text.index(end)
    text = text[:a] + "\n" + block + "\n" + text[b:]
    path.write_text(text)


def main():
    results, skipped = {}, []
    for name in SCRIPTS:
        try:
            results.update(run(name))
            print(f"ok    {name}")
        except MissingDataError as e:
            skipped.append(name)
            print(f"SKIP  {name}: {e}")
    RESULTS.mkdir(exist_ok=True)
    stamp = (f"Daily series end {DATA_END:%Y-%m-%d}; Shiller monthly data through 2026-09 (September price = "
             f"1 September close, recent CPI months estimated by Shiller); Damodaran annual data through 2025; "
             f"FRED CPI through 2026-08. Generated {date.today():%Y-%m-%d} by `python run_all.py`.")
    summary = f"# Summary of results\n\n{stamp}\n\n" + build(results, readme_only=False)
    if skipped:
        summary += "\n\nSkipped (daily data not downloaded, run `python fetch.py`): " + ", ".join(skipped) + "\n"
    (RESULTS / "SUMMARY.md").write_text(summary)
    update_readme(f"_{stamp}_\n" + build(results, readme_only=True))
    print(f"wrote {RESULTS / 'SUMMARY.md'} and refreshed README.md ({len(results)} tables)")


if __name__ == "__main__":
    main()

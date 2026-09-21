"""Every script runs and returns non-empty tables; a few known numbers are pinned.

Scripts that need the Yahoo Finance daily series are skipped (not failed) when
data/cache/ is empty - run `python fetch.py` first to exercise them.
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import MissingDataError  # noqa: E402

SCRIPTS = ["01_long_run_returns", "02_cape_forward_returns", "03_missing_best_days",
           "04_waiting_in_cash", "05_drawdowns", "06_near_ath", "07_cash_real_yield",
           "08_lump_sum_vs_dca"]
_cache = {}


def run(name):
    if name not in _cache:
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        try:
            _cache[name] = mod.main(verbose=False)
        except MissingDataError as e:
            pytest.skip(str(e))
    return _cache[name]


@pytest.mark.parametrize("name", SCRIPTS)
def test_script_runs_and_returns_tables(name):
    out = run(name)
    assert isinstance(out, dict) and out
    for key, df in out.items():
        assert isinstance(df, pd.DataFrame), key
        assert len(df) > 0, key
        assert (ROOT / "results" / f"{key}.csv").exists(), key


# ---- pinned numbers (from the September 2026 research notes), with tolerances
def test_cagr_30y_nominal():
    w = run("01_long_run_returns")["01_cagr_windows"].set_index("window")
    assert abs(w.loc["1996-2025", "nominal_cagr"] - 0.1026) < 0.0005
    assert abs(w.loc["1976-2025", "nominal_cagr"] - 0.1192) < 0.0005
    assert abs(w.loc["1928-2025", "nominal_cagr"] - 0.1002) < 0.0005
    assert abs(w.loc["1996-2025", "real_cagr"] - 0.0754) < 0.0005


def test_rolling_10y():
    r = run("01_long_run_returns")["01_rolling_10y_summary"].iloc[0]
    assert r["windows"] == 89
    assert abs(r["median"] - 0.1096) < 0.0005
    assert abs(r["min"] - (-0.0167)) < 0.0005


def test_cape_buckets():
    fwd = run("02_cape_forward_returns")["02_forward_by_bucket"]
    real = fwd[fwd["kind"] == "real"].set_index(["bucket", "horizon_years"])
    assert abs(real.loc[("cape_gt35", 10), "median"] - (-0.0303)) < 0.001
    assert abs(real.loc[("cape_gt30", 10), "median"] - (-0.0113)) < 0.001
    assert real.loc[("cape_gt40", 10), "n"] == 21
    assert real.loc[("cape_gt40", 10), "share_negative"] == 1.0
    assert abs(real.loc[("all", 10), "median"] - 0.0661) < 0.001
    ep = run("02_cape_forward_returns")["02_independent_episodes"]
    assert (ep["bucket"] == "cape_gt40").sum() == 1      # one episode: 1999-2000
    assert (ep["bucket"] == "cape_gt30").sum() == 4


def test_missing_best_days():
    m = run("03_missing_best_days")["03_missing_days"]
    tr = m[m["series"].str.startswith("S&P 500 total")].set_index("scenario")
    assert abs(tr.loc["buy and hold", "cagr"] - 0.1148) < 0.0005
    assert abs(tr.loc["without 50 best days", "cagr"] - 0.0417) < 0.0005
    assert abs(tr.loc["without 50 worst days", "cagr"] - 0.2010) < 0.0005
    loc = run("03_missing_best_days")["03_best_days_location"].set_index("series")
    assert loc.loc["S&P 500 price (no dividends)", "in_drawdown_gt20"] == 47


def test_waiting_in_cash_1996():
    n = run("04_waiting_in_cash")["04_waiting_nominal"].set_index("start")
    row = n.loc[pd.Timestamp("1996-12-05")]
    assert abs(row["cash_shortfall"] - 0.889) < 0.005
    assert abs(row["stocks_cagr"] - 0.1010) < 0.0005
    d = run("04_waiting_in_cash")["04_wait_for_dip"].set_index("start").loc[pd.Timestamp("1996-12-05")]
    assert abs(d["wait_for_20pct_vs_immediate"] - (-0.26)) < 0.01


def test_drawdowns():
    f = run("05_drawdowns")["05_drawdown_frequency"].set_index("threshold")
    assert f.loc[0.20, "episodes"] == 12
    assert f.loc[0.50, "episodes"] == 2
    assert abs(f.loc[0.20, "median_full_cycle_days"] - 764) <= 1
    ep = run("05_drawdowns")["05_episodes_ge20"]
    assert abs(ep["depth"].min() - (-0.862)) < 0.002


def test_near_ath():
    s = run("06_near_ath")["06_share_near_high"].set_index("period")
    assert abs(s.loc["last 50 years", "within_1pct"] - 0.214) < 0.003
    f = run("06_near_ath")["06_forward_after_entry"]
    ath = f[(f["horizon_years"] == 1) & (f["entry"] == "new all-time high day")
            & f["series"].str.startswith("S&P 500 total")].iloc[0]
    assert ath["n"] == 764
    assert abs(ath["mean"] - 0.1378) < 0.001


def test_cash_real_yield():
    p = run("07_cash_real_yield")["07_real_cash_by_period"].set_index("period")
    assert abs(p.loc["2010-2019", "mean_real"] - (-0.0117)) < 0.001
    assert abs(p.loc["2021", "mean_real"] - (-0.0440)) < 0.001
    d = run("07_cash_real_yield")["07_negative_months_by_decade"].set_index("period")
    assert abs(d.loc["1982-2008", "share_months_real_negative"] - 0.17) < 0.01


def test_lump_sum_vs_dca():
    s = run("08_lump_sum_vs_dca")["08_lump_sum_vs_dca"]
    r = s[(s["dca_months"] == 3) & s["uninvested_cash"].str.contains("T-bill")].iloc[0]
    assert 0.55 < r["ls_beats_dca"] < 0.80          # Vanguard 2023: ~65 % with T-bill interest

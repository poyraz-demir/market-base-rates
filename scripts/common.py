"""Shared loaders and small helpers used by every script.

Plain functions, plain pandas. Every daily series is cut at DATA_END so that a
re-run on freshly downloaded data reproduces the published tables exactly
(Yahoo Finance history for past dates is stable; only the tail grows).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CACHE = ROOT / "data" / "cache"
RESULTS = ROOT / "results"

# Last trading day covered by the published results. Daily series downloaded
# later are truncated here so numbers stay reproducible.
DATA_END = pd.Timestamp("2026-09-18")

# Yahoo Finance-derived daily series live in data/cache/ (not committed, see
# fetch.py and data/SOURCES.md). File format: date,close
DAILY_FILES = {
    "GSPC": "GSPC.csv",        # S&P 500 price index, 1927-12-30 -> DATA_END
    "SP500TR": "SP500TR.csv",  # S&P 500 total return index, 1988-01-04 -> DATA_END
    "SPY": "SPY.csv",          # SPY ETF adjusted close (total return net of fees), 1993-01-29 -> DATA_END
}


class MissingDataError(RuntimeError):
    pass


# --------------------------------------------------------------------------- loaders
def load_daily(name: str) -> pd.Series:
    """Daily close series from data/cache/, indexed by date, cut at DATA_END."""
    path = CACHE / DAILY_FILES[name]
    if not path.exists():
        raise MissingDataError(
            f"{path} not found. Run `python fetch.py` first (see data/SOURCES.md)."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    s = df.set_index("date")["close"].astype(float).dropna().sort_index()
    return s[s.index <= DATA_END]


def load_fred(series: str) -> pd.Series:
    """FRED series from data/raw/fred/<series>.csv (observation_date,<series>)."""
    df = pd.read_csv(RAW / "fred" / f"{series}.csv", parse_dates=["observation_date"],
                     na_values=["."])
    s = df.set_index("observation_date")[series].astype(float).sort_index()
    return s[s.index <= DATA_END]


def load_shiller() -> pd.DataFrame:
    """Robert Shiller's monthly data (ie_data.xls, sheet 'Data').

    Columns: date (first of month), P, D, E, CPI, GS10, real_price, real_tr
    (Real Total Return Price, dividends reinvested), cape, tr_cape, nom_tr
    (= real_tr * CPI, i.e. nominal total return index).
    """
    raw = pd.read_excel(RAW / "ie_data.xls", sheet_name="Data", header=None, engine="xlrd")
    raw = raw.iloc[8:]                       # first 8 rows are the multi-line header
    raw = raw[pd.to_numeric(raw[0], errors="coerce").notna()]
    cols = {0: "date_num", 1: "P", 2: "D", 3: "E", 4: "CPI", 6: "GS10",
            7: "real_price", 9: "real_tr", 12: "cape", 14: "tr_cape"}
    df = raw[list(cols)].rename(columns=cols)
    df = df.apply(pd.to_numeric, errors="coerce")
    year = df["date_num"].astype(int)
    month = ((df["date_num"] - year) * 100).round().astype(int)
    df.insert(0, "date", pd.to_datetime(dict(year=year, month=month, day=1)))
    df = df.drop(columns="date_num").reset_index(drop=True)
    df["nom_tr"] = df["real_tr"] * df["CPI"]
    return df


def load_damodaran() -> pd.DataFrame:
    """Damodaran 'Returns by year' sheet as a tidy annual table (1928-...).

    Columns: year, sp500, tbill, tbond, baa, real_estate, gold, inflation,
    sp500_real, tbill_real, tbond_real, baa_real, real_estate_real, gold_real.
    """
    raw = pd.read_excel(RAW / "histretSP.xlsx", sheet_name="Returns by year", header=None)
    hdr_row = raw.index[raw[0].astype(str).str.strip() == "Year"][0]
    body = raw.iloc[hdr_row + 1:]
    body = body[pd.to_numeric(body[0], errors="coerce").notna()]
    # Column positions in the sheet (see the header row); the layout has been
    # stable for years: nominal returns in 1..7, inflation in 20, real in 21..27.
    cols = {0: "year", 1: "sp500", 3: "tbill", 4: "tbond", 5: "baa", 6: "real_estate",
            7: "gold", 20: "inflation", 21: "sp500_real", 23: "tbill_real",
            24: "tbond_real", 25: "baa_real", 26: "real_estate_real", 27: "gold_real"}
    df = body[list(cols)].rename(columns=cols).apply(pd.to_numeric, errors="coerce")
    df["year"] = df["year"].astype(int)
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- math
def years_between(d0, d1) -> float:
    return (pd.Timestamp(d1) - pd.Timestamp(d0)).days / 365.25


def cagr(multiple: float, years: float) -> float:
    return multiple ** (1.0 / years) - 1.0


def cash_index(yields: pd.Series, end=DATA_END) -> pd.Series:
    """Daily cash index from an annualised T-bill yield series (percent).

    cash[i] = cash[i-1] * (1 + y[i-1]/100) ** (days_between / 365)
    Continuous reinvestment, no taxes. Missing yields (holidays) are dropped.
    The index is extended to `end` using the last available yield.
    """
    y = yields.dropna()
    if y.index[-1] < end:
        y = pd.concat([y, pd.Series([y.iloc[-1]], index=[pd.Timestamp(end)])])
    days = y.index.to_series().diff().dt.days.fillna(0).to_numpy()
    growth = (1 + y.shift(1).fillna(y.iloc[0]).to_numpy() / 100) ** (days / 365.0)
    return pd.Series(np.cumprod(growth), index=y.index, name="cash")


def summarize(x: pd.Series, extra_pct=(5, 25, 75, 95)) -> dict:
    """n, median, mean, worst, best, share<0 and selected percentiles."""
    x = x.dropna()
    out = {"n": int(len(x)), "median": x.median(), "mean": x.mean(),
           "worst": x.min(), "best": x.max(), "share_negative": (x < 0).mean()}
    for p in extra_pct:
        out[f"p{p}"] = x.quantile(p / 100)
    return out


# --------------------------------------------------------------------------- output
def save(df: pd.DataFrame, name: str) -> Path:
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / name
    df.to_csv(path, index=False)
    return path


def fmt(v, kind="pct", digits=2):
    """Format one cell for markdown output."""
    if v is None or pd.isna(v):
        return ""
    if kind == "pct":
        return f"{v * 100:.{digits}f}%"
    if kind == "x":
        return f"{v:.{digits}f}x"
    if kind == "int":
        return f"{int(round(v)):,}"
    if kind == "year":
        return f"{int(v)}"
    if kind == "date":
        return pd.Timestamp(v).strftime("%Y-%m-%d")
    if kind == "num":
        return f"{v:,.{digits}f}"
    return str(v)


def md_table(df: pd.DataFrame, kinds: dict | None = None, digits=2) -> str:
    """Render a DataFrame as a GitHub markdown table (no external deps).

    `kinds` maps column -> 'pct' | 'x' | 'int' | 'year' | 'date' | 'num' | 'str',
    or a (kind, digits) tuple to override `digits` for that column.
    Columns not listed are printed as-is; float columns default to 'pct'.
    """
    kinds = kinds or {}
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            k = kinds.get(c)
            d = digits
            if isinstance(k, tuple):
                k, d = k
            if k is None:
                k = "pct" if isinstance(v, (float, np.floating)) else "str"
            cells.append(fmt(v, k, d))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def print_table(title: str, df: pd.DataFrame, kinds=None, digits=2):
    print(f"\n### {title}\n")
    print(md_table(df, kinds, digits))

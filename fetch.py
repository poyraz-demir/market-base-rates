"""Download the data that is NOT committed to this repository.

Default: the three Yahoo Finance daily series, written to data/cache/ as
date,close CSVs (the format scripts/common.py reads):

  GSPC.csv     ^GSPC     S&P 500 price index, close, from 1927-12-30
  SP500TR.csv  ^SP500TR  S&P 500 total return index, close, from 1988-01-04
  SPY.csv      SPY       SPDR S&P 500 ETF, adjusted close, from 1993-01-29

Yahoo Finance data is for personal use and is not redistributed here; every
script truncates these series at common.DATA_END, so a fresh download
reproduces the published tables.

Usage:
  python fetch.py               Yahoo chart API through urllib (no extra packages);
                                falls back to yfinance if that is installed and the API fails
  python fetch.py --yfinance    use yfinance directly (pip install yfinance)
  python fetch.py --raw         ALSO re-download Shiller, Damodaran and FRED files into
                                data/raw/ (overwrites the committed snapshots; the
                                monthly/annual tables will then move with the new data)
  python fetch.py --out DIR     write the Yahoo files somewhere else
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "data" / "cache"
RAW = ROOT / "data" / "raw"

YAHOO = {  # file name -> (symbol, field)
    "GSPC.csv": ("^GSPC", "close"),
    "SP500TR.csv": ("^SP500TR", "close"),
    "SPY.csv": ("SPY", "adjclose"),
}
RAW_URLS = {
    # Shiller's hosting URL changes from time to time; check https://shillerdata.com/ if this 404s.
    "ie_data.xls": "https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/70fec4f5-727f-4e53-b5f1-179af109c5fa/ie_data.xls",
    "histretSP.xlsx": "https://pages.stern.nyu.edu/~adamodar/pc/datasets/histretSP.xlsx",
    **{f"fred/{s}.csv": f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}"
       for s in ("DGS3MO", "DGS30", "T10YIE", "ECBDFR", "ECBMRRFR", "CPIAUCSL", "CPIAUCNS")},
}
UA = "Mozilla/5.0 (X11; Linux x86_64) market-base-rates/0.1 (+https://github.com)"


def http_get(url: str, timeout=60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_chart(payload: dict, field: str) -> pd.Series:
    """Yahoo v8 chart JSON -> Series of closes indexed by New York calendar date."""
    res = payload["chart"]["result"][0]
    ts = pd.to_datetime(res["timestamp"], unit="s", utc=True)
    dates = ts.tz_convert("America/New_York").tz_localize(None).normalize()
    if field == "adjclose":
        vals = res["indicators"]["adjclose"][0]["adjclose"]
    else:
        vals = res["indicators"]["quote"][0]["close"]
    s = pd.Series(vals, index=dates, dtype=float).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s.index.name = "date"
    return s.rename("close")


def yahoo_api(symbol: str, field: str) -> pd.Series:
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.request.quote(symbol)}?period1=-2208988800&period2={int(time.time())}"
           "&interval=1d&events=div%2Csplits")
    return parse_chart(json.loads(http_get(url)), field)


def yahoo_yfinance(symbol: str, field: str) -> pd.Series:
    import yfinance as yf  # optional dependency
    df = yf.download(symbol, period="max", interval="1d", auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    col = "Adj Close" if field == "adjclose" else "Close"
    s = df[col].dropna().astype(float)
    s.index = pd.to_datetime(s.index).normalize()
    s.index.name = "date"
    return s.rename("close")


def fetch_yahoo(out: Path, use_yfinance: bool):
    out.mkdir(parents=True, exist_ok=True)
    for fname, (symbol, field) in YAHOO.items():
        s = None
        if not use_yfinance:
            try:
                s = yahoo_api(symbol, field)
            except Exception as e:  # noqa: BLE001 - report and try the fallback
                print(f"  {symbol}: chart API failed ({e}); trying yfinance")
        if s is None:
            try:
                s = yahoo_yfinance(symbol, field)
            except ImportError:
                sys.exit("yfinance is not installed: pip install yfinance, or retry later without --yfinance")
        s.to_csv(out / fname)
        print(f"  {symbol:9s} -> {out / fname}  {s.index[0]:%Y-%m-%d} .. {s.index[-1]:%Y-%m-%d}  ({len(s)} rows)")


def fetch_raw():
    for rel, url in RAW_URLS.items():
        path = RAW / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = http_get(url)
        path.write_bytes(data)
        print(f"  {rel:20s} <- {url}  ({len(data):,} bytes)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yfinance", action="store_true", help="use the yfinance package instead of the chart API")
    ap.add_argument("--raw", action="store_true", help="also refresh data/raw/ (Shiller, Damodaran, FRED)")
    ap.add_argument("--out", type=Path, default=CACHE, help="directory for the Yahoo CSVs (default data/cache)")
    a = ap.parse_args()
    print("Yahoo Finance daily series:")
    fetch_yahoo(a.out, a.yfinance)
    if a.raw:
        print("Raw sources (overwriting data/raw/):")
        fetch_raw()
    print("done")


if __name__ == "__main__":
    main()

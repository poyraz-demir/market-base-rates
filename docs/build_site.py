#!/usr/bin/env python3
"""Render docs/index.html from results/*.csv.

Every number on the page is read from a CSV in results/. The data notes are
read from results/SUMMARY.md (data end dates), data/SOURCES.md (download
dates), scripts/common.py (DATA_END) and the "What this does and does not
show" section of README.md. Nothing is typed in by hand.

Usage:  python docs/build_site.py        (stdlib + pandas only)
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "index.html"
REPO = "https://github.com/poyraz-demir/market-base-rates"
LICENSE_URL = "https://opensource.org/license/mit/"

TITLE = "Should you wait for a crash? Market base rates"
DESCRIPTION = (
    "Reproducible base rates for the US stock market from Shiller, Damodaran, "
    "FRED and Yahoo Finance data: what followed high CAPE readings, what missing "
    "the best days costs, what happened to investors who waited in cash, how "
    "often drawdowns come, returns after buying at an all-time high, the real "
    "yield on cash, and lump sum versus dollar-cost averaging."
)

# ----------------------------------------------------------------- helpers
NUMERIC = {"pct", "spct", "x", "int", "num"}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def isna(v) -> bool:
    return v is None or (not isinstance(v, str) and pd.isna(v))


def fmt(v, kind: str = "pct", digits: int = 2) -> str:
    """Same conventions as scripts/common.py::fmt, with a typographic minus."""
    if isna(v):
        return ""
    if kind == "pct":
        s = f"{v * 100:.{digits}f}%"
    elif kind == "spct":
        s = f"{v * 100:+.{digits}f}%"
    elif kind == "x":
        s = f"{v:.{digits}f}x"
    elif kind == "int":
        s = f"{int(round(v)):,}"
    elif kind == "num":
        s = f"{v:,.{digits}f}"
    else:
        s = str(v)
    return s.replace("-", "−")


def table(df: pd.DataFrame, spec, caption: str, source: str, note: str | None = None,
          blank: str = "") -> str:
    """spec: list of (column, header, kind, digits). kind 'str' = text cell."""
    head = "".join(
        f'<th scope="col"{" class=\"num\"" if k in NUMERIC else ""}>{esc(h)}</th>'
        for _, h, k, _ in spec
    )
    rows = []
    for _, r in df.iterrows():
        cells = []
        for i, (c, _, k, d) in enumerate(spec):
            v = r[c]
            if k == "str":
                txt = blank if isna(v) else str(v)
                tag = "th scope=\"row\"" if i == 0 else "td"
                cells.append(f"<{tag}>{esc(txt)}</{tag.split()[0]}>")
            else:
                txt = fmt(v, k, d) or blank
                cells.append(f'<td class="num">{esc(txt)}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    note_html = f'<p class="src">{note}</p>' if note else ""
    return (
        f'<figure class="tbl"><figcaption>{caption}</figcaption>'
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        f'<p class="src">Source: <code>results/{esc(source)}</code></p>{note_html}</figure>'
    )


def bar_path(xz: float, xe: float, y: float, h: float, r: float = 4.0) -> str:
    """Horizontal bar from the zero line to xe: square at the baseline, rounded data end."""
    d = xe - xz
    if abs(d) < 0.5:
        return f'M{xz - 1:.1f},{y:.1f} h2 v{h:.1f} h-2 Z'
    r = min(r, abs(d), h / 2)
    if d > 0:
        return (f'M{xz:.1f},{y:.1f} H{xe - r:.1f} A{r},{r} 0 0 1 {xe:.1f},{y + r:.1f} '
                f'V{y + h - r:.1f} A{r},{r} 0 0 1 {xe - r:.1f},{y + h:.1f} H{xz:.1f} Z')
    return (f'M{xz:.1f},{y:.1f} H{xe + r:.1f} A{r},{r} 0 0 0 {xe:.1f},{y + r:.1f} '
            f'V{y + h - r:.1f} A{r},{r} 0 0 0 {xe + r:.1f},{y + h:.1f} H{xz:.1f} Z')


def hbars(items, title: str, aria: str) -> str:
    """Single-series horizontal bars. items: [(label, value, value_text)], values as fractions."""
    W, label_w, val_w, row_h, bar_h, top, bottom = 560, 190, 66, 30, 18, 6, 6
    vals = [v for _, v, _ in items]
    lo, hi = min(0.0, min(vals)), max(0.0, max(vals))
    span = (hi - lo) or 1.0
    px0 = label_w + (val_w if lo < 0 else 0)
    px1 = W - val_w

    def X(v: float) -> float:
        return px0 + (v - lo) / span * (px1 - px0)

    zero = X(0.0)
    H = top + row_h * len(items) + bottom
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(aria)}">',
           f'<title>{esc(title)}</title>',
           f'<line class="axis" x1="{zero:.1f}" y1="{top}" x2="{zero:.1f}" y2="{H - bottom}"/>']
    for i, (lab, v, txt) in enumerate(items):
        y = top + i * row_h + (row_h - bar_h) / 2
        cy = y + bar_h / 2
        xe = X(v)
        out.append(f'<path class="bar" d="{bar_path(zero, xe, y, bar_h)}"><title>{esc(lab)}: {esc(txt)}</title></path>')
        out.append(f'<text class="lab" x="{label_w - 12}" y="{cy:.1f}" text-anchor="end" dominant-baseline="central">{esc(lab)}</text>')
        if v >= 0:
            out.append(f'<text class="val" x="{xe + 8:.1f}" y="{cy:.1f}" text-anchor="start" dominant-baseline="central">{esc(txt)}</text>')
        else:
            out.append(f'<text class="val" x="{xe - 8:.1f}" y="{cy:.1f}" text-anchor="end" dominant-baseline="central">{esc(txt)}</text>')
    out.append("</svg>")
    return f'<figure class="fig"><figcaption>{title}</figcaption><div class="scroll">{"".join(out)}</div></figure>'


def md_inline(s: str) -> str:
    """Escape, then render the little markdown the README uses: **bold**, `code`, [text](url)."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(#[^)]*\)", r"\1", s)                      # in-README anchors
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def readme_limitations() -> list[str]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"^## What this does and does not show\s*$(.*?)^## ", text, re.S | re.M)
    block = m.group(1) if m else ""
    items, cur = [], []
    for line in block.splitlines():
        if line.startswith("- "):
            if cur:
                items.append(" ".join(cur))
            cur = [line[2:].strip()]
        elif line.startswith("  ") and cur:
            cur.append(line.strip())
    if cur:
        items.append(" ".join(cur))
    return [md_inline(i) for i in items]


def summary_asof() -> tuple[str, str]:
    """('Daily series end ...' sentence as HTML, generated date)."""
    text = (RESULTS / "SUMMARY.md").read_text(encoding="utf-8")
    line = next((ln.strip() for ln in text.splitlines() if ln.startswith("Daily series end")), "")
    gen = re.search(r"Generated (\d{4}-\d{2}-\d{2})", line)
    return md_inline(line), (gen.group(1) if gen else "")


def data_end() -> str:
    m = re.search(r'DATA_END\s*=\s*pd\.Timestamp\("([^"]+)"\)', (ROOT / "scripts" / "common.py").read_text())
    return m.group(1) if m else ""


def source_dates() -> dict[str, str]:
    text = (ROOT / "data" / "SOURCES.md").read_text(encoding="utf-8")
    sections = re.split(r"^### ", text, flags=re.M)
    out = {}
    for sec in sections:
        head = sec.splitlines()[0] if sec else ""
        m = re.search(r"[Dd]ownload(?:ed:?| taken on)\s+(\d{4}-\d{2}-\d{2})", sec)
        if not m:
            continue
        for key, needle in (("shiller", "Shiller"), ("damodaran", "Damodaran"), ("fred", "FRED"), ("yahoo", "Yahoo")):
            if needle in head:
                out[key] = m.group(1)
    return out


# ----------------------------------------------------------------- load
cape_now = load("02_cape_now.csv").iloc[0]
fb = load("02_forward_by_bucket.csv")
fb_real = fb[fb["kind"] == "real"].copy()
episodes = load("02_independent_episodes.csv")
gt40_runs = load("02_cape_gt40_episodes.csv")
regime = load("02_regime_split.csv")
regime_real = regime[regime["kind"] == "real"].copy()

missing = load("03_missing_days.csv")
location = load("03_best_days_location.csv")

wait_nom = load("04_waiting_nominal.csv")
wait_real = load("04_waiting_real.csv")
wait_ahead = load("04_was_cash_ever_ahead.csv")
wait_dip = load("04_wait_for_dip.csv")

dd_freq = load("05_drawdown_frequency.csv")
dd_ep = load("05_episodes_ge20.csv")
dd_below = load("05_time_below_high.csv")
dd_intra = load("05_intra_year.csv")

near_high = load("06_share_near_high.csv")
fwd_entry = load("06_forward_after_entry.csv")

cash_now = load("07_current.csv")
cash_period = load("07_real_cash_by_period.csv")
cash_neg = load("07_negative_months_by_decade.csv")

dca = load("08_lump_sum_vs_dca.csv")

# ----------------------------------------------------------------- derived values used in the prose
BUCKET_LABEL = {"all": "All months", "cape_25_30": "CAPE 25–30", "cape_gt30": "CAPE > 30",
                "cape_gt35": "CAPE > 35", "cape_gt40": "CAPE > 40"}
BUCKET_ORDER = ["all", "cape_25_30", "cape_gt30", "cape_gt35", "cape_gt40"]
fb_real["bucket_label"] = fb_real["bucket"].map(BUCKET_LABEL)
fb_real["_o"] = fb_real["bucket"].map({b: i for i, b in enumerate(BUCKET_ORDER)})
fb_real = fb_real.sort_values(["_o", "horizon_years"])


def fbv(bucket: str, horizon: int, col: str):
    r = fb_real[(fb_real["bucket"] == bucket) & (fb_real["horizon_years"] == horizon)].iloc[0]
    return r[col]


runs_per_bucket = episodes.groupby("bucket").size()
gt40_ep = episodes[episodes["bucket"] == "cape_gt40"].iloc[0]
gt40_last = gt40_runs.iloc[-1]
share_no_10y_gt30 = 1 - fbv("cape_gt30", 10, "n") / fbv("cape_gt30", 10, "months_in_bucket")
months_above = int(cape_now["months_above_current"])

SERIES_SHORT = {
    "S&P 500 price (no dividends)": "Price index, no dividends",
    "S&P 500 total return": "Total return",
    "SPY ETF adjusted close (after fees)": "SPY ETF, after fees",
}
SCENARIOS = ["buy and hold", "without 10 best days", "without 20 best days", "without 30 best days",
             "without 50 best days", "without 100 best days", "without 50 worst days",
             "without 50 best and 50 worst days"]
series_meta = missing.groupby("series").first()[["start", "end", "years", "trading_days"]]
tr_name = "S&P 500 total return"
tr_rows = missing[missing["series"] == tr_name].set_index("scenario")
price_loc = location[location["series"] == "S&P 500 price (no dividends)"].iloc[0]
within5_min, within5_max = int(location["within_5_days_of_a_worst_day"].min()), int(location["within_5_days_of_a_worst_day"].max())
in_dd20_min, in_dd20_max = int(location["in_drawdown_gt20"].min()), int(location["in_drawdown_gt20"].max())

dd10 = dd_freq[dd_freq["threshold"] == 0.1].iloc[0]
dd20 = dd_freq[dd_freq["threshold"] == 0.2].iloc[0]
dd_1929 = dd_ep.iloc[0]
tr_start = series_meta.loc[tr_name, "start"]
episodes_since_tr = int((dd_ep["peak"] >= tr_start).sum())
intra_all = dd_intra.iloc[0]

nh20 = near_high[near_high["period"] == "last 20 years"].iloc[0]
tr_series = "S&P 500 total return (1988-)"
px_series = "S&P 500 price (1928-)"


def fe(series: str, horizon: int, entry: str) -> pd.Series:
    return fwd_entry[(fwd_entry["series"] == series) & (fwd_entry["horizon_years"] == horizon)
                     & (fwd_entry["entry"] == entry)].iloc[0]


ath1, rnd1 = fe(tr_series, 1, "new all-time high day"), fe(tr_series, 1, "random day")

cash_latest = cash_now.iloc[0]
cash_2021 = cash_now[cash_now["as_of"] == "2021 average"].iloc[0]
per_0921 = cash_period[cash_period["period"] == "2009-2021"].iloc[0]
per_2023 = cash_period[cash_period["period"].str.startswith("2023")].iloc[0]
per_all = cash_period.iloc[-1]

dca12 = dca[(dca["dca_months"] == 12) & (dca["uninvested_cash"] == "cash earns 3m T-bill")].iloc[0]
dca_beats_cash_min, dca_beats_cash_max = dca["dca_beats_all_cash"].min(), dca["dca_beats_all_cash"].max()

wait_first = wait_nom.iloc[0]
ahead_max = wait_ahead.loc[wait_ahead["share_of_days_cash_ahead"].idxmax()]
ahead_first = wait_ahead.iloc[0]
dip_2018 = wait_dip[wait_dip["start"] == "2018-01-02"].iloc[0]
dip_2021 = wait_dip[wait_dip["start"] == "2021-01-04"].iloc[0]
regime_a, regime_b = regime_real["regime"].iloc[0], regime_real["regime"].iloc[-1]
n_best = int(location["best_days"].iloc[0])

asof_html, generated = summary_asof()
DATA_END = data_end()
dates = source_dates()
limitations = readme_limitations()

# ----------------------------------------------------------------- sections
P = []  # page parts

P.append(f"""
<header class="top">
  <p class="eyebrow"><a href="{REPO}">market-base-rates</a> &middot; reproducible tables, no forecasts</p>
  <h1>Should you wait for a crash? The base rates, reproduced from primary data</h1>
  <p class="lead">Distributions and counts for the US stock market, computed with plain pandas from
  Robert Shiller&rsquo;s monthly data, Aswath Damodaran&rsquo;s annual returns, FRED and Yahoo Finance
  daily series. One command (<code>python run_all.py</code>) regenerates every table; this page is
  rendered from those CSV files and contains no number typed in by hand. There are no forecasts and no
  recommendations here. Each section answers one question people ask before investing and then says
  what the table does and does not show.</p>
  <p class="asof">{asof_html}</p>
  <nav class="toc" aria-label="Contents"><ol>
    <li><a href="#cape">What happened after CAPE was this high?</a></li>
    <li><a href="#best-days">What does missing the best days cost, and where are those days?</a></li>
    <li><a href="#waiting">What happened to people who waited in cash?</a></li>
    <li><a href="#drawdowns">How often do drawdowns come, and how long does recovery take?</a></li>
    <li><a href="#all-time-high">Buying at an all-time high vs any day</a></li>
    <li><a href="#cash-yield">What does waiting cost today? The real yield on cash</a></li>
    <li><a href="#lump-sum">Lump sum vs dollar-cost averaging</a></li>
    <li><a href="#data">Data and method</a> &middot; <a href="#limitations">Limitations</a></li>
  </ol></nav>
</header>
""")

# 1 ------------------------------------------------------------------ CAPE
cape_tbl = table(
    pd.DataFrame([cape_now]),
    [("month", "Month", "str", 0), ("cape", "CAPE", "num", 2), ("cape_median_all", "Median, all months", "num", 2),
     ("percentile", "Percentile", "pct", 2), ("months_above_current", "Months above current", "int", 0),
     ("months_with_cape", "Months with CAPE", "int", 0), ("peak_cape", "Peak CAPE", "num", 2), ("peak_month", "Peak month", "str", 0)],
    "Where CAPE stands", "02_cape_now.csv")

bucket_tbl = table(
    fb_real,
    [("bucket_label", "Bucket", "str", 0), ("months_in_bucket", "Months in bucket", "int", 0),
     ("horizon_years", "Horizon, years", "int", 0), ("n", "Windows (n)", "int", 0),
     ("median", "Median", "pct", 2), ("p25", "25th pct", "pct", 2), ("p75", "75th pct", "pct", 2),
     ("worst", "Worst", "pct", 2), ("best", "Best", "pct", 2), ("share_negative", "Share negative", "pct", 2)],
    "Forward real annualised return by CAPE bucket (overlapping monthly windows)", "02_forward_by_bucket.csv",
    note="Rows with <code>kind = real</code>; the CSV also carries nominal rows.")

cape_chart = hbars(
    [(f"{BUCKET_LABEL[b]} (n = {fmt(fbv(b, 10, 'n'), 'int')})", float(fbv(b, 10, "median")), fmt(fbv(b, 10, "median"), "pct", 2))
     for b in BUCKET_ORDER],
    "Median real return over the following 10 years, per year, by CAPE at entry",
    "Bar chart of the median 10-year forward real annualised return for each CAPE bucket; values are in the table above.")

ep_tbl = table(
    episodes.assign(bucket_label=episodes["bucket"].map(BUCKET_LABEL)),
    [("bucket_label", "Bucket", "str", 0), ("run_start", "Run start", "str", 0), ("run_end", "Run end", "str", 0),
     ("months", "Months", "int", 0), ("median_real_10y", "Median real 10y", "pct", 2), ("median_nom_10y", "Median nominal 10y", "pct", 2)],
    "Contiguous runs of months behind the 10-year statistics (months that already have a 10-year outcome)", "02_independent_episodes.csv")

gt40_tbl = table(
    gt40_runs,
    [("run_start", "Run start", "str", 0), ("run_end", "Run end", "str", 0), ("months", "Months", "int", 0)],
    "Every stretch of months with CAPE > 40", "02_cape_gt40_episodes.csv")

regime_tbl = table(
    regime_real,
    [("regime", "Entries", "str", 0), ("horizon_years", "Horizon, years", "int", 0), ("n", "Windows (n)", "int", 0),
     ("median", "Median", "pct", 2), ("mean", "Mean", "pct", 2), ("worst", "Worst", "pct", 2), ("best", "Best", "pct", 2),
     ("share_negative", "Share negative", "pct", 2)],
    "CAPE > 30 entries split by regime, real annualised", "02_regime_split.csv",
    note="Rows with <code>kind = real</code>.")

P.append(f"""
<section id="cape">
  <h2>What happened after CAPE was this high?</h2>
  <p>Shiller&rsquo;s cyclically adjusted price/earnings ratio for {esc(cape_now['month'])} is {fmt(cape_now['cape'], 'num', 2)},
  against a median of {fmt(cape_now['cape_median_all'], 'num', 2)} across the {fmt(cape_now['months_with_cape'], 'int')} months
  with a reading. Only {months_above} of those months were higher; the peak was {fmt(cape_now['peak_cape'], 'num', 2)}
  in {esc(cape_now['peak_month'])}.</p>
  {cape_tbl}
  <p>The table below takes every month in a bucket and looks 1, 3, 5 and 10 years ahead, in real
  (CPI-deflated) total-return terms.</p>
  {bucket_tbl}
  {cape_chart}
  <h3>What this does and does not show</h3>
  <p>The windows overlap. Consecutive monthly starts share almost their whole path, so <em>n</em> counts
  windows, not independent outcomes. The next table lists the contiguous runs behind the 10-year rows:
  CAPE &gt; 30 rests on {int(runs_per_bucket['cape_gt30'])} runs, CAPE &gt; 35 on {int(runs_per_bucket['cape_gt35'])} runs inside the
  dot-com bubble, and <strong>CAPE &gt; 40 is a single episode</strong> ({esc(gt40_ep['run_start'])} to {esc(gt40_ep['run_end'])},
  {int(gt40_ep['months'])} months) counted {fmt(fbv('cape_gt40', 10, 'n'), 'int')} times. The {int(gt40_last['months'])}-month run
  that began in {esc(gt40_last['run_start'])} has no outcome yet, at any horizon.</p>
  {ep_tbl}
  {gt40_tbl}
  <p>Two regimes sit in one bucket. {fmt(share_no_10y_gt30, 'pct', 0)} of CAPE &gt; 30 months (every entry from
  mid-2017 on) do not have a 10-year outcome, and the entries that do come from {esc(regime_a)}.
  Splitting the bucket by regime shows that the pooled median describes neither group: the {esc(regime_a)}
  entries were followed by a negative median real return at 3 and 5 years, the {esc(regime_b)} entries by a
  positive return in every 3- and 5-year window.</p>
  {regime_tbl}
</section>
""")

# 2 ------------------------------------------------------------------ best days
def missing_pivot() -> str:
    series = list(series_meta.index)
    head1 = '<th scope="col" rowspan="2">Scenario</th>' + "".join(
        f'<th scope="colgroup" colspan="2">{esc(SERIES_SHORT[s])}, {esc(str(series_meta.loc[s, "start"])[:4])}&ndash;{esc(str(series_meta.loc[s, "end"])[:4])}</th>'
        for s in series)
    head2 = "".join('<th scope="col" class="num">Multiple</th><th scope="col" class="num">CAGR</th>' for _ in series)
    rows = []
    for sc in SCENARIOS:
        cells = [f'<th scope="row">{esc(sc)}</th>']
        for s in series:
            r = missing[(missing["series"] == s) & (missing["scenario"] == sc)].iloc[0]
            cells.append(f'<td class="num">{esc(fmt(r["multiple"], "x", 2))}</td><td class="num">{esc(fmt(r["cagr"], "pct", 2))}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (f'<figure class="tbl"><figcaption>Growth multiple and CAGR over the same calendar span, with the listed days removed</figcaption>'
            f'<div class="scroll"><table><thead><tr>{head1}</tr><tr>{head2}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="src">Source: <code>results/03_missing_days.csv</code></p></figure>')


days_chart = hbars(
    [(sc, float(tr_rows.loc[sc, "cagr"]), fmt(tr_rows.loc[sc, "cagr"], "pct", 2))
     for sc in ["buy and hold", "without 10 best days", "without 20 best days", "without 30 best days",
                "without 50 best days", "without 100 best days", "without 50 worst days"]],
    f"S&P 500 total return, {esc(str(series_meta.loc[tr_name, 'start'])[:4])}–{esc(str(series_meta.loc[tr_name, 'end'])[:4])}: CAGR with the listed days removed",
    "Bar chart of the S&P 500 total return CAGR when the best or worst days are removed; values are in the table above.")

loc_tbl = table(
    location.assign(series_label=location["series"].map(SERIES_SHORT)),
    [("series_label", "Series", "str", 0), ("best_days", "Best days counted", "int", 0),
     ("in_drawdown_gt20", "Inside a drawdown of 20%+", "int", 0), ("in_drawdown_gt10", "Inside a drawdown of 10%+", "int", 0),
     ("within_5_days_of_a_worst_day", "Within 5 trading days of one of the 50 worst days", "int", 0)],
    "Where the 50 best days sit", "03_best_days_location.csv")

P.append(f"""
<section id="best-days">
  <h2>What does missing the best days cost, and where are those days?</h2>
  <p>Three daily series, each over its own full span: the S&amp;P 500 price index from
  {esc(str(series_meta.loc['S&P 500 price (no dividends)', 'start']))} (no dividends), the S&amp;P 500 total return index
  from {esc(str(series_meta.loc[tr_name, 'start']))}, and the SPY ETF from
  {esc(str(series_meta.loc['SPY ETF adjusted close (after fees)', 'start']))} (dividends reinvested, net of the fund&rsquo;s
  expenses). Each scenario deletes the listed days and compounds the rest.</p>
  {missing_pivot()}
  {days_chart}
  <h3>What this does and does not show</h3>
  <p>Removing the best days and removing the worst days are the same arithmetic, and both are shown
  because neither is something an investor can actually do: nobody is out of the market only on the
  best days. The reason the cost looks so large is where those days sit. Of the {n_best} best days,
  {in_dd20_min}&ndash;{in_dd20_max} (depending on the series) came while the index was more than 20% below its
  high, and {within5_min}&ndash;{within5_max} fell within five trading days of one of the 50 worst days.
  Big up days are part of crashes, not a reward for sitting through calm markets.</p>
  {loc_tbl}
</section>
""")

# 3 ------------------------------------------------------------------ waiting in cash
nom_tbl = table(
    wait_nom,
    [("start", "Start", "str", 0), ("reason", "Why this date", "str", 0), ("years", "Years", "num", 2),
     ("stocks_multiple", "Stocks", "x", 2), ("stocks_cagr", "Stocks CAGR", "pct", 2),
     ("cash_multiple", "Cash", "x", 2), ("cash_cagr", "Cash CAGR", "pct", 2), ("cash_shortfall", "Cash shortfall", "pct", 2)],
    "Moved to 3-month T-bills on that date vs invested in the S&P 500 total return index the same day, nominal", "04_waiting_nominal.csv",
    blank="—")

real_tbl = table(
    wait_real,
    [("start", "Start", "str", 0), ("inflation_multiple", "CPI", "x", 2),
     ("stocks_real_multiple", "Stocks, real", "x", 2), ("stocks_real_cagr", "Stocks real CAGR", "pct", 2),
     ("cash_real_multiple", "Cash, real", "x", 2), ("cash_real_cagr", "Cash real CAGR", "pct", 2)],
    "Same, CPI-deflated", "04_waiting_real.csv")

ahead_tbl = table(
    wait_ahead,
    [("start", "Start", "str", 0), ("min_stocks_to_cash", "Lowest stocks / cash ratio", "num", 2), ("min_date", "On", "str", 0),
     ("last_day_cash_ahead", "Last day cash was ahead", "str", 0), ("share_of_days_cash_ahead", "Share of days cash ahead", "pct", 2)],
    "Was cash ever ahead?", "04_was_cash_ever_ahead.csv")

dip_tbl = table(
    wait_dip,
    [("start", "Start", "str", 0), ("invest_immediately", "Invest at once", "x", 2),
     ("wait_for_10pct", "Wait for −10%", "x", 2), ("wait_for_10pct_entry", "Entered", "str", 0), ("wait_for_10pct_vs_immediate", "vs at once", "spct", 2),
     ("wait_for_20pct", "Wait for −20%", "x", 2), ("wait_for_20pct_entry", "Entered", "str", 0), ("wait_for_20pct_vs_immediate", "vs at once", "spct", 2),
     ("wait_for_30pct", "Wait for −30%", "x", 2), ("wait_for_30pct_entry", "Entered", "str", 0), ("wait_for_30pct_vs_immediate", "vs at once", "spct", 2)],
    "Stay in T-bills until the index is X% below its running high since the start date, then go all in (final multiple)", "04_wait_for_dip.csv",
    note="&ldquo;never&rdquo; = the trigger did not fire before the data end, so the money stayed in T-bills.", blank="never")

P.append(f"""
<section id="waiting">
  <h2>What happened to people who waited in cash?</h2>
  <p>Five start dates: one chosen for what was said that day ({esc(wait_first['reason'])},
  {esc(wait_first['start'])}) and four first-trading-days of a January. &ldquo;Cash&rdquo; is a rolling position in 3-month
  Treasury bills; &ldquo;stocks&rdquo; is the S&amp;P 500 with dividends reinvested. Both paths run to the data end.</p>
  {nom_tbl}
  {real_tbl}
  {ahead_tbl}
  <p>The last table turns waiting into a rule: stay in T-bills until the index has fallen 10, 20 or 30%
  from its highest close since the start date, then buy everything.</p>
  {dip_tbl}
  <h3>What this does and does not show</h3>
  <p>These are five paths, not a distribution, and the cash series only exists from late 1981, so no
  earlier start is possible. From {esc(ahead_first['start'])} the cash position was ahead on
  {fmt(ahead_first['share_of_days_cash_ahead'], 'pct', 2)} of trading days and for the last time on
  {esc(ahead_first['last_day_cash_ahead'])}; the largest share in any case is {fmt(ahead_max['share_of_days_cash_ahead'], 'pct', 2)}
  (start {esc(ahead_max['start'])}). The dip rule can win: the {esc(dip_2018['start'][:4])} start ends
  {fmt(dip_2018['wait_for_30pct_vs_immediate'], 'spct', 2)} ahead by waiting for a 30% fall, because that fall came on
  {esc(str(dip_2018['wait_for_30pct_entry']))}. The {esc(dip_2021['start'][:4])} start shows the other side: a 30% fall never came, and the
  money is still in T-bills, {fmt(dip_2021['wait_for_30pct_vs_immediate'], 'spct', 2)} against investing at once.</p>
</section>
""")

# 4 ------------------------------------------------------------------ drawdowns
freq_tbl = table(
    dd_freq,
    [("threshold", "Decline of at least", "pct", 0), ("episodes", "Episodes", "int", 0), ("years_per_episode", "Years per episode", "num", 1),
     ("median_depth", "Median depth", "pct", 1), ("worst_depth", "Worst depth", "pct", 1),
     ("median_peak_to_trough_days", "Median peak to trough, days", "int", 0), ("median_trough_to_recovery_days", "Median trough to recovery, days", "int", 0),
     ("median_full_cycle_days", "Median full cycle, days", "int", 0), ("mean_full_cycle_years", "Mean full cycle, years", "num", 1),
     ("max_full_cycle_years", "Longest full cycle, years", "num", 1)],
    "Drawdown base rates, S&P 500 price index (calendar days)", "05_drawdown_frequency.csv")

ep20_tbl = table(
    dd_ep,
    [("peak", "Peak", "str", 0), ("trough", "Trough", "str", 0), ("depth", "Depth", "pct", 1),
     ("peak_to_trough_days", "Peak to trough, days", "int", 0), ("recovery", "Back to the old high", "str", 0), ("full_cycle_years", "Full cycle, years", "num", 1)],
    "Every decline of 20% or more", "05_episodes_ge20.csv")

below_tbl = table(
    dd_below,
    [("period", "Period", "str", 0), ("days", "Trading days", "int", 0), ("below_high_by_10pct_or_more", "10%+ below high", "pct", 1),
     ("below_high_by_20pct_or_more", "20%+ below high", "pct", 1), ("below_high_by_30pct_or_more", "30%+ below high", "pct", 1)],
    "Share of trading days spent below the running high", "05_time_below_high.csv")

intra_tbl = table(
    dd_intra,
    [("period", "Period", "str", 0), ("years", "Years", "int", 0), ("mean_intra_year_drawdown", "Mean intra-year drawdown", "pct", 1),
     ("median_intra_year_drawdown", "Median", "pct", 1), ("positive_calendar_years", "Positive calendar years", "int", 0),
     ("share_years_dd_ge_5pct", "Years with a 5%+ dip", "pct", 1), ("share_years_dd_ge_10pct", "10%+", "pct", 1),
     ("share_years_dd_ge_15pct", "15%+", "pct", 1), ("share_years_dd_ge_20pct", "20%+", "pct", 1)],
    "Intra-year drawdowns (complete calendar years)", "05_intra_year.csv")

P.append(f"""
<section id="drawdowns">
  <h2>How often do drawdowns come, and how long does recovery take?</h2>
  <p>Price index, daily closes, from {esc(str(series_meta.loc['S&P 500 price (no dividends)', 'start']))}. An episode starts
  at a running high, ends when the old high is regained, and counts if the decline in between reached the threshold.</p>
  {freq_tbl}
  <p>A decline of 10% or more has arrived once every {fmt(dd10['years_per_episode'], 'num', 1)} years on average, one of 20%
  or more once every {fmt(dd20['years_per_episode'], 'num', 1)} years. The median 20% episode took
  {fmt(dd20['median_peak_to_trough_days'], 'int')} days from peak to trough and {fmt(dd20['median_trough_to_recovery_days'], 'int')} more
  to get back to the old high.</p>
  {ep20_tbl}
  {below_tbl}
  {intra_tbl}
  <h3>What this does and does not show</h3>
  <p>Everything here is nominal and price-only, because a daily total-return series only exists from
  {esc(str(tr_start)[:4])}. The {fmt(dd_1929['full_cycle_years'], 'num', 1)}-year recovery from the {esc(str(dd_1929['peak'])[:4])} peak is
  therefore overstated: with dividends reinvested and the deflation of the 1930s, the real recovery came
  earlier. {episodes_since_tr} of the {len(dd_ep)} declines of 20% or more began after the total-return series starts.
  Intra-year drawdowns are the base rate for &ldquo;something will go wrong this year&rdquo;: in
  {fmt(intra_all['share_years_dd_ge_10pct'], 'pct', 1)} of years the index fell 10% or more at some point, and
  {fmt(intra_all['positive_calendar_years'], 'int')} of {fmt(intra_all['years'], 'int')} years still closed higher than they opened.</p>
</section>
""")

# 5 ------------------------------------------------------------------ all-time highs
near_tbl = table(
    near_high,
    [("period", "Period", "str", 0), ("days", "Trading days", "int", 0), ("new_high_days", "New-high days", "int", 0),
     ("share_new_high", "Share new high", "pct", 1), ("within_1pct", "Within 1% of high", "pct", 1), ("within_2pct", "Within 2%", "pct", 1),
     ("within_5pct", "Within 5%", "pct", 1), ("within_10pct", "Within 10%", "pct", 1), ("below_high_gt20pct", "20%+ below high", "pct", 1)],
    "How often the price index sits near its all-time high", "06_share_near_high.csv")

ENTRY_SPEC = [("entry", "Bought on a", "str", 0), ("n", "Windows (n)", "int", 0), ("median", "Median", "pct", 2), ("mean", "Mean", "pct", 2),
              ("share_negative", "Share negative", "pct", 2), ("p5", "5th pct", "pct", 2), ("p95", "95th pct", "pct", 2), ("worst", "Worst", "pct", 2)]
fe_tr1 = table(fwd_entry[(fwd_entry["series"] == tr_series) & (fwd_entry["horizon_years"] == 1)], ENTRY_SPEC,
               "Return over the following 1 year, S&P 500 total return, 1988 onwards", "06_forward_after_entry.csv")
fe_px1 = table(fwd_entry[(fwd_entry["series"] == px_series) & (fwd_entry["horizon_years"] == 1)], ENTRY_SPEC,
               "Same, price index 1928 onwards (no dividends)", "06_forward_after_entry.csv")
fe_tr_h = table(
    fwd_entry[(fwd_entry["series"] == tr_series) & (fwd_entry["entry"].isin(["random day", "new all-time high day", "20%+ below high"]))]
    .assign(_o=lambda d: d["entry"].map({"random day": 0, "new all-time high day": 1, "20%+ below high": 2}))
    .sort_values(["horizon_years", "_o"]),
    [("horizon_years", "Horizon, years", "int", 0), ("entry", "Bought on a", "str", 0), ("n", "Windows (n)", "int", 0),
     ("median", "Median, annualised", "pct", 2), ("share_negative", "Share negative", "pct", 2), ("p5", "5th pct", "pct", 2), ("worst", "Worst", "pct", 2)],
    "Longer horizons, S&P 500 total return, annualised", "06_forward_after_entry.csv")

P.append(f"""
<section id="all-time-high">
  <h2>Buying at an all-time high vs any day</h2>
  <p>Over the last 20 years the price index closed at a new all-time high on {fmt(nh20['share_new_high'], 'pct', 1)} of trading days and
  within 5% of one on {fmt(nh20['within_5pct'], 'pct', 1)} and within 10% on {fmt(nh20['within_10pct'], 'pct', 1)}.
  A rule of not buying near a high excludes most days.</p>
  {near_tbl}
  <p>The next tables take every trading day as a purchase date, group the days by distance from the
  running high, and compare the return over the following year.</p>
  {fe_tr1}
  {fe_px1}
  {fe_tr_h}
  <h3>What this does and does not show</h3>
  <p>In the total-return series a purchase on a new-high day (n = {fmt(ath1['n'], 'int')}) was followed by a median
  1-year return of {fmt(ath1['median'], 'pct', 2)}, against {fmt(rnd1['median'], 'pct', 2)} for a random day, and was negative
  {fmt(ath1['share_negative'], 'pct', 2)} of the time against {fmt(rnd1['share_negative'], 'pct', 2)}. The distribution after a
  high is narrower, not higher: the 5th percentile is {fmt(ath1['p5'], 'pct', 2)} against {fmt(rnd1['p5'], 'pct', 2)}.
  <em>n</em> counts overlapping daily windows, and the total-return series covers {esc(str(tr_start)[:4])} onwards only, a
  period with {episodes_since_tr} declines of 20% or more; the price-index table reaches back to 1928 and includes
  1929, which is why its worst cases are so much deeper.</p>
</section>
""")

# 6 ------------------------------------------------------------------ real cash yield
now_tbl = table(
    cash_now,
    [("as_of", "As of", "str", 0), ("basis", "Basis", "str", 0), ("nominal", "3-month T-bill", "pct", 2),
     ("cpi_yoy", "CPI, year on year", "pct", 2), ("real", "Real yield", "pct", 2)],
    "Real yield on cash now vs 2021", "07_current.csv")

period_tbl = table(
    cash_period,
    [("period", "Period", "str", 0), ("months", "Months", "int", 0), ("mean_nominal", "Mean 3-month yield", "pct", 2),
     ("mean_cpi_yoy", "Mean CPI y/y", "pct", 2), ("mean_real", "Mean real", "pct", 2), ("min_real", "Lowest real", "pct", 2),
     ("max_real", "Highest real", "pct", 2), ("share_months_real_negative", "Months with negative real yield", "pct", 2)],
    "Real yield on 3-month T-bills by period (monthly, 1982 onwards)", "07_real_cash_by_period.csv")

neg_tbl = table(
    cash_neg,
    [("period", "Period", "str", 0), ("months", "Months", "int", 0), ("share_months_real_negative", "Months with negative real yield", "pct", 2),
     ("mean_real", "Mean real yield", "pct", 2)],
    "Share of months with a negative real cash yield", "07_negative_months_by_decade.csv")

P.append(f"""
<section id="cash-yield">
  <h2>What does waiting cost today? The real yield on cash</h2>
  <p>Real yield here is the 3-month Treasury bill yield minus CPI inflation over the previous twelve
  months. On {esc(cash_latest['as_of'])} that is {fmt(cash_latest['nominal'], 'pct', 2)} minus {fmt(cash_latest['cpi_yoy'], 'pct', 2)},
  a real yield of {fmt(cash_latest['real'], 'pct', 2)}. The 2021 average was {fmt(cash_2021['real'], 'pct', 2)}.</p>
  {now_tbl}
  {period_tbl}
  {neg_tbl}
  <h3>What this does and does not show</h3>
  <p>Waiting in cash forgoes whatever stocks return; that cost is in the sections above and does not
  depend on the rate. What the rate changes is whether cash also loses purchasing power while you wait.
  Between 2009 and 2021 the real yield was negative in {fmt(per_0921['share_months_real_negative'], 'pct', 2)} of months
  (mean {fmt(per_0921['mean_real'], 'pct', 2)}); since 2023 in {fmt(per_2023['share_months_real_negative'], 'pct', 2)} of months
  (mean {fmt(per_2023['mean_real'], 'pct', 2)}). The whole 1982&ndash;{esc(str(per_all['period']).split('-', 1)[1])} history averages
  {fmt(per_all['mean_real'], 'pct', 2)}. The series starts in 1982 because FRED&rsquo;s daily 3-month yield does, and the
  latest CPI print lags the yield by a few weeks.</p>
</section>
""")

# 7 ------------------------------------------------------------------ lump sum vs DCA
dca_tbl = table(
    dca,
    [("dca_months", "DCA over, months", "int", 0), ("uninvested_cash", "Uninvested cash", "str", 0), ("windows", "Windows", "int", 0),
     ("ls_beats_dca", "Lump sum beats DCA", "pct", 1), ("median_ls_minus_dca", "Median lump sum minus DCA", "pct", 1),
     ("ls_p5", "Lump sum 5th pct", "x", 3), ("dca_p5", "DCA 5th pct", "x", 3), ("ls_median", "Lump sum median", "x", 3),
     ("dca_median", "DCA median", "x", 3), ("dca_beats_all_cash", "DCA beats staying in cash", "pct", 1)],
    "Lump sum vs spreading the purchase (S&P 500 total return, monthly entries 1988 onwards, wealth after 12 months)", "08_lump_sum_vs_dca.csv")

P.append(f"""
<section id="lump-sum">
  <h2>Lump sum vs dollar-cost averaging</h2>
  <p>Each of the {fmt(dca12['windows'], 'int')} monthly start dates since 1988 is a window. &ldquo;Lump sum&rdquo; invests everything
  on day one; &ldquo;DCA&rdquo; invests in equal monthly slices over 3, 6 or 12 months, with the uninvested part either
  earning the 3-month T-bill rate or nothing. Both are measured after 12 months.</p>
  {dca_tbl}
  <h3>What this does and does not show</h3>
  <p>Spreading the purchase over 12 months lost to investing at once in {fmt(dca12['ls_beats_dca'], 'pct', 1)} of windows, by a
  median {fmt(dca12['median_ls_minus_dca'], 'pct', 1)} of the amount invested, when the idle cash earned T-bills. What it bought
  was a better bad case: the 5th-percentile outcome is {fmt(dca12['dca_p5'], 'x', 3)} for DCA against {fmt(dca12['ls_p5'], 'x', 3)}
  for the lump sum. Either choice beat staying in cash in {fmt(dca_beats_cash_min, 'pct', 1)}&ndash;{fmt(dca_beats_cash_max, 'pct', 1)}
  of windows. The design follows Vanguard&rsquo;s 2023 study but uses a different index and period, so the hit
  rates are comparable in spirit, not identical.</p>
</section>
""")

# 8 ------------------------------------------------------------------ data, limitations, footer
P.append(f"""
<section id="data">
  <h2>Data and method</h2>
  <p>All computation is plain pandas in eight scripts, one per question; <code>python run_all.py</code> writes
  <code>results/*.csv</code> and <code>results/SUMMARY.md</code>, and <code>python docs/build_site.py</code> renders this
  page from those files. Every daily series is cut at <code>DATA_END = {esc(DATA_END)}</code> so a later download
  reproduces the same tables. Tables generated {esc(generated)}.</p>
  <dl class="sources">
    <dt>Robert Shiller, <em>Irrational Exuberance</em> data (shillerdata.com)</dt>
    <dd>Monthly S&amp;P composite price, dividends, earnings, CPI and CAPE from 1871. Snapshot downloaded {esc(dates.get('shiller', ''))}. Used for the CAPE tables.</dd>
    <dt>Aswath Damodaran, Historical Returns on Stocks, Bonds and Bills (NYU Stern)</dt>
    <dd>Annual returns from 1928. Snapshot downloaded {esc(dates.get('damodaran', ''))}. Used for long-run returns.</dd>
    <dt>FRED, Federal Reserve Bank of St. Louis</dt>
    <dd><code>DGS3MO</code> (3-month Treasury yield), <code>CPIAUCSL</code> and <code>CPIAUCNS</code> (CPI-U) and others. Downloaded {esc(dates.get('fred', ''))}. Used for cash returns, real yields and inflation adjustment.</dd>
    <dt>Yahoo Finance daily series</dt>
    <dd><code>^GSPC</code> (price, 1927 onwards), <code>^SP500TR</code> (total return, 1988 onwards), <code>SPY</code> (adjusted close, 1993 onwards). Downloaded {esc(dates.get('yahoo', ''))}, last observation {esc(DATA_END)}. Not redistributed; <code>python fetch.py</code> re-downloads them.</dd>
  </dl>
  <p>Full source list, coverage and redistribution terms: <a href="{REPO}/blob/master/data/SOURCES.md">data/SOURCES.md</a>.</p>
</section>

<section id="limitations">
  <h2>Limitations</h2>
  <ul class="limits">
    {"".join(f"<li>{li}</li>" for li in limitations)}
  </ul>
</section>

<footer>
  <p>Code and tables: <a href="{REPO}">{REPO.replace('https://', '')}</a>, MIT licence. Each data source keeps its
  own terms. This page is not investment advice.</p>
</footer>
""")

# ----------------------------------------------------------------- head + css
jsonld = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "name": TITLE,
    "description": DESCRIPTION,
    "url": REPO,
    "license": LICENSE_URL,
    "isAccessibleForFree": True,
    "dateModified": generated,
    "temporalCoverage": f"1871-01/{DATA_END}",
    "keywords": ["S&P 500", "CAPE", "Shiller PE", "missing the best days", "waiting in cash", "drawdowns",
                 "all-time high", "real yield", "dollar-cost averaging", "base rates"],
    "isBasedOn": ["https://shillerdata.com/", "https://pages.stern.nyu.edu/~adamodar/pc/datasets/histretSP.xlsx",
                  "https://fred.stlouisfed.org/"],
    "distribution": {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{REPO}/tree/master/results"},
}

CSS = """
:root{
  color-scheme:light dark;
  --bg:#f5f7f6; --surface:#ffffff; --fg:#1b2422; --fg-2:#485451; --fg-3:#6f7c78;
  --rule:#dde3e0; --rule-strong:#b6c0bc; --accent:#1f6b64; --accent-soft:#e2eeec; --link:#1a5f59;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#141918; --surface:#1b2120; --fg:#e6ebe9; --fg-2:#b3bdb9; --fg-3:#86918d;
    --rule:#29322f; --rule-strong:#45514d; --accent:#62b7ad; --accent-soft:#1c2e2b; --link:#7fc9c0;
  }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--fg);
  font-family:"Source Sans 3","Source Sans Pro","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  font-size:1.0625rem; line-height:1.55; padding-inline:16px;
}
.page{max-width:58rem; margin:0 auto; padding-block:2.5rem 4rem}
p,li,h1,h2,h3,dl,.lead{max-width:65ch}
h1,h2,h3{
  font-family:"Source Serif 4","Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-weight:600; line-height:1.15; text-wrap:balance; margin:0 0 .6em;
}
h1{font-size:clamp(1.9rem,4.6vw,2.6rem); letter-spacing:-.01em; margin-top:.4rem}
h2{font-size:clamp(1.35rem,3vw,1.65rem); margin-top:0}
h3{font-family:inherit; font-size:.8rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--fg-3); margin:2rem 0 .4rem}
p{margin:0 0 1rem}
a{color:var(--link); text-decoration-thickness:1px; text-underline-offset:2px}
a:hover{text-decoration-thickness:2px}
code{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace; font-size:.88em; background:var(--surface); border:1px solid var(--rule); border-radius:3px; padding:0 .3em}
.eyebrow{font-size:.85rem; color:var(--fg-3); letter-spacing:.04em; text-transform:uppercase; margin-bottom:.5rem}
.lead{font-size:1.15rem; line-height:1.5; color:var(--fg-2)}
.asof{font-size:.9rem; color:var(--fg-3)}
.toc{margin:1.5rem 0 0; padding:1rem 1.25rem; border:1px solid var(--rule); border-radius:6px; background:var(--surface); max-width:65ch}
.toc ol{margin:0; padding-left:1.2rem}
.toc li{margin:.15rem 0}
section{margin-top:3.5rem; padding-top:2rem; border-top:1px solid var(--rule)}
figure{margin:1.6rem 0}
figcaption{font-weight:600; font-size:.95rem; margin-bottom:.45rem; color:var(--fg); max-width:65ch; text-wrap:balance}
.scroll{overflow-x:auto; -webkit-overflow-scrolling:touch; max-width:100%}
table{border-collapse:collapse; width:100%; font-size:.9rem; line-height:1.35; background:var(--surface)}
th,td{padding:.42rem .65rem; border-bottom:1px solid var(--rule); text-align:left; vertical-align:top; white-space:nowrap}
thead th{font-weight:600; color:var(--fg-2); font-size:.78rem; letter-spacing:.02em; border-bottom:1px solid var(--rule-strong); vertical-align:bottom}
thead th[colspan]{text-align:center; border-bottom:1px solid var(--rule)}
tbody th{font-weight:500}
.num{text-align:right; font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace; font-variant-numeric:tabular-nums; font-size:.84rem}
thead th.num{font-family:inherit; font-size:.78rem}
tbody tr:hover{background:var(--accent-soft)}
.src{font-size:.8rem; color:var(--fg-3); margin:.4rem 0 0; max-width:none}
.src code{font-size:.9em}
.chart{display:block; width:100%; min-width:520px; height:auto; font-size:13px}
.chart .bar{fill:var(--accent)}
.chart .lab{fill:var(--fg)}
.chart .val{fill:var(--fg-2); font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-variant-numeric:tabular-nums}
.chart .axis{stroke:var(--rule-strong); stroke-width:1}
.sources dt{font-weight:600; margin-top:.9rem}
.sources dd{margin:.15rem 0 0; color:var(--fg-2)}
.limits li{margin:.5rem 0}
footer{margin-top:3.5rem; padding-top:1.5rem; border-top:1px solid var(--rule); font-size:.9rem; color:var(--fg-3)}
@media (max-width:480px){ body{font-size:1rem} table{font-size:.85rem} }
"""

HEAD = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(TITLE)}</title>
<meta name="description" content="{esc(DESCRIPTION)}">
<meta property="og:title" content="{esc(TITLE)}">
<meta property="og:description" content="{esc(DESCRIPTION)}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://poyraz-demir.github.io/market-base-rates/">
<link rel="canonical" href="https://poyraz-demir.github.io/market-base-rates/">
<meta name="robots" content="index,follow">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False, indent=1)}</script>
<style>{CSS}</style>
</head>
<body>
<div class="page">
"""

TAIL = """
</div>
</body>
</html>
"""


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    page = HEAD + "".join(P) + TAIL
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

# Data sources

All files in `data/raw/` are unmodified snapshots. Download dates are when the
snapshot was taken; keep the attribution below if you redistribute them.

## Included in the repository

### Robert Shiller, "Irrational Exuberance" data - `data/raw/ie_data.xls`

- Source: Robert J. Shiller, Yale University. https://shillerdata.com/
  (historically http://www.econ.yale.edu/~shiller/data.htm)
- Content: monthly S&P composite price, dividends, earnings, CPI, GS10, real
  total-return price index, CAPE (P/E10), TR-CAPE; January 1871 - September 2026.
- Downloaded: 2026-09-20. File last saved by the author on 2026-09-02
  (September price = 1 September close; the latest CPI months are the
  author's estimates, as noted in the file).
- Terms: published by the author for public use with no formal license
  statement on the site; it is customarily reused and redistributed with
  attribution. Cite: Shiller, R. J., *Irrational Exuberance*, Princeton
  University Press (2000, 2005, 2015), data updated at shillerdata.com.

### Aswath Damodaran, "Historical Returns on Stocks, Bonds and Bills" - `data/raw/histretSP.xlsx`

- Source: Aswath Damodaran, NYU Stern.
  https://pages.stern.nyu.edu/~adamodar/pc/datasets/histretSP.xlsx
  (index page: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html)
- Content: annual returns 1928-2025 on the S&P 500 (with dividends), 3-month
  T-bills, 10-year T-bonds, Baa corporate bonds, US home prices, gold, US CPI;
  nominal and real; sheet "Returns by year".
- Downloaded: 2026-09-19 (sheet header "Date updated: 2026-01-01"; file last
  saved by the author 2026-08-24).
- Terms: the author makes his datasets freely available for use with
  attribution. Cite: Damodaran, A., "Historical Returns on Stocks, Bonds and
  Bills: 1928-Current", NYU Stern.

### FRED series - `data/raw/fred/*.csv`

Downloaded 2026-09-19 from https://fred.stlouisfed.org/ (format
`observation_date,<SERIES>`; missing values are `.`).

| File | Series | Original source | Coverage in snapshot |
|---|---|---|---|
| `DGS3MO.csv` | Market yield on US Treasury securities at 3-month constant maturity, daily | Board of Governors of the Federal Reserve System, H.15 | 1981-09-01 - 2026-09-17 |
| `DGS30.csv` | Same, 30-year constant maturity, daily | Board of Governors, H.15 | 1977-02-15 - 2026-09-17 |
| `T10YIE.csv` | 10-year breakeven inflation rate, daily | Federal Reserve Bank of St. Louis (from Treasury yields) | 2003-01-02 - 2026-09-18 |
| `ECBDFR.csv` | ECB deposit facility rate, daily | European Central Bank | 1999-01-01 - 2026-09-18 |
| `ECBMRRFR.csv` | ECB main refinancing operations rate (fixed), daily | European Central Bank | 1999-01-01 - 2026-09-18 |
| `CPIAUCSL.csv` | CPI-U, all items, seasonally adjusted, monthly | US Bureau of Labor Statistics | 1947-01 - 2026-08 |
| `CPIAUCNS.csv` | CPI-U, all items, not seasonally adjusted, monthly | US Bureau of Labor Statistics | 1913-01 - 2026-08 |

Terms: FRED permits redistribution of these series with attribution.
Attribution: "Source: FRED, Federal Reserve Bank of St. Louis; original
source as listed above." H.15 and BLS data are US federal government works;
ECB data may be reused with attribution to the ECB. See
https://fred.stlouisfed.org/legal/ for FRED's terms.

## Not included - downloaded by `fetch.py` into `data/cache/`

### Yahoo Finance daily series

| File | Symbol | Field | Coverage |
|---|---|---|---|
| `GSPC.csv` | `^GSPC` | close | 1927-12-30 - present |
| `SP500TR.csv` | `^SP500TR` | close | 1988-01-04 - present |
| `SPY.csv` | `SPY` | adjusted close (dividends reinvested, after the fund's expenses) | 1993-01-29 - present |

Yahoo Finance data is licensed for personal, non-commercial use and may not be
redistributed, so the raw series are not part of the repository; only
aggregated results derived from them are committed (`results/`). The results
were generated from a download taken on 2026-09-20 with the last observation
on 2026-09-18 (`DATA_END` in `scripts/common.py`); every script truncates the
series there so a later download reproduces the same tables.

The `^GSPC` series was cross-checked in the original research against J.P.
Morgan's Guide to the Markets (average intra-year decline 1980-2026 YTD:
JPM -14.2 %, this series -14.1 %; positive calendar years 35 of 46 in both).

### Not used

- LBMA gold PM fix (`prices.lbma.org.uk`): used in the original research for a
  gold cross-check, subject to LBMA redistribution restrictions, and not
  needed by any script here; the gold column in the results comes from
  Damodaran's file.
- US Treasury daily par yield curve (home.treasury.gov): used in the original
  research for the 2026-09-18 3-month yield (4.14 %); the scripts use FRED
  `DGS3MO` instead (4.12 % on 2026-09-17, last day in the snapshot).

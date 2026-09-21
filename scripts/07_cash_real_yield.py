"""07 - Real yield on cash (3-month T-bills) now vs. the past.

Outputs (results/):
  07_real_cash_by_period.csv   mean nominal 3m yield, mean CPI y/y, mean/min/max real yield per period
  07_negative_months_by_decade.csv  share of months with a negative real cash yield, by decade
  07_worst_months.csv          the ten worst months for real cash yield
  07_current.csv               latest 3m yield, latest CPI y/y, implied real yield; 2021 for contrast
  07_calendar_years.csv        cash index return vs CPI (Dec/Dec) for every calendar year
  07_rates_snapshot.csv        last available values of the other FRED series in data/raw/fred

Method: monthly mean of daily DGS3MO; CPI y/y from CPIAUCSL for the same month;
real = (1 + y) / (1 + pi) - 1. The series starts 1981-09 (start of DGS3MO), so
periods begin 1982. "Calendar-year cash return" = cash index (see common.cash_index)
last trading day of the year vs previous year.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import cash_index, load_fred, print_table, save  # noqa: E402

PERIODS = [("1982-1989", "1982-01", "1989-12"), ("1990-1999", "1990-01", "1999-12"),
           ("2000-2009", "2000-01", "2009-12"), ("2010-2019", "2010-01", "2019-12"),
           ("2009-2021", "2009-01", "2021-12"), ("2021", "2021-01", "2021-12"),
           ("2022", "2022-01", "2022-12"), ("2023-now", "2023-01", None), ("1982-now", "1982-01", None)]
DECADES = [("1982-1989", "1982-01", "1989-12"), ("1990-1999", "1990-01", "1999-12"),
           ("2000-2008", "2000-01", "2008-12"), ("2009-2021", "2009-01", "2021-12"),
           ("2010-2019", "2010-01", "2019-12"), ("2022-now", "2022-01", None),
           ("1982-2008", "1982-01", "2008-12")]
OTHER_SERIES = {"DGS30": "US 30-year Treasury yield", "T10YIE": "US 10-year breakeven inflation",
                "ECBDFR": "ECB deposit facility rate", "ECBMRRFR": "ECB main refinancing rate"}


def main(verbose=True) -> dict:
    y = load_fred("DGS3MO")
    cpi = load_fred("CPIAUCSL")
    m = pd.DataFrame({"nominal": y.resample("MS").mean() / 100})
    m["cpi_yoy"] = (cpi / cpi.shift(12) - 1).reindex(m.index)
    m["real"] = (1 + m["nominal"]) / (1 + m["cpi_yoy"]) - 1
    m = m.dropna()
    m = m[m.index >= "1982-01-01"]

    def stats(label, a, b):
        sub = m.loc[a:] if b is None else m.loc[a:b]
        return {"period": label if b is not None else f"{label.replace('now', sub.index[-1].strftime('%Y-%m'))}",
                "months": len(sub), "mean_nominal": sub["nominal"].mean(),
                "mean_cpi_yoy": sub["cpi_yoy"].mean(), "mean_real": sub["real"].mean(),
                "min_real": sub["real"].min(), "max_real": sub["real"].max(),
                "share_months_real_negative": (sub["real"] < 0).mean()}

    by_period = pd.DataFrame([stats(*p) for p in PERIODS])
    by_decade = pd.DataFrame([stats(*p) for p in DECADES])[
        ["period", "months", "share_months_real_negative", "mean_real"]]
    worst = m.nsmallest(10, "real").reset_index().rename(columns={"observation_date": "month"})
    worst["month"] = worst["month"].dt.strftime("%Y-%m")

    latest_y = y.dropna().iloc[-1] / 100
    latest_pi = m["cpi_yoy"].iloc[-1]
    aug = m.iloc[-1]
    current = pd.DataFrame([
        {"as_of": y.dropna().index[-1].strftime("%Y-%m-%d"), "basis": "latest daily 3m yield, latest CPI y/y",
         "nominal": latest_y, "cpi_yoy": latest_pi, "real": (1 + latest_y) / (1 + latest_pi) - 1},
        {"as_of": m.index[-1].strftime("%Y-%m"), "basis": "monthly average 3m yield, same-month CPI y/y",
         "nominal": aug["nominal"], "cpi_yoy": aug["cpi_yoy"], "real": aug["real"]},
        {"as_of": "2021 average", "basis": "monthly averages", **m.loc["2021"].mean().to_dict()},
        {"as_of": "2010-2019 average", "basis": "monthly averages", **m.loc["2010":"2019"].mean().to_dict()},
    ])

    cash = cash_index(y)
    ye = cash.groupby(cash.index.year).last()
    cpi_dec = cpi[cpi.index.month == 12]
    cpi_dec.index = cpi_dec.index.year
    cal = pd.DataFrame({"cash_return": ye / ye.shift(1) - 1,
                        "cpi_dec_to_dec": cpi_dec / cpi_dec.shift(1) - 1}).dropna()
    cal["real_return"] = (1 + cal["cash_return"]) / (1 + cal["cpi_dec_to_dec"]) - 1
    cal = cal.reset_index().rename(columns={"index": "year"})
    cal["year"] = cal["year"].astype(int)

    snap = [{"series": "DGS3MO", "description": "US 3-month Treasury yield",
             "date": y.dropna().index[-1], "value": y.dropna().iloc[-1]}]
    for code, desc in OTHER_SERIES.items():
        s = load_fred(code).dropna()
        snap.append({"series": code, "description": desc, "date": s.index[-1], "value": s.iloc[-1]})
    snap = pd.DataFrame(snap)

    out = {"07_real_cash_by_period": by_period, "07_negative_months_by_decade": by_decade,
           "07_worst_months": worst, "07_current": current, "07_calendar_years": cal,
           "07_rates_snapshot": snap}
    for name, df in out.items():
        save(df, name + ".csv")
    if verbose:
        print(f"DGS3MO {y.index[0]:%Y-%m-%d} -> {y.index[-1]:%Y-%m-%d}; CPIAUCSL through {cpi.index[-1]:%Y-%m}")
        print_table("Real cash yield by period", by_period, {"months": "int"})
        print_table("Share of months with negative real cash yield", by_decade, {"months": "int"})
        print_table("Worst months", worst, {"month": "str"})
        print_table("Now vs 2021", current, {"as_of": "str", "basis": "str"})
        print_table("Calendar years (recent)", cal.tail(8), {"year": "year"})
        print_table("Rates snapshot (last value in file)", snap, {"date": "date", "value": "num"})
    return out


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fit the empirical growth exponent b in  T(n) ≈ c · n^b  per method (log-log least squares).

For the naive algorithm the model predicts b ≈ 3; deviations reveal cache/memory effects or
constant overheads at small n. Uses the per-configuration MEDIAN from summarize.py output and
reports a 95% confidence interval for b (t-distribution on the slope's standard error).

Example
  python3 growth_fit.py results/summary/summary.csv --min-n 128 --by method language \\
      --out results/summary/growth_fit.csv
"""
import argparse

import numpy as np
import pandas as pd

T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
       9: 2.262, 10: 2.228, 12: 2.179, 15: 2.131, 20: 2.086, 30: 2.042}


def t95(dof):
    if dof <= 0:
        return np.nan
    keys = sorted(k for k in T95 if k <= dof)
    return T95[keys[-1]] if dof <= 30 else 1.96


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary")
    ap.add_argument("--by", nargs="+", default=["method"])
    ap.add_argument("--min-n", type=float, default=0)
    ap.add_argument("--max-n", type=float, default=np.inf)
    ap.add_argument("--out")
    args = ap.parse_args()

    s = pd.read_csv(args.summary, keep_default_na=False)
    s = s[(pd.to_numeric(s["n_ok"]) > 0)]
    s["n"] = pd.to_numeric(s["n"])
    s["median_s"] = pd.to_numeric(s["median_s"])
    s = s[(s["n"] >= args.min_n) & (s["n"] <= args.max_n)]
    rows = []
    for key, g in s.groupby(args.by):
        if len(g) < 3:
            continue
        x, y = np.log(g["n"].to_numpy()), np.log(g["median_s"].to_numpy())
        (b, a), cov = np.polyfit(x, y, 1, cov=True)
        se = float(np.sqrt(cov[0, 0]))
        half = t95(len(g) - 2) * se
        r2 = 1 - np.sum((y - (a + b * x)) ** 2) / np.sum((y - y.mean()) ** 2)
        row = dict(zip(args.by, key if isinstance(key, tuple) else (key,)))
        row.update({"points": len(g), "n_min": g["n"].min(), "n_max": g["n"].max(),
                    "exponent_b": b, "ci95_low": b - half, "ci95_high": b + half,
                    "r2": r2, "c": float(np.exp(a))})
        rows.append(row)
    res = pd.DataFrame(rows)
    print(res.to_string(index=False))
    if args.out:
        res.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Speedup S(p) = T_seq(n) / T_p(n) and efficiency E(p) = S(p) / p from RAW measurements.

T_seq and T_p are medians of the measured (non-warm-up, status=ok) repetitions. A 95% bootstrap
confidence interval of the median ratio is reported, which reflects run-to-run variability.
The resource column (--resource) is the parallel degree p: "threads" for Assignment 3,
"workers" (or "nodes") for Assignment 4.

Example (A3):
  python3 speedup.py results/raw/*.csv --baseline "method == 'seq_blocked'" \\
      --parallel "method == 'omp_blocked'" --resource threads --out results/summary/speedup.csv
"""
import argparse

import numpy as np
import pandas as pd

RNG = np.random.default_rng(12345)


def boot_ratio(a, b, reps=2000):
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan
    ra = RNG.choice(a, size=(reps, len(a)), replace=True)
    rb = RNG.choice(b, size=(reps, len(b)), replace=True)
    ratios = np.median(ra, axis=1) / np.median(rb, axis=1)
    return float(np.quantile(ratios, .025)), float(np.quantile(ratios, .975))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--baseline", required=True, help="pandas query selecting the sequential baseline rows")
    ap.add_argument("--parallel", required=True, help="pandas query selecting the parallel rows")
    ap.add_argument("--resource", default="threads")
    ap.add_argument("--out")
    args = ap.parse_args()

    df = pd.concat([pd.read_csv(p, keep_default_na=False, dtype=str) for p in args.csv], ignore_index=True)
    for c in ("n", "time_s", "is_warmup", args.resource):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[(df["is_warmup"].fillna(0) == 0) & (df["status"] == "ok")]
    base = df.query(args.baseline)
    par = df.query(args.parallel)
    if base["timer_boundary"].nunique() > 1 or par["timer_boundary"].nunique() > 1 or \
            set(base["timer_boundary"]) != set(par["timer_boundary"]):
        raise SystemExit("timer_boundary differs between/within baseline and parallel rows: refuse to mix")

    rows = []
    for n, gp in par.groupby("n"):
        tb = base.loc[base["n"] == n, "time_s"].to_numpy()
        if len(tb) == 0:
            continue
        tseq = float(np.median(tb))
        for p, g in gp.groupby(args.resource):
            tp_raw = g["time_s"].to_numpy()
            tp = float(np.median(tp_raw))
            lo, hi = boot_ratio(tb, tp_raw)
            s = tseq / tp
            rows.append({"n": int(n), args.resource: int(p), "T_seq_median_s": tseq, "T_p_median_s": tp,
                         "k_seq": len(tb), "k_p": len(tp_raw), "speedup": s, "speedup_ci95_low": lo,
                         "speedup_ci95_high": hi, "efficiency": s / p})
    res = pd.DataFrame(rows).sort_values(["n", args.resource])
    print(res.to_string(index=False))
    if args.out:
        res.to_csv(args.out, index=False)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Summarise raw benchmark CSVs (schema of run_measured.py) into per-configuration statistics.

Warm-up rows are excluded; failed rows (status != ok) are counted, never given a time.

Outputs
  --out      summary CSV: one row per configuration with n_ok, median, q1, q3, iqr, min, max,
             mean, std of time_s, peak RSS stats, memory_bytes median and failure counts.
  --limits   optional CSV: largest n that completed (all measured reps ok) and smallest n that
             failed, per method configuration.
  --latex    optional LaTeX table (booktabs) of the main columns, for \\input{} in the report.

Example
  python3 summarize.py results/raw/*.csv --out results/summary/summary.csv \\
      --limits results/summary/limits.csv --latex report/generated/table_summary.tex
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CONFIG_COLS = ["experiment", "method", "language", "n", "dtype", "density", "representation",
               "threads", "workers", "nodes", "timer_boundary"]


def load(paths):
    frames = [pd.read_csv(p, dtype=str, keep_default_na=False) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    for col in ("n", "time_s", "process_wall_s", "peak_rss_kib", "memory_bytes", "is_warmup"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_warmup"] = df["is_warmup"].fillna(0).astype(int)
    for col in ("threads", "workers", "nodes"):
        if col in df:
            df[col] = pd.to_numeric(df[col].replace("", np.nan), errors="coerce").astype("Int64")
    if "density" in df:
        dens = pd.to_numeric(df["density"].replace("", np.nan), errors="coerce")
        if dens.notna().sum() == (df["density"] != "").sum():
            df["density"] = dens
    # failed runs print no JSON, so they carry no timer_boundary: inherit it from the ok rows
    # of the same configuration so that failures stay in the same group as the successes
    if "timer_boundary" in df:
        keys = [c for c in CONFIG_COLS if c in df and c not in ("n", "timer_boundary")]
        def key_of(row):
            return tuple("" if pd.isna(v) else str(v) for v in row)

        ok = df[(df["status"] == "ok") & (df["timer_boundary"] != "")]
        mode = {}
        for _, row in ok.iterrows():
            mode.setdefault(key_of(row[keys]), row["timer_boundary"])
        missing = (df["status"] != "ok") & (df["timer_boundary"] == "")
        for idx in df.index[missing]:
            key = key_of(df.loc[idx, keys])
            if key in mode:
                df.loc[idx, "timer_boundary"] = mode[key]
    return df


def cell(v):
    return "" if pd.isna(v) else str(v)


def q(x, p):
    return float(np.quantile(x, p)) if len(x) else np.nan


def summarise(df, group_cols):
    measured = df[df["is_warmup"] == 0]
    out = []
    for key, g in measured.groupby(group_cols, dropna=False, sort=True):
        ok = g[g["status"] == "ok"]
        t = ok["time_s"].dropna().to_numpy()
        rss = ok["peak_rss_kib"].dropna().to_numpy()
        mem = ok["memory_bytes"].dropna().to_numpy() if "memory_bytes" in ok else np.array([])
        row = dict(zip(group_cols, key if isinstance(key, tuple) else (key,)))
        row.update({
            "n_ok": len(t), "n_failed": int((g["status"] != "ok").sum()),
            "failed_statuses": ";".join(sorted(set(g.loc[g["status"] != "ok", "status"]))),
            "median_s": q(t, .5), "q1_s": q(t, .25), "q3_s": q(t, .75),
            "iqr_s": q(t, .75) - q(t, .25) if len(t) else np.nan,
            "min_s": t.min() if len(t) else np.nan, "max_s": t.max() if len(t) else np.nan,
            "mean_s": t.mean() if len(t) else np.nan,
            "std_s": t.std(ddof=1) if len(t) > 1 else np.nan,
            "median_peak_rss_mib": q(rss, .5) / 1024 if len(rss) else np.nan,
            "max_peak_rss_mib": rss.max() / 1024 if len(rss) else np.nan,
            "memory_metric": ";".join(sorted(set(ok["memory_metric"]) - {""})) if "memory_metric" in ok else "",
            "median_memory_mib": q(mem, .5) / 2**20 if len(mem) else np.nan,
        })
        out.append(row)
    return pd.DataFrame(out)


def limits(summary, group_cols):
    method_cols = [c for c in group_cols if c != "n"]
    rows = []
    for key, g in summary.groupby(method_cols, dropna=False):
        done = g[(g["n_ok"] > 0) & (g["n_failed"] == 0)]
        failed = g[g["n_failed"] > 0]
        row = dict(zip(method_cols, key if isinstance(key, tuple) else (key,)))
        row["largest_completed_n"] = done["n"].max() if len(done) else np.nan
        row["smallest_failed_n"] = failed["n"].min() if len(failed) else np.nan
        row["failure_type"] = ";".join(sorted(set(";".join(failed["failed_statuses"]).split(";")) - {""}))
        rows.append(row)
    return pd.DataFrame(rows)


def fmt_time(x):
    if pd.isna(x):
        return "--"
    if x >= 100:
        return f"{x:.0f}\\,s"
    if x >= 1:
        return f"{x:.2f}\\,s"
    if x >= 1e-3:
        return f"{x * 1e3:.2f}\\,ms"
    return f"{x * 1e6:.1f}\\,\\textmu s"


def to_latex(summary, path, caption, label):
    cols = [c for c in ("method", "language", "threads", "workers", "density", "n") if c in summary
            and summary[c].map(cell).str.len().gt(0).any()]
    lines = [r"\begin{table}[t]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             r"\small", r"\begin{tabular}{" + "l" * len(cols) + "rrrr}", r"\toprule",
             " & ".join(c.replace("_", " ").capitalize() for c in cols)
             + r" & Median & IQR & $k$ & Peak RSS [MiB] \\", r"\midrule"]
    for _, r in summary.iterrows():
        cells = [cell(r[c]).replace("_", r"\_") for c in cols]
        if r["n_ok"] == 0:
            cells += [r"\multicolumn{3}{c}{" + (r["failed_statuses"] or "no data") + "}", "--"]
        else:
            cells += [fmt_time(r["median_s"]), fmt_time(r["iqr_s"]), str(int(r["n_ok"])),
                      "--" if pd.isna(r["median_peak_rss_mib"]) else f"{r['median_peak_rss_mib']:.1f}"]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limits")
    ap.add_argument("--latex")
    ap.add_argument("--caption", default="Runtime summary: median and interquartile range (IQR) over $k$ measured repetitions; peak RSS is the median process peak resident set size.")
    ap.add_argument("--label", default="tab:summary")
    ap.add_argument("--query", help="pandas query applied to the summary before writing LaTeX, e.g. \"n >= 256\"")
    args = ap.parse_args()

    df = load(args.csv)
    group_cols = [c for c in CONFIG_COLS if c in df]
    summary = summarise(df, group_cols)
    summary = summary.sort_values([c for c in ("experiment", "method", "threads", "workers", "density", "n")
                                   if c in summary])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out, index=False)
    print(f"summary: {len(summary)} configurations -> {args.out}")
    if args.limits:
        limits(summary, group_cols).to_csv(args.limits, index=False)
        print(f"limits -> {args.limits}")
    if args.latex:
        tab = summary.query(args.query) if args.query else summary
        to_latex(tab, args.latex, args.caption, args.label)
        print(f"latex -> {args.latex}")


if __name__ == "__main__":
    main()

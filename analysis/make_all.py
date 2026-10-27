#!/usr/bin/env python3
"""Regenerate every summary, table, figure and LaTeX macro of the Assignment 2 report from results/raw.

Usage:  python analysis/make_all.py [--prefix pilot_]
Inputs : results/raw/{block_sweep,dense_size_sweep,sparse_density,sparse_scaling,sparse_scaling_xl}.csv
Outputs: results/summary/*.csv, report/figures/*.pdf|png, report/generated/*.tex

Rules applied (stated in the report):
- warm-up rows (is_warmup = 1) are excluded; rows with status != ok carry no time and are reported as failures;
- no other exclusions;
- statistic: median and IQR (25th-75th percentile, numpy linear interpolation) over the k measured repetitions;
- speedup = median(T_baseline) / median(T_method) at the same n; 95 % CI by bootstrap of both samples.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from plot_style import new_figure, savefig  # noqa: E402
from summarize import load, summarise, limits  # noqa: E402

RAW, SUM = ROOT / "results" / "raw", ROOT / "results" / "summary"
FIG, GEN = ROOT / "report" / "figures", ROOT / "report" / "generated"
RNG = np.random.default_rng(12345)

# fixed colour per entity (Okabe-Ito); markers/line styles give a second, non-colour encoding
STYLE = {
    "naive_ijk": ("#D55E00", "o", "-"), "reorder_ikj": ("#E69F00", "s", "-"),
    "blocked_ikj": ("#0072B2", "^", "-"), "dense": ("#0072B2", "^", "-"),
    "csr": ("#009E73", "o", "-"), "csr_e2e": ("#CC79A7", "D", "-"),
}
PATTERN_LS = {"uniform": "-", "banded": "--"}
PATTERN_MK = {"uniform": "o", "banded": "s"}
LABEL = {"naive_ijk": "naive ijk (baseline)", "reorder_ikj": "reordered ikj", "blocked_ikj": "blocked ikj"}
MACROS = {}


def macro(name, value):
    MACROS[name] = value


def fmt(x, sig=3):
    """Format with `sig` significant digits, no scientific notation for the usual ranges."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "--"
    if x == 0:
        return "0"
    digits = max(sig - int(np.floor(np.log10(abs(x)))) - 1, 0)
    return f"{x:.{digits}f}"


def fmt_t(x):
    """Time with a unit chosen for readability."""
    if not np.isfinite(x):
        return "--"
    if x >= 1:
        return f"{fmt(x)}\\,s"
    if x >= 1e-3:
        return f"{fmt(x * 1e3)}\\,ms"
    return f"{fmt(x * 1e6)}\\,\\textmu s"


def extra(df, key):
    return df["extra_json"].map(lambda s: json.loads(s).get(key) if isinstance(s, str) and s else np.nan)


def ok_rows(df):
    return df[(df["is_warmup"] == 0) & (df["status"] == "ok")].copy()


def boot_ratio(a, b, reps=4000):
    """95 % bootstrap CI of median(a) / median(b)."""
    a, b = np.asarray(a), np.asarray(b)
    ra = RNG.choice(a, size=(reps, len(a)), replace=True)
    rb = RNG.choice(b, size=(reps, len(b)), replace=True)
    r = np.median(ra, axis=1) / np.median(rb, axis=1)
    return float(np.quantile(r, .025)), float(np.quantile(r, .975))


def stats(t):
    t = np.asarray(t, dtype=float)
    return {"median": float(np.median(t)), "q1": float(np.quantile(t, .25)),
            "q3": float(np.quantile(t, .75)), "k": len(t)}


def errbar(ax, x, s, label, color, marker, ls="-"):
    med = np.array([v["median"] for v in s])
    lo = med - np.array([v["q1"] for v in s])
    hi = np.array([v["q3"] for v in s]) - med
    ax.errorbar(x, med, yerr=[lo, hi], label=label, color=color, marker=marker, linestyle=ls,
                markersize=4, linewidth=1.2, capsize=2)


def write_table(path, header, rows, caption, label, colspec, wide=False, size="\\footnotesize", notes=None):
    env = "table*" if wide else "table"
    lines = [f"\\begin{{{env}}}[t]", "\\centering", f"\\caption{{{caption}}}", f"\\label{{{label}}}", size,
             "\\setlength{\\tabcolsep}{3.5pt}", f"\\begin{{tabular}}{{{colspec}}}", "\\toprule",
             " & ".join(header) + " \\\\", "\\midrule"]
    for r in rows:
        lines.append(r if isinstance(r, str) else " & ".join(r) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    if notes:
        lines.append(f"\\\\[2pt]\\parbox{{\\linewidth}}{{\\scriptsize {notes}}}")
    lines.append(f"\\end{{{env}}}")
    (GEN / path).write_text("\n".join(lines) + "\n")


# ====================================================================== Part A
def part_a(prefix):
    bsw = load([RAW / f"{prefix}block_sweep.csv"])
    bsw = ok_rows(bsw)
    bsw["bs"] = extra(bsw, "block_size").astype(int)
    fig, ax = new_figure(height=2.1)
    bs_rows = []
    best = {}
    for i, (n, g) in enumerate(bsw.groupby("n")):
        xs = sorted(g["bs"].unique())
        s = [stats(2 * n ** 3 / g[g["bs"] == b]["time_s"] / 1e9) for b in xs]
        meds = {b: stats(g[g["bs"] == b]["time_s"]) for b in xs}
        best[n] = min(meds, key=lambda b: meds[b]["median"])
        errbar(ax, xs, s, f"$n={n}$", ["#0072B2", "#D55E00"][i % 2], ["^", "o"][i % 2], ["-", "--"][i % 2])
        for b in xs:
            m = meds[b]
            bs_rows.append((n, b, m))
    ax.set_xscale("log", base=2)
    ax.set_xticks(sorted(bsw["bs"].unique()))
    ax.set_xticklabels([str(b) for b in sorted(bsw["bs"].unique())])
    ax.set_xlabel("Block size $b$")
    ax.set_ylabel("GFLOP/s ($2n^3/T$)")
    ax.legend(loc="lower center")
    savefig(fig, FIG / "block_sweep")
    tuning_n = max(best)
    bs_star = best[tuning_n]
    macro("BestBs", str(bs_star))
    macro("BsTuningN", str(tuning_n))
    for n in best:
        macro(f"BestBsAt{n}", str(best[n]))
        meds = {b: m["median"] for (nn, b, m) in bs_rows if nn == n}
        spread = (max(meds.values()) - min(meds.values())) / min(meds.values()) * 100
        macro(f"BsSpreadPct{n}", fmt(spread, 2))
        macro(f"BsBestT{n}", fmt_t(meds[best[n]]))
        macro(f"BsWorst{n}", str(max(meds, key=meds.get)))
    # block-sweep table: columns per n
    ns = sorted(best)
    bss = sorted(bsw["bs"].unique())
    rows = []
    for b in bss:
        cells = [str(b)]
        for n in ns:
            m = [mm for (nn, bb, mm) in bs_rows if nn == n and bb == b][0]
            star = "$^\\ast$" if b == best[n] else ""
            cells.append(f"{fmt_t(m['median'])}{star} [{fmt_t(m['q3'] - m['q1'])}]")
        rows.append(cells)
    write_table("table_blocks.tex", ["$b$"] + [f"$n={n}$: median [IQR]" for n in ns], rows,
                f"Block-size study for blocked ikj: median kernel time [IQR] over $k=5$ repetitions "
                f"(1 warm-up excluded). $^\\ast$ = fastest; the rule selects the fastest $b$ at $n={tuning_n}$.",
                "tab:blocks", "@{}r" + "r" * len(ns) + "@{}")

    # ---- size sweep
    raw = load([RAW / f"{prefix}dense_size_sweep.csv"])
    measured = raw[raw["is_warmup"] == 0]
    okd = ok_rows(raw)
    summ = summarise(raw, ["method", "n", "timer_boundary"])
    summ.to_csv(SUM / "dense_size_sweep_summary.csv", index=False)
    methods = ["naive_ijk", "reorder_ikj", "blocked_ikj"]
    fig, ax = new_figure(height=2.3)
    fig2, ax2 = new_figure(height=2.1)
    S = {}
    for m in methods:
        g = okd[okd["method"] == m]
        ns_m = sorted(g["n"].unique())
        S[m] = {n: g[g["n"] == n]["time_s"].to_numpy() for n in ns_m}
        c, mk, ls = STYLE[m]
        errbar(ax, ns_m, [stats(S[m][n]) for n in ns_m], LABEL[m], c, mk, ls)
        errbar(ax2, ns_m, [stats(2 * n ** 3 / S[m][n] / 1e9) for n in ns_m], LABEL[m], c, mk, ls)
    ref_n = np.array(sorted(okd["n"].unique()), dtype=float)
    t0 = np.median(S["blocked_ikj"][int(ref_n[0])])
    ax.plot(ref_n, t0 * (ref_n / ref_n[0]) ** 3, color="0.6", linestyle=":", linewidth=1, label="$\\propto n^3$")
    for a in (ax,):
        a.set_xscale("log", base=2)
        a.set_yscale("log")
    for a in (ax, ax2):
        a.set_xscale("log", base=2)
        a.set_xticks(ref_n)
        a.set_xticklabels([str(int(v)) for v in ref_n], rotation=0)
        a.set_xlabel("Matrix size $n$")
    ax.set_ylabel("Median kernel time [s]")
    ax2.set_ylabel("GFLOP/s ($2n^3/T$)")
    ax2.set_ylim(bottom=0)
    ax.legend()
    ax2.legend(loc="center right")
    savefig(fig, FIG / "dense_runtime")
    savefig(fig2, FIG / "dense_gflops")

    # speedup over naive with bootstrap CI
    fig, ax = new_figure(height=2.1)
    sp_rows = []
    for m in ("reorder_ikj", "blocked_ikj"):
        common = sorted(set(S[m]) & set(S["naive_ijk"]))
        sp = [np.median(S["naive_ijk"][n]) / np.median(S[m][n]) for n in common]
        ci = [boot_ratio(S["naive_ijk"][n], S[m][n]) for n in common]
        c, mk, ls = STYLE[m]
        ax.errorbar(common, sp, yerr=[[s - lo for s, (lo, hi) in zip(sp, ci)], [hi - s for s, (lo, hi) in zip(sp, ci)]],
                    color=c, marker=mk, linestyle=ls, label=LABEL[m], capsize=2, markersize=4)
        for n, s, (lo, hi) in zip(common, sp, ci):
            sp_rows.append({"method": m, "n": n, "speedup": s, "ci_lo": lo, "ci_hi": hi})
    # blocked vs ikj ratio
    for n in sorted(set(S["reorder_ikj"]) & set(S["blocked_ikj"])):
        r = np.median(S["reorder_ikj"][n]) / np.median(S["blocked_ikj"][n])
        lo, hi = boot_ratio(S["reorder_ikj"][n], S["blocked_ikj"][n])
        sp_rows.append({"method": "blocked_vs_ikj", "n": n, "speedup": r, "ci_lo": lo, "ci_hi": hi})
    ax.axhline(1, color="0.5", linewidth=0.8)
    ax.set_xscale("log", base=2)
    ax.set_xticks(ref_n)
    ax.set_xticklabels([str(int(v)) for v in ref_n])
    ax.set_xlabel("Matrix size $n$")
    ax.set_ylabel("Speedup over naive ijk")
    ax.set_ylim(bottom=0)
    ax.legend()
    savefig(fig, FIG / "dense_speedup")
    spd = pd.DataFrame(sp_rows)
    spd.to_csv(SUM / "dense_speedup.csv", index=False)

    # limits per method (largest completed n, failures)
    lim = []
    attempted = measured.groupby("method")["n"].max()
    for m in methods:
        g = measured[measured["method"] == m]
        fails = g[g["status"] != "ok"]
        okn = sorted(set(g[g["status"] == "ok"]["n"]) - set(fails["n"]))
        lim.append({"method": m, "largest_completed_n": max(okn) if okn else np.nan,
                    "largest_attempted_n": int(attempted[m]),
                    "failure": ";".join(f"{r.status} at n={int(r.n)}" for r in fails.itertuples()) or "none"})
    lim = pd.DataFrame(lim)
    lim.to_csv(SUM / "dense_limits.csv", index=False)

    # main dense table
    rows = []
    all_n = sorted(measured["n"].unique())
    for n in all_n:
        cells = [str(int(n))]
        for m in methods:
            g = measured[(measured["method"] == m) & (measured["n"] == n)]
            if len(g) == 0:
                cells += ["\\multicolumn{2}{c}{not attempted}"]
                continue
            if (g["status"] != "ok").any():
                st = g[g["status"] != "ok"]["status"].iloc[0]
                cells += [f"\\multicolumn{{2}}{{c}}{{{st} ($>${cfg_timeout()}\\,s)}}"]
                continue
            s = stats(S[m][n])
            cells += [f"{fmt_t(s['median'])} [{fmt_t(s['q3'] - s['q1'])}]",
                      fmt(2 * n ** 3 / s["median"] / 1e9)]
        k = okd[okd["n"] == n].groupby("method").size()
        cells.append(str(int(k.min())) if len(k) else "--")
        rss = okd[(okd["n"] == n)]["peak_rss_kib"].median() / 1024
        cells.append(fmt(rss))
        rows.append(cells)
    write_table("table_dense.tex",
                ["$n$", "naive: median [IQR]", "GF/s", "ikj: median [IQR]", "GF/s", "blocked: median [IQR]", "GF/s",
                 "$k$", "RSS"],
                rows,
                f"Part A: kernel time, median [IQR] over $k$ measured repetitions, and GFLOP/s $=2n^3/T_{{med}}$. "
                f"Blocked ikj uses $b=\\BestBs$. RSS = median peak resident set size [MiB] of the process "
                f"(GNU time), all methods. $n\\le 2048$: 1 warm-up + $k=5$; $n\\ge 3072$: no warm-up, $k=3$.",
                "tab:dense", "@{}r rr rr rr rr@{}", wide=True)

    # macros
    for m, short in (("naive_ijk", "Naive"), ("reorder_ikj", "Ikj"), ("blocked_ikj", "Blk")):
        for n in S[m]:
            s = stats(S[m][n])
            nm = num_word(n)
            macro(f"T{short}{nm}", fmt_t(s["median"]))
            macro(f"IQR{short}{nm}", fmt_t(s["q3"] - s["q1"]))
            macro(f"GF{short}{nm}", fmt(2 * n ** 3 / s["median"] / 1e9))
        r = lim[lim["method"] == m].iloc[0]
        macro(f"MaxN{short}", str(int(r["largest_completed_n"])))
        macro(f"AttN{short}", str(int(r["largest_attempted_n"])))
        macro(f"Fail{short}", r["failure"])
    for r in sp_rows:
        short = {"reorder_ikj": "Ikj", "blocked_ikj": "Blk", "blocked_vs_ikj": "BlkVsIkj"}[r["method"]]
        nm = num_word(r["n"])
        macro(f"Sp{short}{nm}", fmt(r["speedup"]))
        macro(f"SpLo{short}{nm}", fmt(r["ci_lo"]))
        macro(f"SpHi{short}{nm}", fmt(r["ci_hi"]))
    for m, short in (("reorder_ikj", "Ikj"), ("blocked_ikj", "Blk")):
        sub = spd[spd["method"] == m]
        macro(f"SpMax{short}", fmt(sub["speedup"].max()))
        macro(f"SpMaxN{short}", str(int(sub.loc[sub["speedup"].idxmax(), "n"])))
        macro(f"SpMin{short}", fmt(sub["speedup"].min()))
    gf = {m: [2 * n ** 3 / np.median(S[m][n]) / 1e9 for n in S[m]] for m in methods}
    for m, short in (("naive_ijk", "Naive"), ("reorder_ikj", "Ikj"), ("blocked_ikj", "Blk")):
        macro(f"GFMax{short}", fmt(max(gf[m])))
        macro(f"GFMin{short}", fmt(min(gf[m])))
    # growth exponent of each method over n >= 512 (log-log least squares on medians)
    for m, short in (("naive_ijk", "Naive"), ("reorder_ikj", "Ikj"), ("blocked_ikj", "Blk")):
        ns_fit = [n for n in S[m] if n >= 512]
        b = np.polyfit(np.log(ns_fit), np.log([np.median(S[m][n]) for n in ns_fit]), 1)[0]
        macro(f"Exp{short}", fmt(b))
    rel = okd.groupby(["method", "n"])["time_s"].agg(lambda t: (np.quantile(t, .75) - np.quantile(t, .25)) / np.median(t))
    macro("MaxRelIQRDense", fmt(rel.max() * 100, 2))
    macro("MedRelIQRDense", fmt(rel.median() * 100, 2))
    macro("NDenseRows", str(len(okd)))
    return bs_star, S


def num_word(n):
    """LaTeX macro names cannot contain digits: 2048 -> 'TwoZeroFourEight'."""
    words = "Zero One Two Three Four Five Six Seven Eight Nine".split()
    return "".join(words[int(c)] for c in str(int(n)))


_TIMEOUT = [600]


def cfg_timeout():
    return _TIMEOUT[0]


# ====================================================================== Part B
def part_b(prefix, S_dense):
    raw = load([RAW / f"{prefix}sparse_density.csv"])
    okd = ok_rows(raw)
    okd["pattern"] = okd["representation"].str.split(":").str[1]
    for key in ("nnz_a", "nnz_b", "nnz_c", "flops_madd", "nnz_c_numeric"):
        okd[key] = extra(okd, key)
    n = int(okd["n"].iloc[0])
    macro("SpN", str(n))
    densities = sorted(okd["density"].unique())
    rows, recs = [], []
    for pat in ("uniform", "banded"):
        for d in densities:
            g = okd[(okd["pattern"] == pat) & (okd["density"] == d)]
            sp_t = g[g["timer_boundary"] == "spgemm_kernel"]
            de_t = g[g["timer_boundary"] == "dense_kernel"]
            c1 = g[g["timer_boundary"] == "convert_dense_to_csr"]
            c2 = g[g["timer_boundary"] == "convert_csr_to_dense"]
            if len(sp_t) == 0 or len(de_t) == 0:
                continue
            s_sp, s_de = stats(sp_t["time_s"]), stats(de_t["time_s"])
            s_c1, s_c2 = stats(c1["time_s"]), stats(c2["time_s"])
            lo, hi = boot_ratio(de_t["time_s"], sp_t["time_s"])
            e2e = s_c1["median"] + s_sp["median"] + s_c2["median"]
            rss_sp = sp_t["peak_rss_kib"].median() / 1024
            rss_de = de_t["peak_rss_kib"].median() / 1024
            recs.append({
                "pattern": pat, "density": d, "nnz_a": int(sp_t["nnz_a"].iloc[0]), "nnz_b": int(sp_t["nnz_b"].iloc[0]),
                "nnz_c": int(sp_t["nnz_c"].iloc[0]), "nnz_c_dense_numeric": int(de_t["nnz_c_numeric"].iloc[0]),
                "flops_madd": int(sp_t["flops_madd"].iloc[0]),
                "t_spgemm_med": s_sp["median"], "t_spgemm_iqr": s_sp["q3"] - s_sp["q1"], "k_sp": s_sp["k"],
                "t_dense_med": s_de["median"], "t_dense_iqr": s_de["q3"] - s_de["q1"], "k_de": s_de["k"],
                "t_d2csr_med": s_c1["median"], "t_csr2d_med": s_c2["median"],
                "t_e2e_med": e2e, "speedup_dense_over_sparse": s_de["median"] / s_sp["median"],
                "ci_lo": lo, "ci_hi": hi, "speedup_incl_conversion": s_de["median"] / e2e,
                "rss_spgemm_mib": rss_sp, "rss_dense_mib": rss_de,
                "mem_est_spgemm_mib": sp_t["memory_bytes"].median() / 2 ** 20,
                "mem_est_dense_mib": de_t["memory_bytes"].median() / 2 ** 20,
                "ns_per_madd": s_sp["median"] / max(int(sp_t["flops_madd"].iloc[0]), 1) * 1e9,
                "q1_sp": s_sp["q1"], "q3_sp": s_sp["q3"], "q1_de": s_de["q1"], "q3_de": s_de["q3"],
            })
    R = pd.DataFrame(recs)
    R.to_csv(SUM / "sparse_density_summary.csv", index=False)

    # --- crossover per pattern (first tested density where median SpGEMM >= median dense)
    for pat in ("uniform", "banded"):
        Rp = R[R["pattern"] == pat].sort_values("density")
        P = pat.capitalize()
        for col, tag in (("speedup_dense_over_sparse", "Kernel"), ("speedup_incl_conversion", "Eetoe")):
            slower = Rp[Rp[col] < 1]
            if len(slower):
                d_hi = slower["density"].iloc[0]
                faster = Rp[(Rp["density"] < d_hi) & (Rp[col] >= 1)]
                d_lo = faster["density"].iloc[-1] if len(faster) else np.nan
                # log-linear interpolation of log(speedup) vs density between the bracketing levels
                if np.isfinite(d_lo):
                    s_lo = Rp[Rp["density"] == d_lo][col].iloc[0]
                    s_hi = Rp[Rp["density"] == d_hi][col].iloc[0]
                    f = np.log(s_lo) / (np.log(s_lo) - np.log(s_hi))
                    d_x = d_lo + f * (d_hi - d_lo)
                else:
                    d_x = np.nan
                macro(f"Cross{tag}Lo{P}", fmt(d_lo * 100, 3) if np.isfinite(d_lo) else "--")
                macro(f"Cross{tag}Hi{P}", fmt(d_hi * 100, 3))
                macro(f"Cross{tag}Interp{P}", fmt(d_x * 100, 2) if np.isfinite(d_x) else "--")
            else:
                macro(f"Cross{tag}Lo{P}", fmt(Rp["density"].max() * 100, 3))
                macro(f"Cross{tag}Hi{P}", "none")
                macro(f"Cross{tag}Interp{P}", "none")
        for _, r in Rp.iterrows():
            dw = density_word(r["density"])
            macro(f"SpT{P}{dw}", fmt_t(r["t_spgemm_med"]))
            macro(f"SpIQR{P}{dw}", fmt_t(r["t_spgemm_iqr"]))
            macro(f"DeT{P}{dw}", fmt_t(r["t_dense_med"]))
            macro(f"DeIQR{P}{dw}", fmt_t(r["t_dense_iqr"]))
            macro(f"Ratio{P}{dw}", fmt(r["speedup_dense_over_sparse"]))
            macro(f"RatioLo{P}{dw}", fmt(r["ci_lo"]))
            macro(f"RatioHi{P}{dw}", fmt(r["ci_hi"]))
            macro(f"RatioEe{P}{dw}", fmt(r["speedup_incl_conversion"]))
            macro(f"NnzC{P}{dw}", f"{int(r['nnz_c']):,}".replace(",", "\\,"))
            macro(f"OutDens{P}{dw}", fmt(r["nnz_c"] / n ** 2 * 100, 3))
            macro(f"NsMadd{P}{dw}", fmt(r["ns_per_madd"], 2))
            macro(f"RssSp{P}{dw}", fmt(r["rss_spgemm_mib"]))
            macro(f"ConvA{P}{dw}", fmt_t(r["t_d2csr_med"]))
            macro(f"ConvB{P}{dw}", fmt_t(r["t_csr2d_med"]))
            macro(f"ConvShare{P}{dw}", fmt((r["t_d2csr_med"] + r["t_csr2d_med"]) / r["t_e2e_med"] * 100, 2))
            macro(f"Flops{P}{dw}", f"{r['flops_madd']:.3g}".replace("e+0", "e").replace("e+", "e"))
    macro("DenseRssMiB", fmt(R["rss_dense_mib"].median()))
    macro("DenseTMin", fmt_t(R["t_dense_med"].min()))
    macro("DenseTMax", fmt_t(R["t_dense_med"].max()))
    # SpGEMM cost per multiply-add: range and uniform/banded contrast at equal flops
    macro("NsMaddMin", fmt(R["ns_per_madd"].min(), 2))
    macro("NsMaddMax", fmt(R["ns_per_madd"].max(), 2))

    # --- figure: time vs density
    fig, ax = new_figure(height=2.5)
    for pat in ("uniform", "banded"):
        Rp = R[R["pattern"] == pat].sort_values("density")
        x = Rp["density"] * 100
        ls, mk = PATTERN_LS[pat], PATTERN_MK[pat]
        for kind, col, q1, q3, lab in (("csr", "t_spgemm_med", "q1_sp", "q3_sp", "CSR SpGEMM"),
                                       ("dense", "t_dense_med", "q1_de", "q3_de", f"dense blocked ($b$={int(cfg_bs[0])})")):
            c = STYLE[kind][0]
            ax.errorbar(x, Rp[col], yerr=[Rp[col] - Rp[q1], Rp[q3] - Rp[col]], color=c, linestyle=ls,
                        marker=mk, markersize=3.5, capsize=2, label=f"{lab}, {pat}")
        ax.plot(x, Rp["t_e2e_med"], color=STYLE["csr_e2e"][0], linestyle=ls, marker="D", markersize=3,
                label=f"CSR incl. conversions, {pat}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Input density $d$ [% nonzeros]")
    ax.set_ylabel("Median time [s]")
    ax.legend(fontsize=5.5, ncol=1, loc="lower right")
    savefig(fig, FIG / "sparse_time_vs_density")

    # --- figure: output density vs input density with uniform-random expectation
    fig, ax = new_figure(height=2.1)
    dd = np.logspace(np.log10(min(densities)), 0, 200)
    ax.plot(dd * 100, (1 - (1 - dd ** 2) ** n) * 100, color="0.55", linestyle=":", linewidth=1,
            label="uniform model $1-(1-d^2)^n$")
    for pat in ("uniform", "banded"):
        Rp = R[R["pattern"] == pat].sort_values("density")
        ax.plot(Rp["density"] * 100, Rp["nnz_c"] / n ** 2 * 100, color=STYLE["csr"][0] if pat == "uniform" else "#E69F00",
                linestyle=PATTERN_LS[pat], marker=PATTERN_MK[pat], markersize=3.5, label=f"measured nnz(C), {pat}")
    ax.plot(dd * 100, dd * 100, color="0.3", linewidth=0.7, linestyle="-", label="output = input density")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Input density $d$ [%]")
    ax.set_ylabel("Output density nnz(C)/$n^2$ [%]")
    ax.legend(fontsize=6)
    savefig(fig, FIG / "sparse_fill_in")

    # --- figure: memory vs density (peak RSS, one metric per axis)
    fig, ax = new_figure(height=2.1)
    for pat in ("uniform", "banded"):
        Rp = R[R["pattern"] == pat].sort_values("density")
        ax.plot(Rp["density"] * 100, Rp["rss_spgemm_mib"], color=STYLE["csr"][0], linestyle=PATTERN_LS[pat],
                marker=PATTERN_MK[pat], markersize=3.5, label=f"CSR SpGEMM process, {pat}")
        ax.plot(Rp["density"] * 100, Rp["rss_dense_mib"], color=STYLE["dense"][0], linestyle=PATTERN_LS[pat],
                marker="^", markersize=3.5, label=f"dense process, {pat}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Input density $d$ [%]")
    ax.set_ylabel("Peak RSS [MiB] (GNU time)")
    ax.legend(fontsize=6)
    savefig(fig, FIG / "sparse_memory")

    # --- table (both patterns)
    trows = []
    for pat in ("uniform", "banded"):
        trows.append(f"\\multicolumn{{10}}{{@{{}}l}}{{\\textit{{{pat} pattern}}}} \\\\")
        for _, r in R[R["pattern"] == pat].sort_values("density").iterrows():
            trows.append([fmt(r["density"] * 100, 2), f"{int(r['nnz_a']):,}".replace(",", "\\,"),
                          f"{int(r['nnz_c']):,}".replace(",", "\\,"),
                          f"{fmt_t(r['t_spgemm_med'])} [{fmt_t(r['t_spgemm_iqr'])}]",
                          f"{fmt_t(r['t_dense_med'])} [{fmt_t(r['t_dense_iqr'])}]",
                          f"{fmt(r['speedup_dense_over_sparse'])}",
                          fmt_t(r["t_d2csr_med"]), fmt_t(r["t_csr2d_med"]),
                          fmt(r["speedup_incl_conversion"]),
                          f"{fmt(r['rss_spgemm_mib'])} / {fmt(r['rss_dense_mib'])}"])
    write_table("table_sparse.tex",
                ["$d$ [\\%]", "nnz(A)", "nnz(C)", "SpGEMM [IQR]", "dense [IQR]", "$T_D/T_S$",
                 "dense$\\to$CSR", "CSR$\\to$dense", "$T_D/T_S^{conv}$", "RSS S/D [MiB]"], trows,
                f"Part B at $n={n}$: median time [IQR] over $k=5$ repetitions (1 warm-up excluded) of CSR SpGEMM and "
                f"of the dense blocked kernel on the same logical inputs; nnz(B) $=$ nnz(A). $T_D/T_S$: dense median over "
                f"SpGEMM median ($>1$: sparse faster). Conversions (medians) are measured separately; dense$\\to$CSR "
                f"converts both inputs. $T_S^{{conv}}$ = dense$\\to$CSR + SpGEMM + CSR$\\to$dense. RSS: median peak "
                f"resident set of the SpGEMM process / of the dense process.",
                "tab:sparse", "@{}r rr rr r rr r r@{}", wide=True)

    # banded vs uniform at equal density: time ratio and flops ratio
    for d in densities:
        u = R[(R["pattern"] == "uniform") & (R["density"] == d)]
        b = R[(R["pattern"] == "banded") & (R["density"] == d)]
        if len(u) and len(b):
            dw = density_word(d)
            macro(f"UoverB{dw}", fmt(u["t_spgemm_med"].iloc[0] / b["t_spgemm_med"].iloc[0]))
            macro(f"FlopsUoverB{dw}", fmt(u["flops_madd"].iloc[0] / b["flops_madd"].iloc[0]))
            macro(f"NnzCUoverB{dw}", fmt(u["nnz_c"].iloc[0] / b["nnz_c"].iloc[0]))
    relsp = okd.groupby(["representation", "density", "timer_boundary"])["time_s"].agg(
        lambda t: (np.quantile(t, .75) - np.quantile(t, .25)) / np.median(t))
    macro("MaxRelIQRSparse", fmt(relsp.max() * 100, 2))
    macro("MedRelIQRSparse", fmt(relsp.median() * 100, 2))
    return R


def density_word(d):
    """0.001 -> 'Dpointone' style names without digits: per-mille based mapping."""
    table = {0.001: "Dzeroone", 0.005: "Dzerofive", 0.01: "Done", 0.02: "Dtwo", 0.05: "Dfive", 0.1: "Dten",
             0.2: "Dtwenty", 0.3: "Dthirty", 0.5: "Dfifty", 0.7: "Dseventy", 1.0: "Dhundred"}
    return table.get(round(float(d), 6), "D" + num_word(round(d * 1000)))


def part_b_scaling(prefix, S_dense):
    files = [RAW / f"{prefix}sparse_scaling.csv", RAW / f"{prefix}sparse_scaling_xl.csv"]
    files = [f for f in files if f.exists()]
    raw = load(files)
    measured = raw[raw["is_warmup"] == 0].copy()
    okd = ok_rows(raw)
    okd["pattern"] = okd["representation"].str.split(":").str[1]
    measured["pattern"] = measured["representation"].str.split(":").str[1]
    for key in ("nnz_a", "nnz_c", "flops_madd"):
        okd[key] = extra(okd, key)
    fig, ax = new_figure(height=2.3)
    rows = []
    colors = {0.001: "#009E73", 0.01: "#CC79A7"}
    for d in sorted(okd["density"].unique()):
        for pat in ("uniform", "banded"):
            g = okd[(okd["density"] == d) & (okd["pattern"] == pat)]
            ns = sorted(g["n"].unique())
            if not ns:
                continue
            s = [stats(g[g["n"] == n]["time_s"]) for n in ns]
            errbar(ax, ns, s, f"CSR, $d$={fmt(d * 100, 2)}\\%, {pat}", colors[d], PATTERN_MK[pat], PATTERN_LS[pat])
            for n, st in zip(ns, s):
                gn = g[g["n"] == n]
                rows.append({"density": d, "pattern": pat, "n": n, "median": st["median"],
                             "iqr": st["q3"] - st["q1"], "k": st["k"], "nnz_a": int(gn["nnz_a"].iloc[0]),
                             "nnz_c": int(gn["nnz_c"].iloc[0]), "flops": int(gn["flops_madd"].iloc[0]),
                             "rss_mib": gn["peak_rss_kib"].median() / 1024})
    # dense reference from Part A (different logical inputs: dense random matrices; kernel cost data-independent)
    nsd = sorted(S_dense["blocked_ikj"])
    errbar(ax, nsd, [stats(S_dense["blocked_ikj"][n]) for n in nsd], "dense blocked (Part A inputs)",
           STYLE["dense"][0], "^", ":")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("Matrix size $n$")
    ax.set_ylabel("Median time [s]")
    ax.legend(fontsize=5.5, loc="upper left")
    savefig(fig, FIG / "sparse_scaling")
    T = pd.DataFrame(rows)
    T.to_csv(SUM / "sparse_scaling_summary.csv", index=False)
    fails = measured[measured["status"] != "ok"]
    fails.to_csv(SUM / "sparse_scaling_failures.csv", index=False)
    macro("SpScaleMaxN", str(int(T["n"].max())))
    macro("SpScaleFailures", str(len(fails)))
    for d in sorted(T["density"].unique()):
        for pat in ("uniform", "banded"):
            sub = T[(T["density"] == d) & (T["pattern"] == pat)]
            if not len(sub):
                continue
            top = sub.sort_values("n").iloc[-1]
            P = pat.capitalize() + density_word(d)
            macro(f"ScaleMaxN{P}", str(int(top["n"])))
            macro(f"ScaleT{P}", fmt_t(top["median"]))
            macro(f"ScaleIQR{P}", fmt_t(top["iqr"]))
            macro(f"ScaleRss{P}", fmt(top["rss_mib"]))
            macro(f"ScaleNnzC{P}", f"{int(top['nnz_c']):,}".replace(",", "\\,"))
            if len(sub) >= 3:
                b = np.polyfit(np.log(sub["n"]), np.log(sub["median"]), 1)[0]
                macro(f"ScaleExp{P}", fmt(b))
    # table
    trows = []
    for _, r in T.sort_values(["density", "pattern", "n"], ascending=[True, False, True]).iterrows():
        trows.append([fmt(r["density"] * 100, 2), r["pattern"], str(int(r["n"])),
                      f"{int(r['nnz_a']):,}".replace(",", "\\,"), f"{int(r['nnz_c']):,}".replace(",", "\\,"),
                      f"{fmt_t(r['median'])} [{fmt_t(r['iqr'])}]", str(int(r["k"])), fmt(r["rss_mib"])])
    write_table("table_scaling.tex", ["$d$ [\\%]", "pattern", "$n$", "nnz(A)", "nnz(C)", "SpGEMM median [IQR]", "$k$",
                                      "RSS [MiB]"], trows,
                "Sparse scaling with $n$ at fixed density (CSR SpGEMM only): median [IQR] over $k$ repetitions, "
                "peak RSS of the process (GNU time).", "tab:scaling", "@{}rlr rr rr r@{}", size="\\scriptsize")
    return T


cfg_bs = [64]


def write_macros():
    lines = ["% generated by analysis/make_all.py -- do not edit",
             "\\makeatletter",
             "\\newcommand{\\val}[1]{\\ifcsname val@#1\\endcsname\\csname val@#1\\endcsname\\else\\textbf{??#1}\\fi}"]
    for k, v in sorted(MACROS.items()):
        lines.append(f"\\expandafter\\def\\csname val@{k}\\endcsname{{{v}}}")
    lines.append("\\makeatother")
    (GEN / "numbers.tex").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    for d in (SUM, FIG, GEN):
        d.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ROOT / "configs" / ("pilot.json" if a.prefix else "experiment.json")).read_text())
    _TIMEOUT[0] = cfg["timeout_s"]
    # overall summary of all raw files of this run (schema of run_measured.py)
    files = sorted(p for p in RAW.glob(f"{a.prefix}*.csv") if a.prefix or not p.name.startswith("pilot_"))
    df = load(files)
    gcols = ["experiment", "method", "n", "density", "representation", "timer_boundary"]
    summ = summarise(df, gcols)
    summ.to_csv(SUM / "summary.csv", index=False)
    limits(summ, gcols).to_csv(SUM / "limits.csv", index=False)
    macro("NRawRows", str(len(df)))
    macro("NMeasuredRows", str(int(((df["is_warmup"] == 0) & (df["status"] == "ok")).sum())))
    macro("NFailedRows", str(int((df["status"] != "ok").sum())))
    macro("LoadMax", fmt(df["loadavg_1m"].astype(float).max(), 2))
    macro("LoadMedian", fmt(df["loadavg_1m"].astype(float).median(), 2))
    # total locked machine time actually consumed (sum of process wall times of every launched process)
    per_proc = df.groupby("run_id")["process_wall_s"].first().astype(float)
    macro("MachineMinutes", fmt(per_proc.sum() / 60, 2))
    corr = json.loads((ROOT / "results" / "correctness_summary.json").read_text())
    macro("CorrChecks", str(corr["tolerance_checks"]))
    macro("CorrMaxRatio", fmt(corr["max_error_over_bound"], 2))
    macro("CorrMaxAbs", f"{corr['max_abs_error']:.1e}".replace("e-", "\\times10^{-") + "}")
    bs, S = part_a(a.prefix)
    cfg_bs[0] = bs
    part_b(a.prefix, S)
    part_b_scaling(a.prefix, S)
    write_macros()
    print(f"analysis done: {len(MACROS)} macros, figures in {FIG}, tables in {GEN}")


if __name__ == "__main__":
    main()

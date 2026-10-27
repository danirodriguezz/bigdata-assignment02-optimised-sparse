#!/usr/bin/env python3
"""Experiment driver for Assignment 2: runs every configuration of a JSON config through
run_measured.py (machine-wide benchmark lock, peak RSS, timeout/OOM recording).

Usage
  run_experiments.py --config configs/experiment.json [--only NAME ...] [--inputs-only] [--dry-run]

Experiment types in the config
  dense  : Part A. One process per (method, n[, block size]); in-process warm-up + repetitions.
           If a configuration fails (timeout/oom/error, exit code 3) larger n are NOT attempted
           for that method and a 'not_attempted' note is printed (no row with an invented time).
           "block_size": "auto" -> fastest median of the block-size study (rule declared in
           docs/experiment_plan.md), read from the raw CSV of the experiment named in "bs_from".
  sparse : Part B. For each (n, pattern, density) one process per mode (spgemm, dense, convert)
           on the same logical inputs A (seed s) and B (seed s+1).
Method order is shuffled per size with a fixed seed (interleaving to spread systematic drift).
"""
import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_inputs as gi  # noqa: E402

RUN_MEASURED = ROOT / ".claude" / "skills" / "benchmark-protocol" / "scripts" / "run_measured.py"
ENV = ["OMP_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1", "MKL_NUM_THREADS=1"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def measured(out_csv, labels, cmd, timeout, dry):
    args = [sys.executable, str(RUN_MEASURED), "--out", str(out_csv), "--warmup", "0", "--reps", "1",
            "--timeout", str(timeout), "--label"] + [f"{k}={v}" for k, v in labels.items()] + \
           ["--env"] + ENV + ["--"] + [str(c) for c in cmd]
    if dry:
        log("DRY " + " ".join(args[-len(cmd):]))
        return 0
    t0 = time.time()
    rc = subprocess.run(args, cwd=ROOT).returncode
    log(f"  -> rc={rc} ({time.time() - t0:.1f}s incl. lock wait) {labels.get('method')} n={labels.get('n')} "
        f"{labels.get('density', '')} {labels.get('representation', '')}")
    return rc


def best_block_size(csv_path, n=None):
    """Declared rule: block size with the smallest median kernel time in the block-size study."""
    import pandas as pd
    df = pd.read_csv(csv_path)
    df = df[(df["is_warmup"] == 0) & (df["status"] == "ok")]
    if n is not None:
        df = df[df["n"] == n]
    df["block_size"] = df["extra_json"].map(lambda s: json.loads(s)["block_size"])
    med = df.groupby("block_size")["time_s"].median()
    return int(med.idxmin()), med


def run_dense(exp, cfg, args, rng):
    out = ROOT / cfg["raw_dir"] / f"{cfg.get('prefix', '')}{exp['name']}.csv"
    seed = cfg["seed_dense"]
    if exp.get("block_size") == "auto":
        src = ROOT / cfg["raw_dir"] / f"{cfg.get('prefix', '')}{exp['bs_from']}.csv"
        bs, med = best_block_size(src, exp.get("bs_tuning_n"))
        log(f"block size rule -> bs={bs} (medians: {med.to_dict()})")
        block_sizes = [bs]
    else:
        block_sizes = exp.get("block_sizes", [exp.get("block_size", 64)])
    failed = set()
    for n in exp["n"]:
        pa = gi.dense_input(ROOT / cfg["input_dir"], n, seed)
        pb = gi.dense_input(ROOT / cfg["input_dir"], n, seed + 1)
        if args.inputs_only:
            continue
        jobs = [(m, b) for m in exp["methods"] for b in (block_sizes if m == "blocked_ikj" else [0])]
        rng.shuffle(jobs)
        reps = exp.get("reps_by_n", {}).get(str(n), exp["reps"])
        warm = exp.get("warmup_by_n", {}).get(str(n), exp["warmup"])
        for method, bs in jobs:
            if method in failed:
                log(f"not_attempted {method} n={n}: a smaller n already failed under the budget")
                continue
            labels = {"assignment": "A2", "experiment": exp["name"], "method": method, "language": "c",
                      "n": n, "dtype": "float64", "representation": "dense", "threads": 1,
                      "seed": seed}
            cmd = [ROOT / "build" / "bench_dense", "--method", method, "--n", n, "--a", pa, "--b", pb,
                   "--bs", bs or 64, "--warmup", warm, "--reps", reps]
            rc = measured(out, labels, cmd, cfg["timeout_s"], args.dry_run)
            if rc == 3:
                failed.add(method)


def run_sparse(exp, cfg, args, rng):
    out = ROOT / cfg["raw_dir"] / f"{cfg.get('prefix', '')}{exp['name']}.csv"
    if exp.get("block_size") == "auto":
        src = ROOT / cfg["raw_dir"] / f"{cfg.get('prefix', '')}{exp['bs_from']}.csv"
        bs, _ = best_block_size(src, exp.get("bs_tuning_n"))
    else:
        bs = exp.get("block_size", 64)
    failed = set()
    for n in exp["n"]:
        for pattern in exp["patterns"]:
            for d in exp["densities"]:
                seed = cfg["seed_sparse"] + int(round(d * 1e6))     # distinct seed per density level
                pa = gi.sparse_input(ROOT / cfg["input_dir"], n, d, pattern, seed)
                pb = gi.sparse_input(ROOT / cfg["input_dir"], n, d, pattern, seed + 1)
                if args.inputs_only:
                    continue
                modes = list(exp["modes"])
                rng.shuffle(modes)
                for mode in modes:
                    key = (mode, pattern, d)
                    if key in failed:
                        log(f"not_attempted mode={mode} {pattern} d={d} n={n}: smaller n failed")
                        continue
                    method = {"spgemm": "csr_gustavson", "dense": "dense_blocked_ikj",
                              "convert": "conversion"}[mode]
                    rep = "csr" if mode != "dense" else "dense"
                    labels = {"assignment": "A2", "experiment": exp["name"], "method": method,
                              "language": "c", "n": n, "dtype": "float64", "density": d,
                              "representation": f"{rep}:{pattern}", "threads": 1, "seed": seed}
                    reps = exp.get("reps_by_mode", {}).get(mode, exp["reps"])
                    cmd = [ROOT / "build" / "bench_sparse", "--mode", mode, "--a", pa, "--b", pb,
                           "--bs", bs, "--warmup", exp["warmup"], "--reps", reps]
                    rc = measured(out, labels, cmd, cfg["timeout_s"], args.dry_run)
                    if rc == 3:
                        failed.add(key)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--only", nargs="*", help="run only these experiment names")
    ap.add_argument("--inputs-only", action="store_true", help="only generate the input files")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for exe in ("bench_dense", "bench_sparse"):
        if not (ROOT / "build" / exe).exists():
            sys.exit("build the programs first: make build")
    rng = random.Random(cfg.get("order_seed", 2026))
    t0 = time.time()
    for exp in cfg["experiments"]:
        if args.only and exp["name"] not in args.only:
            continue
        log(f"=== experiment {exp['name']} ({exp['type']})")
        (run_dense if exp["type"] == "dense" else run_sparse)(exp, cfg, args, rng)
    # checksums of every generated input (committed; the binaries themselves are git-ignored)
    inputs = sorted((ROOT / cfg["input_dir"]).glob("*.json"))
    lines = [f"{json.loads(p.read_text())['sha256']}  {json.loads(p.read_text())['file']}" for p in inputs]
    (ROOT / cfg["input_dir"] / "checksums.sha256").write_text("\n".join(lines) + "\n")
    log(f"done in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()

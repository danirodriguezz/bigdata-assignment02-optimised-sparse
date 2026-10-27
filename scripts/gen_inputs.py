#!/usr/bin/env python3
"""Generate the shared input matrices of Assignment 2 (dense and sparse) with fixed seeds.

Dense  : n x n float64, values ~ U[-1, 1), NumPy PCG64 generator (numpy.random.default_rng(seed)),
         written as raw little-endian row-major float64 (.f64) + JSON sidecar with SHA-256.
Sparse : n x n, exactly nnz = round(d * n^2) distinct nonzero positions, values ~ U[-1, 1)
         (an exact 0.0 is redrawn so that every stored entry is structurally and numerically nonzero).
         Patterns
           uniform : positions drawn uniformly at random over the whole matrix
           banded  : positions drawn uniformly at random inside the narrowest band |i - j| <= w
                     that can hold nnz entries (w is recorded); same nnz as uniform at equal d
         Written as COO (.coo: int64 n, int64 nnz, int32 rows, int32 cols, float64 vals; sorted by
         (row, col)) + JSON sidecar.

Usage (CLI):
  gen_inputs.py dense  --n 1024 --seed 42 --out data/inputs
  gen_inputs.py sparse --n 2048 --density 0.01 --pattern uniform --seed 1042 --out data/inputs
The experiment driver imports dense_input()/sparse_input() and generates files on demand.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

GENERATOR = "numpy.random.default_rng (PCG64), numpy " + np.__version__


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_sidecar(path, meta):
    meta["sha256"] = sha256(path)
    meta["file"] = Path(path).name
    Path(str(path) + ".json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def nonzero_uniform_values(rng, size):
    """U[-1, 1) values with exact zeros redrawn (probability ~2^-53 each, but keep it exact)."""
    v = rng.uniform(-1.0, 1.0, size)
    while True:
        z = v == 0.0
        if not z.any():
            return v
        v[z] = rng.uniform(-1.0, 1.0, int(z.sum()))


def dense_input(out_dir, n, seed):
    """Return the path of the dense matrix (n, seed), generating it if missing."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"dense_n{n}_s{seed}.f64"
    if path.exists() and Path(str(path) + ".json").exists():
        return path
    rng = np.random.default_rng(seed)
    a = rng.uniform(-1.0, 1.0, (n, n)).astype("<f8")
    a.tofile(path)
    _write_sidecar(path, {"kind": "dense", "n": n, "seed": seed, "dtype": "float64",
                          "layout": "row-major", "distribution": "uniform[-1,1)",
                          "generator": GENERATOR})
    return path


def _sample_distinct(rng, population, k):
    """k distinct integers from range(population), uniformly, without materialising the range."""
    if k > population:
        raise ValueError("more nonzeros than positions")
    if k > population // 4:                       # dense enough: a permutation is cheap
        return np.sort(rng.permutation(population)[:k])
    chosen = np.unique(rng.integers(0, population, size=int(k * 1.1) + 16, dtype=np.int64))
    while chosen.size < k:
        extra = rng.integers(0, population, size=int((k - chosen.size) * 1.2) + 16, dtype=np.int64)
        chosen = np.unique(np.concatenate([chosen, extra]))
    # drop a uniformly random subset of the surplus so that exactly k remain
    keep = np.sort(rng.choice(chosen.size, size=k, replace=False))
    return chosen[keep]


def band_size(n, w):
    """Number of positions with |i - j| <= w in an n x n matrix."""
    w = min(w, n - 1)
    return n * (2 * w + 1) - w * (w + 1)


def sparse_positions(rng, n, nnz, pattern):
    """Return (rows, cols, extra_meta) with exactly nnz distinct positions sorted by (row, col)."""
    if pattern == "uniform":
        lin = _sample_distinct(rng, n * n, nnz)
        return (lin // n).astype("<i4"), (lin % n).astype("<i4"), {}
    if pattern == "banded":
        w = 0
        while band_size(n, w) < nnz:
            w += 1
        # enumerate the band row by row: row i holds columns max(0, i-w) .. min(n-1, i+w)
        lo = np.maximum(np.arange(n) - w, 0)
        hi = np.minimum(np.arange(n) + w, n - 1)
        lengths = hi - lo + 1
        starts = np.concatenate([[0], np.cumsum(lengths)[:-1]])
        pick = _sample_distinct(rng, int(lengths.sum()), nnz)   # indices into the band
        rows = np.searchsorted(starts, pick, side="right") - 1
        cols = lo[rows] + (pick - starts[rows])
        meta = {"half_bandwidth": int(w), "band_positions": int(lengths.sum()),
                "band_fill_fraction": nnz / float(lengths.sum())}
        return rows.astype("<i4"), cols.astype("<i4"), meta
    raise ValueError(f"unknown pattern {pattern!r}")


def sparse_input(out_dir, n, density, pattern, seed):
    """Return the path of the sparse matrix (n, density, pattern, seed), generating it if missing."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{density:.6g}".replace(".", "p")
    path = out_dir / f"sparse_{pattern}_n{n}_d{tag}_s{seed}.coo"
    if path.exists() and Path(str(path) + ".json").exists():
        return path
    nnz = int(round(density * n * n))
    rng = np.random.default_rng(seed)
    rows, cols, extra = sparse_positions(rng, n, nnz, pattern)
    vals = nonzero_uniform_values(rng, nnz).astype("<f8")
    with open(path, "wb") as f:
        np.array([n, nnz], dtype="<i8").tofile(f)
        rows.tofile(f)
        cols.tofile(f)
        vals.tofile(f)
    meta = {"kind": "sparse_coo", "n": n, "density_declared": density, "nnz": nnz,
            "density_actual": nnz / float(n * n), "pattern": pattern, "seed": seed,
            "dtype": "float64", "index_dtype": "int32", "distribution": "uniform[-1,1) (zeros redrawn)",
            "generator": GENERATOR}
    meta.update(extra)
    _write_sidecar(path, meta)
    return path


def read_coo(path):
    """Read a .coo file back (used by tests and analysis)."""
    with open(path, "rb") as f:
        n, nnz = np.fromfile(f, dtype="<i8", count=2)
        rows = np.fromfile(f, dtype="<i4", count=nnz)
        cols = np.fromfile(f, dtype="<i4", count=nnz)
        vals = np.fromfile(f, dtype="<f8", count=nnz)
    return int(n), rows, cols, vals


def write_coo(path, n, rows, cols, vals):
    """Write an arbitrary (sorted, duplicate-free) COO matrix (used by the tests)."""
    order = np.lexsort((cols, rows))
    with open(path, "wb") as f:
        np.array([n, len(rows)], dtype="<i8").tofile(f)
        np.asarray(rows, dtype="<i4")[order].tofile(f)
        np.asarray(cols, dtype="<i4")[order].tofile(f)
        np.asarray(vals, dtype="<f8")[order].tofile(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="kind", required=True)
    d = sub.add_parser("dense")
    d.add_argument("--n", type=int, required=True)
    d.add_argument("--seed", type=int, required=True)
    d.add_argument("--out", default="data/inputs")
    s = sub.add_parser("sparse")
    s.add_argument("--n", type=int, required=True)
    s.add_argument("--density", type=float, required=True)
    s.add_argument("--pattern", choices=["uniform", "banded"], required=True)
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--out", default="data/inputs")
    a = ap.parse_args()
    if a.kind == "dense":
        print(dense_input(a.out, a.n, a.seed))
    else:
        print(sparse_input(a.out, a.n, a.density, a.pattern, a.seed))


if __name__ == "__main__":
    main()

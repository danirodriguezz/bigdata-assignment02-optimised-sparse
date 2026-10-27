#!/usr/bin/env python3
"""Correctness tests for every method of Assignment 2 (must pass before any benchmark).

Runs the compiled C programs on small inputs and compares their output with exact answers
(identity, zero, known 2x2 / 3x3) and with trusted references (NumPy matmul for dense, SciPy
sparse product for SpGEMM). Floating-point tolerance (componentwise, Higham's bound for the
classical algorithm evaluated in any order):
    |C - C_ref|_ij <= 2 * n * u * (|A| |B|)_ij + 1e-300,   u = 2^-53
The factor 2 covers both the tested and the reference evaluation orders (gamma_n ~ n*u each).
Exits with status 1 if any check fails.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_inputs as gi  # noqa: E402

DENSE = ROOT / "build" / "bench_dense"
SPARSE = ROOT / "build" / "bench_sparse"
U = 2.0 ** -53
FAILS = []
REPORT = []          # (test, max_abs_err, max_rel_err_vs_bound) for the log
TMP = Path(tempfile.mkdtemp(prefix="a2_tests_"))


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        FAILS.append(name)


def run(cmd):
    out = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"{cmd} failed: {out.stderr}")
    return [json.loads(l) for l in out.stdout.splitlines() if l.startswith("{")]


def within_bound(name, C, ref, A, B, exact=False):
    n = A.shape[0]
    err = np.abs(C - ref)
    if exact:
        check(name, np.array_equal(C, ref), f"max|err|={err.max():.3g} (exact required)")
        return
    bound = 2 * n * U * (np.abs(A) @ np.abs(B)) + 1e-300
    ratio = float((err / bound).max())
    REPORT.append((name, float(err.max()), ratio))
    check(name, bool((err <= bound).all()), f"max|err|={err.max():.3g}, max err/bound={ratio:.3g}")


# ------------------------------------------------------------------ dense kernels
def dense_run(method, A, B, bs=64):
    n = A.shape[0]
    pa, pb, pc = TMP / "A.f64", TMP / "B.f64", TMP / "C.f64"
    A.astype("<f8").tofile(pa)
    B.astype("<f8").tofile(pb)
    rows = run([DENSE, "--method", method, "--n", n, "--a", pa, "--b", pb, "--bs", bs,
                "--warmup", 0, "--reps", 2, "--dump", pc])
    C = np.fromfile(pc, dtype="<f8").reshape(n, n)
    # the printed checksum must be the sum of the dumped result
    check(f"{method} bs={bs} n={n} checksum", np.isclose(rows[-1]["checksum"], C.sum(), rtol=1e-12, atol=1e-12))
    return C


def test_dense():
    rng = np.random.default_rng(7)
    configs = [("naive_ijk", 64), ("reorder_ikj", 64)] + [("blocked_ikj", b) for b in (1, 3, 16, 64, 256)]
    for method, bs in configs:
        tag = f"{method}(bs={bs})" if method == "blocked_ikj" else method
        A2 = np.array([[1.0, 2.0], [3.0, 4.0]]); B2 = np.array([[5.0, 6.0], [7.0, 8.0]])
        within_bound(f"{tag} known 2x2", dense_run(method, A2, B2, bs), np.array([[19.0, 22.0], [43.0, 50.0]]), A2, B2, exact=True)
        A3 = np.arange(1.0, 10.0).reshape(3, 3); B3 = np.array([[2.0, 0, 1], [1, 3, 0], [0, 1, 4]])
        within_bound(f"{tag} known 3x3", dense_run(method, A3, B3, bs), np.array([[4.0, 9, 13], [13, 21, 28], [22, 33, 43]]), A3, B3, exact=True)
        for n in (1, 7, 100):
            A = rng.uniform(-1, 1, (n, n))
            within_bound(f"{tag} identity n={n}", dense_run(method, A, np.eye(n), bs), A, A, np.eye(n), exact=True)
            within_bound(f"{tag} zero n={n}", dense_run(method, A, np.zeros((n, n)), bs), np.zeros((n, n)), A, np.zeros((n, n)), exact=True)
        for n in (2, 31, 64, 100, 257):
            A = rng.uniform(-1, 1, (n, n)); B = rng.uniform(-1, 1, (n, n))
            within_bound(f"{tag} random n={n} vs numpy", dense_run(method, A, B, bs), A @ B, A, B)


# ------------------------------------------------------------------ sparse
def to_coo_file(M, name):
    M = sp.coo_matrix(M)
    path = TMP / name
    gi.write_coo(path, M.shape[0], M.row, M.col, M.data)
    return path


def sparse_modes(Ad, Bd, label):
    """Run spgemm, dense and convert modes on the same logical inputs and compare."""
    n = Ad.shape[0]
    pa, pb = to_coo_file(Ad, "A.coo"), to_coo_file(Bd, "B.coo")
    ref = (sp.csr_matrix(Ad) @ sp.csr_matrix(Bd)).toarray()
    structural = int(((Ad != 0).astype(np.int64) @ (Bd != 0).astype(np.int64) != 0).sum())
    for mode in ("spgemm", "dense", "convert"):
        out = TMP / f"C_{mode}.f64"
        rows = run([SPARSE, "--mode", mode, "--a", pa, "--b", pb, "--bs", 16,
                    "--warmup", 0, "--reps", 1, "--dump", out])
        C = np.fromfile(out, dtype="<f8").reshape(n, n)
        within_bound(f"{label} mode={mode} vs scipy", C, ref, Ad, Bd)
        if mode == "spgemm":
            nnz_c = rows[-1]["nnz_c"]
            check(f"{label} nnz(C) = structural nnz", nnz_c == structural, f"({nnz_c} vs {structural})")
            check(f"{label} nnz(A), nnz(B) reported", rows[-1]["nnz_a"] == np.count_nonzero(Ad)
                  and rows[-1]["nnz_b"] == np.count_nonzero(Bd))
            flops = int(sum(np.count_nonzero(Bd[k]) for k in np.nonzero(Ad)[1]))
            check(f"{label} flop count", rows[-1]["flops_madd"] == flops)
        if mode == "convert":
            conv = [r for r in rows if r["timer_boundary"] == "convert_dense_to_csr"][0]
            check(f"{label} dense->csr nnz", conv["nnz_a"] == np.count_nonzero(Ad)
                  and conv["nnz_b"] == np.count_nonzero(Bd))


def test_sparse():
    rng = np.random.default_rng(11)
    n = 60
    A = rng.uniform(-1, 1, (n, n)) * (rng.random((n, n)) < 0.1)
    sparse_modes(A, np.eye(n), "sparse identity n=60")
    sparse_modes(A, np.zeros((n, n)), "sparse zero B n=60")
    sparse_modes(np.zeros((n, n)), A, "sparse zero A n=60")
    E = A.copy(); E[5:20, :] = 0.0                          # empty rows in A and empty cols in B
    F = A.T.copy(); F[:, 30:40] = 0.0
    sparse_modes(E, F, "sparse empty rows/cols n=60")
    A2 = np.array([[1.0, 0], [0, 2.0]]); B2 = np.array([[0, 3.0], [4.0, 0]])
    sparse_modes(A2, B2, "sparse known 2x2")
    for pattern in ("uniform", "banded"):
        for n, d in ((50, 0.02), (200, 0.01), (200, 0.1), (300, 0.5)):
            pa = gi.sparse_input(TMP, n, d, pattern, 100 + n)
            pb = gi.sparse_input(TMP, n, d, pattern, 200 + n)
            _, r, c, v = gi.read_coo(pa)
            Ad = np.zeros((n, n)); Ad[r, c] = v
            meta = json.loads(Path(str(pa) + ".json").read_text())
            check(f"generator {pattern} n={n} d={d} exact nnz", np.count_nonzero(Ad) == round(d * n * n) == len(v))
            if pattern == "banded":
                check(f"generator banded n={n} d={d} inside band", int(np.abs(r - c).max()) <= meta["half_bandwidth"])
            _, r, c, v = gi.read_coo(pb)
            Bd = np.zeros((n, n)); Bd[r, c] = v
            sparse_modes(Ad, Bd, f"{pattern} n={n} d={d}")


if __name__ == "__main__":
    for exe in (DENSE, SPARSE):
        if not exe.exists():
            sys.exit(f"missing {exe}: run make build")
    test_dense()
    test_sparse()
    worst = max((r[2] for r in REPORT), default=0.0)
    worst_abs = max((r[1] for r in REPORT), default=0.0)
    summary = {"checks_failed": len(FAILS), "tolerance_checks": len(REPORT),
               "max_abs_error": worst_abs, "max_error_over_bound": worst}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "correctness_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))
    if FAILS:
        print(f"{len(FAILS)} checks FAILED: {FAILS[:10]}")
        sys.exit(1)
    print("ALL CORRECTNESS TESTS PASSED")

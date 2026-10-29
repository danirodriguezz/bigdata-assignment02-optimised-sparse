# Decisions log — Assignment 02

Record every design decision with date, the options considered and Daniel's answer.
Sibling assignments read this file to stay consistent.

| Date | Decision | Choice | Rationale / who decided |
|---|---|---|---|
| 2026-10-27 | Benchmark budget | ≤ 90 min machine time for this assignment; 600 s max per process run; 8 GB memory | Daniel |
| 2026-10-27 | Hardware counters (perf) | Not available (perf_event_paranoid=4) — state as limitation | Daniel |
| 2026-10-27 | Other open choices (language, methods, threads, repo name) | Recommended defaults from CLAUDE.md, delegated to the agent | Daniel delegated |
| 2026-10-27 | Baseline provenance | A1 (`../Assignment01_Basic_MatMul_Languages/src/`) had no C code yet → own naive i-j-k kernel in `src/c/baseline/matmul_naive.c`, validated by `tests/test_correctness.py` | Agent (CLAUDE.md fallback rule) |
| 2026-10-27 | Language / compiler | C11, gcc 13.3 `-O2 -std=c11`, same flags for every method, no `-march=native`, no BLAS, single thread | Agent (recommended default, delegated) |
| 2026-10-27 | Dense methods | naive_ijk (baseline), reorder_ikj (loop interchange), blocked_ikj (3-level tiling, ikj inside tile). Strassen not implemented (time) | Agent (recommended default) |
| 2026-10-27 | Sparse format / kernel | Own CSR (int64 row_ptr, int32 col_idx, float64 val) + own two-phase Gustavson SpGEMM; SciPy/NumPy only as correctness references | Agent (recommended default) |
| 2026-10-27 | Block-size rule | b ∈ {16,32,48,64,96,128,256} at n=1024 and 2048; the fastest median at n=2048 is used everywhere else (declared before running) | Agent |
| 2026-10-27 | Density grid | Extended up to 100 % after the pilot showed SpGEMM still faster than dense at 50 % | Agent (pilot evidence) |
| 2026-10-27 | Repetitions | In-process: 1 warm-up + k=5; n ≥ 3072 dense: 0 warm-up + k=3 (time budget) | Agent |
| 2026-10-27 | Memory enforcement | Every benchmark process wrapped in `prlimit --as=8 GiB`; allocation failure → `oom` row | Agent |
| 2026-10-29 | Power | Full run started only after AC power was connected (environment.md captured on AC) | Daniel |
| 2026-10-29 | GitHub repo name | `bigdata-assignment02-optimised-sparse` (Daniel creates and pushes) | Recommended default |
| 2026-10-29 | GitHub repository | `git@github.com:danirodriguezz/bigdata-assignment02-optimised-sparse.git` (same GitHub user as A1; Daniel creates the repo and pushes) | Agent (from A1 DECISIONS) |
| 2026-10-29 | SIMD | Assembly + `-fopt-info-vec-all` show no kernel is vectorised at -O2 (scalar mulsd/addsd); kept as is (comparison isolates memory-order effects); plan statement corrected | Agent (verified) |

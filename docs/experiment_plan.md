# Experiment plan — Assignment 02 (written before the full benchmark, 2026-10-27)

## Research questions
- **RQ-A (dense optimisation).** On one i7-9750H core with gcc -O2, how much do loop reordering (i-k-j) and
  cache blocking reduce the runtime of float64 dense n x n multiplication relative to the naive i-j-k
  baseline, and how does the effect change with n?
- **RQ-B (sparse storage).** For matched logical inputs at n = 2048, at which tested densities does a CSR
  representation with Gustavson's SpGEMM run faster or use less memory than the best dense kernel, and
  how does the answer change with the nonzero structure (uniform random vs banded) and with conversion
  costs?

Factors: method, n, block size (Part A); density d, nonzero pattern, n (Part B).
Outcomes: kernel time (median, IQR), GFLOP/s, peak RSS, analytical storage, nnz(C).

## Hypotheses (predictions, not results)
- **H1** reorder_ikj and blocked_ikj are faster than naive_ijk, with a gap that grows with n (the baseline
  reads B with stride 8n bytes and becomes memory-bound once B no longer fits in cache).
- **H2** blocking adds a benefit over reorder_ikj once the matrices exceed the 12 MiB L3 (n >= ~1024).
- **H3** CSR SpGEMM beats the dense kernel below a crossover density that depends on the nonzero pattern.
  Since SpGEMM work grows like d^2 n^3 (uniform inputs) and dense work like n^3, the crossover is expected
  at a high density compared with SpMV-style reasoning.
- **H4** output fill-in (nnz(C) >> nnz(A)) and conversion costs reduce the sparse advantage as d grows;
  at equal density, the banded pattern (less fill-in, better locality) is faster than uniform.

## Methods (all C, gcc 13.3 -O2 -std=c11, single thread, float64, row-major)
| id | change vs baseline |
|---|---|
| naive_ijk | baseline, scalar dot product per C(i,j); B read down a column |
| reorder_ikj | loop order i-k-j, unit stride on B and C; auto-vectorisable at -O2 (gcc >= 12) |
| blocked_ikj(b) | i, k, j tiled in b x b tiles, i-k-j inside a tile |
| csr_gustavson | own CSR + two-phase Gustavson SpGEMM (marker array + dense accumulator), output unsorted |
| dense_blocked_ikj | best dense kernel (blocked_ikj, b from the study) on the densified sparse inputs |
SciPy (`scipy.sparse`) and NumPy are used **only** as correctness references.

## Inputs
- Dense: U[-1,1) float64, `numpy.random.default_rng(seed)` (PCG64), A seed 42, B seed 43, one shared file per
  (n, seed), SHA-256 in sidecar JSON and `data/inputs/checksums.sha256`.
- Sparse: exactly nnz = round(d n^2) distinct positions, values U[-1,1) (exact zeros redrawn).
  Patterns: `uniform` (positions uniform over the matrix) and `banded` (positions uniform inside the narrowest
  band |i-j| <= w that can hold nnz entries). Seeds: A = 1000 + round(10^6 d), B = A + 1.
- Density levels at n = 2048: d in {0.1, 0.5, 1, 2, 5, 10, 20, 30, 50, 70, 100} % (extended to 100 % because the
  pilot showed SpGEMM still faster than dense at 50 %).
- Sparse scaling: d in {0.1, 1} %, uniform and banded, n in {1024, ..., 32768} (n = 32768 only at 0.1 %).

## Timing boundaries (never mixed in one comparison)
- `kernel` (Part A): one call of the kernel; inputs loaded, C allocated and zeroed before the timer.
- `spgemm_kernel`: CSR x CSR -> CSR including symbolic phase and allocation of C; inputs already CSR.
- `dense_kernel`: blocked kernel on densified inputs (same boundary as `kernel`).
- `convert_dense_to_csr` (both inputs) and `convert_csr_to_dense` (output), measured separately and added
  explicitly only where stated ("end-to-end from dense" = dense->CSR + SpGEMM + CSR->dense).

## Protocol
- Timer: `clock_gettime(CLOCK_MONOTONIC)`; checksum of C printed (prevents dead-code elimination).
- One process per configuration; in-process 1 warm-up + 5 measured repetitions (k = 5).
  Costly configurations (n >= 3072 in Part A): 0 warm-up, k = 3 (declared, justified by the time budget).
- Statistic: median and IQR over the k measured repetitions; every raw row kept.
- Memory: peak RSS of the process (GNU time %M via run_measured.py) and analytical array storage
  (`array_storage_estimate`: dense 3 x 8n^2; CSR 12 nnz + 8(n+1) per matrix + SPA 12n).
- Machine-wide lock (`run_measured.py`) per configuration; method order shuffled per size (seeded).
- Block-size rule: b in {16, 32, 48, 64, 96, 128, 256} at n = 1024 and n = 2048; the size sweep and the dense
  comparator of Part B use the b with the smallest median at **n = 2048** (declared before running).
- Sizes Part A: n in {256, 512, 768, 1024, 1536, 2048, 3072, 4096}; a method stops escalating after its first
  failure (timeout/oom).

## Budgets (agreed with Daniel, 2026-10-27)
- Max 600 s per process run (timeout → recorded as `timeout`, no time).
- Memory 8 GiB, enforced with `prlimit --as=8589934592` on every benchmark process (allocation failure →
  recorded as `oom`). Configurations whose analytical storage alone exceeds 8 GiB (dense n = 32768:
  3 x 8.6 GB) are not attempted and reported as such.
- Total machine time for this assignment ≤ 90 min (pilot estimate ≈ 50 min of locked time).

## Limitations known in advance
- No hardware counters (perf_event_paranoid = 4): bottlenecks inferred from timing, GFLOP/s, nnz and storage.
- Shared laptop: three other agents run (locked) benchmarks and unlocked work; `loadavg_1m` recorded per row.
- powersave governor with turbo enabled: frequency not pinned.

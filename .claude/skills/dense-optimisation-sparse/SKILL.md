---
name: dense-optimisation-sparse
description: Technical guide for Assignment 2 — sequential dense matrix multiplication optimisations (loop reordering, cache blocking with block-size study, unrolling, Strassen) against a validated naive baseline, and sparse matrix multiplication (CSR, Gustavson SpGEMM) vs dense across declared densities and nonzero structures, including conversion costs, nnz of inputs/outputs, memory and hardware-counter evidence. Use when designing, coding, testing or analysing Assignment 2.
---

# Dense optimisations and sparse matrices

## 0. Language and baseline
- Recommended: **C** (gcc 13, `-O2 -std=c11`, same flags for all methods, single thread), reusing the
  **validated naive ijk C implementation of Assignment 1** (`../Assignment01_*/src/c/`). Copy it to
  `src/c/baseline/` and record provenance in `docs/DECISIONS.md` and README (path + git commit of A1).
  If A1 is not available yet, implement the same naive ijk kernel here, validate it, and say so.
- Alternative: Java (then JIT warm-up rules of A1 apply). Do not mix languages inside Part A.
- Reuse A1's input generator (float64 little-endian binary + sidecar JSON + sha256) and the CSV schema.

## Part A — dense, sequential (≥ 3 methods: baseline + ≥ 2 optimised)
Recommended set (each = one identifiable change with an expected effect you state *before* measuring):
| Method id | Change vs baseline | Expected effect (hypothesis) |
|---|---|---|
| `naive_ijk` | baseline: inner loop walks a column of B (stride n) | many cache misses for large n |
| `reorder_ikj` | loop order i-k-j: `C[i][*] += A[i][k]·B[k][*]` | unit stride on B and C → fewer misses, auto-vectorisable inner loop |
| `blocked_ikj(b)` | tiling i,k,j in b×b blocks, ikj inside the tile | working set ≈ 3·8·b² B fits in L1/L2 → reuse; benefit grows when n² exceeds the LLC |
| optional `strassen(c)` | 7 recursive products, cutoff c to `blocked_ikj` | fewer flops O(n^2.807) but extra additions/temporaries; benefit only for large n; weaker error bound |
| optional `unrolled` / `transposed_B` | manual unroll ×4 / multiply by Bᵀ | compare with what the compiler already does at -O2 |

Rules:
- Same inputs, numeric type (float64), timing boundary (`kernel`: output allocated and zeroed outside the timer,
  state it), compiler flags, single thread (`OMP_NUM_THREADS=1`; no BLAS).
- **Block-size study**: sweep b ∈ {16, 32, 48, 64, 96, 128, 256} at one or two n; choose b by a declared rule
  (fastest median at the tuning size) and then use it for the size sweep; report the sweep (tuning is a result).
- Strassen: handle n not power of two (padding or peeling — say which), declare cutoff, measure extra memory.
- Correctness: identity, zero, known small cases, random vs NumPy reference with tolerance
  `2·n·u·(|A||B|)_ij` (Higham) for reordered/blocked; Strassen needs a looser, justified tolerance (its error bound
  is normwise, not componentwise — report the observed max relative error). Report observed max errors.
- Sizes: e.g. n ∈ {256, 512, 768, 1024, 1536, 2048, 3072, 4096} under the budget; the naive baseline may time out
  first — record it.
- **Bottleneck evidence (strongly recommended)**: hardware counters with
  `perf stat -e cycles,instructions,L1-dcache-load-misses,LLC-load-misses,LLC-loads <prog>` at a representative n
  (IPC and miss rates per method). `perf` is installed but `kernel.perf_event_paranoid=4` blocks it: ask Daniel to
  run `! sudo sysctl -w kernel.perf_event_paranoid=1` (temporary until reboot). If he declines, state the limitation.
  Counter runs are separate from timed runs.
- Metrics: speedup over baseline at each n (`speedup.py` works with `--resource` replaced by method comparison, or
  compute ratio of medians with bootstrap CI), GFLOP/s = `2n³ / T / 1e9` for classical methods (for Strassen report
  "effective GFLOP/s" = 2n³/T and say so).

## Part B — sparse
### Representation and own code
- **CSR** (row_ptr[n+1], col_idx[nnz] int32, val[nnz] float64) implemented by you. Memory model:
  `8·nnz + 4·nnz + 4·(n+1)` bytes (state index width; int64 if nnz may exceed 2³¹).
- **SpGEMM = Gustavson's row-wise algorithm** (Gustavson 1978 — verify): for each row i of A, for each nonzero a_ik,
  scatter `a_ik · B[k,:]` into a dense accumulator (SPA) of length n with a "touched columns" list; gather into C's
  row (sorted or unsorted — say which). Two-phase (symbolic count + numeric) or growable buffers — say which.
- Library functionality: SciPy `scipy.sparse` only as **correctness reference** (not counted as your method) —
  or, if you include it as an extra comparison, label it clearly as library code.
- Dense comparator: the best dense method of Part A (and optionally the naive baseline) on the **same logical
  matrices** (densified).

### Inputs (declare everything)
- Density d = nnz/n² (percentage of nonzeros); sparsity = 1 − d. Declare levels, e.g. at n = 2048 (and one larger n):
  d ∈ {0.1, 0.5, 1, 2, 5, 10, 20, 50} %.
- Generators with seeds: (1) **uniform random positions** (exactly round(d·n²) distinct positions, values U[-1,1));
  (2) at least one **structured** pattern at the *same density*, e.g. **banded** (bandwidth chosen to match d) or
  **power-law row lengths** — this is what lets you show that the percentage of zeros alone does not determine
  performance. Optional: one real matrix from the SuiteSparse collection (Davis & Hu 2011 — verify), cited.
- Store inputs as COO/CSR binary + sidecar JSON (n, d, pattern, seed, nnz, sha256).

### Measurements
- Separate timing boundaries, reported separately (never summed silently):
  `convert_dense_to_csr`, `spgemm_kernel` (CSR×CSR→CSR), `dense_kernel` (best dense), optional `csr_to_dense`.
  State in the report which comparisons include conversion.
- Record **nnz(A), nnz(B), nnz(C)** and output density; compare nnz(C) with the uniform-random expectation
  `n²·(1 − (1 − d²)^n)` (show the product becomes denser — "fill-in"). Pass them in the JSON (`extra_json`).
- Memory: peak RSS (GNU time) + analytical CSR storage vs dense `8n²` per matrix.
- Find the **crossover density** where sparse stops beating dense, per pattern, at fixed n; explain with indexing
  overhead (irregular access, SPA), output size and conversion costs.

## Analysis checklist
- Part A: runtime vs n (log-log, IQR bars); speedup vs baseline per n; GFLOP/s vs n; block-size sweep figure;
  counters table; largest feasible n per method.
- Part B: time vs density (log-y) for sparse and dense at fixed n, per pattern; nnz(C)/output density vs density;
  memory vs density; conversion cost share; crossover; scaling with n at a fixed low density.
- Discuss **optimisation effects separately from sparse-storage/input-structure effects** (two sub-sections).

## Hypotheses (predictions to label as such)
H1 ikj and blocking reduce time vs ijk increasingly with n (memory-bound baseline); H2 blocking adds benefit over ikj
once matrices exceed the LLC; H3 CSR beats dense below a crossover density that depends on the nonzero pattern;
H4 output fill-in and conversion reduce the sparse advantage as density grows.

## References to verify (candidates)
Lam et al. 1991 (blocking), Goto & van de Geijn 2008, Strassen 1969, Higham 2002 (Strassen stability),
Gustavson 1978, Saad 2003 (CSR), Buluç & Gilbert 2012 (SpGEMM), Davis & Hu 2011, Hennessy & Patterson 2017.

---
name: benchmark-protocol
description: Course-mandated experimental protocol for timing and memory benchmarks of matrix multiplication (ULPGC Big Data). Use whenever you design an experiment, write a timing harness, choose matrix sizes or budgets, run benchmarks, record raw measurements, or measure memory. Provides run_measured.py (locking, warm-up, repetitions, peak RSS, timeout/OOM recording) and capture_env.sh.
---

# Benchmark protocol

The rules below operationalise `context/common_protocol.md`. Read that file once; it is the source of truth.

## 0. Non-negotiable rules
1. **Never fabricate or estimate a measurement.** Every number in the report comes from a file in `results/`.
   If a run did not complete, it is a `timeout`/`oom`/`error` row, never a guessed time.
2. **Validate before benchmarking.** Correctness tests (identity, zero, known 2×2/3×3, random vs reference)
   must pass for every method before any timed run.
3. **One benchmark at a time on this machine.** Always run timed experiments through
   `scripts/run_measured.py` (it takes the machine-wide lock `~/.cache/bigdata_bench.lock`, shared by the
   four assignment folders). Never run two timed experiments in parallel, and do not compile or run heavy
   jobs while a benchmark is running. If you must time inside your own driver, wrap it with
   `flock ~/.cache/bigdata_bench.lock <command>`.
4. **Keep every raw row.** Append-only CSV in `results/raw/`. Never edit or delete rows by hand; if a run is
   invalid (e.g. laptop on battery), keep it and document the exclusion rule in the analysis script.
5. **Same timing boundary within a comparison.** Label it in the `timer_boundary` column
   (`kernel`, `kernel+alloc`, `end_to_end`, `process_wall`, ...).

## 1. Experiment plan first (`docs/experiment_plan.md`)
Write it before coding the benchmarks, and get Daniel's OK on the budgets:
- Research question, factor(s) varied, outcome(s) measured, **hypothesis/prediction (labelled as such)**.
- Methods compared and why the comparison is fair (same algorithm / numeric type / inputs / boundary).
- Declared size sequence (e.g. `n ∈ {64, 128, 256, 512, 1024, 2048}`), plus correctness sizes.
- **Budgets**: max runtime per process run (e.g. 600 s) and memory budget (e.g. 8 GB of the 15 GiB).
  Pre-compute dense storage `3 · 8n²` bytes to predict where the memory budget ends.
- Repetitions (≥ 5 measured), warm-ups (number and why), timer boundary, memory metric(s) and tool.
- Inputs: generator, seed(s), value range (e.g. uniform [-1, 1)), numeric type (float64 unless justified).

## 2. Inputs
- Prefer **one shared input file per (n, seed)** generated once (e.g. little-endian float64 binary + JSON
  sidecar with n, seed, generator, range, SHA-256). All languages/methods read the same file.
- Input generation and file loading happen **outside** the timed kernel region.
- Do not store huge inputs in git: commit the generator and the SHA-256 checksums instead.

## 3. Timing harness rules
| Language | Monotonic timer | Notes |
|---|---|---|
| C | `clock_gettime(CLOCK_MONOTONIC, ...)` | Consume result (checksum print) to avoid dead-code elimination; record `-O` flags. |
| Java | `System.nanoTime()` or **JMH** | JIT: in-process warm-up iterations, fixed `-Xms/-Xmx`, record JVM flags and GC. |
| Python | `time.perf_counter_ns()` | Record CPython version; pure Python loops for "basic"; NumPy only as reference. |

- Very short kernels (< ~10 ms): time a batch of k multiplications, report time per multiplication, record k.
- Each benchmark program prints **one JSON line per measured (or warm-up) repetition** on stdout, e.g.
  `{"time_s": 0.8123, "timer_boundary": "kernel", "repetition": 3, "is_warmup": false, "checksum": 1234.5,
  "memory_metric": "jvm_heap_used_peak", "memory_bytes": 25165824}`
  `run_measured.py` turns those lines into CSV rows and adds process peak RSS.
- Thread control: set and record `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` (=1 for any
  sequential measurement, including the NumPy reference). Use `--env KEY=VALUE` of `run_measured.py`.

## 4. Memory metrics (name them precisely; never mix them in one comparison)
| Metric | Tool | Measures |
|---|---|---|
| `peak_rss_kib` (always recorded) | GNU `/usr/bin/time -f %M` via `run_measured.py` | Peak resident set of the whole process (runtime, interpreter, JVM included) |
| `tracemalloc_peak` | Python `tracemalloc` | Python-level allocations only (slows execution → measure in a separate run) |
| `jvm_heap_used_peak` | `MemoryMXBean` / `MemoryPoolMXBean.getPeakUsage()` | Managed heap only |
| `array_storage_estimate` | formula (e.g. `3·8n²`, CSR `8·nnz + 4·nnz + 4·(n+1)`) | Theoretical data storage |
Report the metric name + tool next to every memory number, and state limitations (RSS includes runtime baseline;
heap measurement depends on GC timing, etc.).

## 5. Running
```bash
python3 .claude/skills/benchmark-protocol/scripts/run_measured.py \
  --out results/raw/<experiment>.csv --warmup 1 --reps 5 --timeout 600 \
  --label assignment=A1 experiment=size_sweep method=naive_ijk language=c n=512 dtype=float64 seed=42 threads=1 \
  --env OMP_NUM_THREADS=1 -- ./build/matmul --n 512 --input data/inputs/n512_s42.bin
```
- Exit code 3 = this configuration failed (timeout/oom/error) → the driver must **stop escalating n** for that
  method and record the largest successful size.
- Write a driver `scripts/run_experiments.sh` (or `.py`) that loops over the declared configurations,
  so the full experiment is reproducible with one command. Randomise or interleave method order across
  sizes when feasible to avoid systematic drift.
- Before the full run: pilot run with 1 rep at small n to check the pipeline end-to-end.
- Laptop hygiene: AC power plugged, close heavy apps, record `loadavg_1m` (done automatically) and the CPU
  governor (`capture_env.sh`). Mention thermal throttling risk as a limitation.

## 6. Environment capture
`bash .claude/skills/benchmark-protocol/scripts/capture_env.sh results/environment.md` at the start of each
benchmark session. Copy the relevant facts into the report's Methodology table (CPU, cores/threads, RAM, OS,
compiler + flags, JDK + JVM flags, Python + packages, thread settings).

## 7. Raw CSV schema (`results/raw/*.csv`)
`run_id, timestamp, host, assignment, experiment, method, language, n, dtype, density, representation,
threads, workers, nodes, process_run, repetition, is_warmup, timer_boundary, time_s, process_wall_s,
peak_rss_kib, memory_metric, memory_bytes, status, returncode, seed, checksum, loadavg_1m, cmd, extra_json`
Document it in `results/README.md` (units: seconds, KiB, bytes).

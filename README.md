# Assignment 02 — Cache-Aware Optimisation of Dense Matrix Multiplication and the Density Threshold for Sparse CSR Multiplication

**Author:** Daniel Rodríguez Alonso · Grado en Ciencia e Ingeniería de Datos · ULPGC
**Course:** Big Data, academic year 2026–2027 · **Report:** `deliverables/Assignment02_RodriguezAlonso_Report.pdf`

**Research questions.**
(A) How much do loop reordering (i-k-j) and cache blocking speed up sequential float64 dense matrix
multiplication over a validated naive i-j-k baseline, and how does the effect change with n?
(B) For matched logical inputs, at which tested densities does an own CSR + Gustavson SpGEMM beat the best
dense kernel in time or memory, and how do the nonzero pattern (uniform vs banded) and conversion costs change
the answer?

## 1. Environment used for the reported results
See `results/environment.md` (captured automatically). Summary: Intel Core i7-9750H (6 cores / 12 threads,
L3 12 MiB), 15 GiB RAM, Ubuntu 24.04.5 (Linux 7.0), gcc 13.3, AC power, governor `powersave`, turbo on.
All measurements are single-threaded.

## 2. Dependencies
| Tool | Version | Notes |
|---|---|---|
| gcc | 13.3.0 | `-O2 -std=c11 -Wall -Wextra`, same flags for every method, no `-march=native`, no BLAS |
| Python | 3.12.3 | venv in `.venv`; packages pinned in `requirements-lock.txt` (NumPy 2.5.4, SciPy 1.18.1, pandas 3.1.0, Matplotlib 3.11.2) |
| GNU time, prlimit (util-linux) | system | peak RSS and the 8 GiB address-space limit |
| LaTeX | TinyTeX (IEEEtran, latexmk) | only for `make report` |

NumPy/SciPy are used **only** to generate inputs and as correctness references; every timed kernel is own C code.

## 3. Reproduce
```bash
make setup      # venv + compile build/bench_dense and build/bench_sparse
make test       # correctness tests (must print ALL CORRECTNESS TESTS PASSED)
make inputs     # regenerate every input file + SHA-256 checksums (deterministic seeds)
make pilot      # optional smoke test (small n, 1 rep)
make bench      # full experiment, configs/experiment.json (~1 h of CPU on the machine above,
                # longer wall time if other benchmarks hold the machine-wide lock)
make analysis   # results/raw -> results/summary, report/figures, report/generated
make report     # PDF -> deliverables/Assignment02_RodriguezAlonso_Report.pdf
```
`make all` runs the whole chain. Configuration: `configs/experiment.json` (sizes, densities, patterns,
block sizes, warm-ups, repetitions, 600 s timeout per process, 8 GiB memory limit per process).

## 4. Data
- **Dense inputs:** n × n float64, U[-1, 1), NumPy PCG64 (`default_rng`), A seed 42, B seed 43.
- **Sparse inputs:** exactly round(d·n²) distinct positions, values U[-1, 1) (zeros redrawn), patterns
  `uniform` and `banded` (narrowest band |i−j| ≤ w that holds nnz entries); seeds A = 1000 + 10⁶·d, B = A + 1.
- Binary input files are git-ignored (large); `make inputs` regenerates them byte-identically. Their JSON
  sidecars and `data/inputs/checksums.sha256` are committed.
- **Raw results:** `results/raw/*.csv` — schema, timing boundaries and `extra_json` keys in `results/README.md`.
  Pilot files (`pilot_*.csv`) were used only for planning.

## 5. Reused materials
None. Assignment 1 had no validated C kernel when this work started (2026-10-27), so the naive baseline
`src/c/baseline/matmul_naive.c` was implemented and validated here (see `docs/DECISIONS.md`). The benchmark
harness `run_measured.py`, `capture_env.sh` and the plotting/summary helpers come from the course skill folder
`.claude/skills/` included in this repository.

## 6. Repository layout
```
src/c/baseline/   naive i-j-k kernel (baseline)
src/c/dense/      reorder_ikj, blocked_ikj + matmul_dense.h (interface reused by A3/A4)
src/c/sparse/     CSR + Gustavson SpGEMM + conversions
src/c/common/     I/O, timer, checksum
src/c/bench_*.c   benchmark drivers (one JSON line per repetition)
tests/            correctness tests (NumPy / SciPy references)
scripts/          gen_inputs.py, run_experiments.py
configs/          pilot.json, experiment.json
data/inputs/      input sidecars + checksums
results/          raw CSVs, summaries, environment.md, correctness_summary.json
analysis/         make_all.py (all tables, figures and numbers of the report)
report/           main.tex, references.bib, figures/, generated/
docs/             DECISIONS.md, experiment_plan.md, PROGRESS.md, review_checklist.md, defensa_oral.md
```

## 7. Use of Generative AI
Claude Code (Anthropic, model Claude Opus 5.5) assisted with planning the experiment, drafting and debugging
the C and Python code, the analysis scripts and the LaTeX report. The author reviewed and ran all code; all
measurements come from the author's runs on the machine above, and every reference was checked against its DOI
or official page.

## License
MIT

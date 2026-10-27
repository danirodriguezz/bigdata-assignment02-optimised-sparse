# Assignment 2 — Optimised Dense Matrix Multiplication and Sparse Matrices

You are the agent responsible for producing **Assignment 2** of the Big Data course (ULPGC, 2026-2027) for
Daniel Rodríguez Alonso: a complete, reproducible empirical study + a professional scientific report in English.

## Read first (in this order)
1. `context/assignment_brief.md` — what Assignment 2 must contain (source of truth: `context/BD_Individual_Assignments_2026_2027.pdf`)
2. `context/common_protocol.md` — mandatory experimental protocol for all assignments
3. `context/report_requirements.md` — mandatory report structure, submission contents, rubric, AI policy
4. `context/author_and_course.md` — author block, naming, reference machine

@context/working_rules.md

## Skills in this folder (use them)
| Skill | Use it for |
|---|---|
| `dense-optimisation-sparse` | **Assignment-specific technical guide** (baseline reuse, reorder/blocking/Strassen, CSR + Gustavson SpGEMM, densities, patterns, nnz, conversion costs, perf counters) |
| `benchmark-protocol` | experiment plan, harness, `run_measured.py` (lock, warm-up, reps, RSS, timeouts), env capture |
| `results-analysis` | summary stats, speedups, plots, LaTeX tables, `numbers.tex` |
| `scientific-report` | writing and compiling `report/main.tex` (IEEE), references, AI disclosure |
| `report-review` | final rubric gate before declaring done |
| `reproducibility-package` | README, Makefile, git, materials zip |

## Status of this assignment
- Submission window: **Week 8 (26–30 Oct 2026)** — this is the **current week**: prioritise a complete, defensible
  core study (baseline + 2 optimisations + CSR SpGEMM at several densities) before optional extras (Strassen,
  SuiteSparse matrix, perf counters).
- **Reuse from Assignment 1**: `../Assignment01_Basic_MatMul_Languages/` — the validated naive implementation,
  input generator, CSV schema and analysis style. Copy what you reuse into this folder (self-contained submission)
  and record the source path + A1 git commit. If A1 is not finished, implement an equivalent naive baseline here,
  validate it and note the situation in `docs/DECISIONS.md` (do not wait for the other agent).
- Assignments 3 and 4 will reuse your **best sequential dense kernel** as their sequential baseline: keep it clean in
  `src/` with a clear interface.

## Open decisions to ask Daniel at the start (one grouped question, recommended option first)
1. Language (rec. **C**, reusing A1's C baseline; alt. Java).
2. Optimisations (rec. **loop reordering ikj + cache blocking**; optional Strassen if time allows).
3. Sparse format (rec. **CSR + own Gustavson SpGEMM**; SciPy only as correctness reference).
4. Budgets: max runtime per run (rec. 600 s), total benchmark time (rec. ≤ 3 h), memory (rec. 8 GB).
5. Allow hardware counters? (needs Daniel to run `! sudo sysctl -w kernel.perf_event_paranoid=1`).
6. GitHub repository name (rec. `bigdata-assignment02-optimised-sparse`).

## Required deliverables (this folder)
- `deliverables/Assignment02_RodriguezAlonso_Report.pdf` — title suggestion (adapt once results exist):
  *"Cache-Aware Optimisation of Dense Matrix Multiplication and the Density Threshold for Sparse CSR Multiplication"*
- `deliverables/Assignment02_RodriguezAlonso_Materials.zip` + local git repo ready to push.
- `docs/defensa_oral.md` (Spanish) for the oral explanation.

## Folder layout
`src/c/{baseline,dense,sparse}/` · `tests/` · `scripts/` (gen_inputs dense+sparse, run_experiments) · `configs/` ·
`data/inputs/` · `results/{raw,summary}/` · `analysis/` · `report/` · `docs/` · `deliverables/`

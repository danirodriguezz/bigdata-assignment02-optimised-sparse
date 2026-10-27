# Progress / handoff — Assignment 02

**Stopped:** 2026-10-27T23:05 (local machine time), at Daniel's request (via coordinator).
**No process of this assignment is running**: the pilot finished by itself (all 22 sparse-pilot and 12 dense-pilot
configurations rc=0) and nothing else was launched. The full benchmark has **not** started.

## Phase reached: 3 (pilot) done; ready to start phase 4 (full benchmark)
| Phase | State |
|---|---|
| 0 Orientation | Done. `results/environment.md` captured (i7-9750H, 6C/12T, 15 GiB, Ubuntu 24.04, gcc 13.3, powersave + turbo, AC on). Decisions in `docs/DECISIONS.md` (from Daniel / delegated). A1 had **no C code yet** (`../Assignment01_Basic_MatMul_Languages/src/` empty at 22:40), so the naive baseline was implemented here (`src/c/baseline/matmul_naive.c`). |
| 1 Plan | Done: `docs/experiment_plan.md` (RQs, H1–H4, methods, inputs, boundaries, budgets, block-size rule). |
| 2 Implement | Done and validated. `make build` clean (-Wall -Wextra). `make test` → 286 checks PASS, max error/bound 0.30 (`results/correctness_summary.json`). |
| 3 Pilot | Done: `results/raw/pilot_*.csv` (1 rep, no warm-up). Logs in `results/logs/pilot_*.log` (git-ignored). |
| 4 Benchmark | **Pending** (not started). |
| 5 Analysis | `analysis/make_all.py` **written but never executed** (untested; expect small bugs). `analysis/plot_style.py`, `analysis/summarize.py` copied from the skill. |
| 6 Report | Not started (`report/main.tex` is still the template). References verified so far (Crossref/web): Gustavson 1978 (10.1145/355791.355796), Lam et al. 1991 (10.1145/106972.106981), Goto & van de Geijn 2008 (10.1145/1356052.1356053, TOMS 34(3) 1–25), Buluç & Gilbert 2012 (10.1137/110848244), Strassen 1969 (10.1007/BF02165411), Higham 2002 (10.1137/1.9780898718027), Saad 2003 (10.1137/1.9780898718003), Virtanen 2020 (10.1038/s41592-019-0686-2), Hoefler & Belli 2015 (10.1145/2807591.2807644, pp. 1–12), Mytkowicz 2009 (10.1145/1508244.1508275, pp. 265–276), Williams 2009 Roofline (10.1145/1498765.1498785), Hennessy & Patterson 6th ed. 2017 (ISBN 978-0-12-811905-1), GCC 12 release notes (vectorisation enabled at -O2, very-cheap cost model: https://gcc.gnu.org/gcc-12/changes.html). `report/references.bib` is still empty. |
| 7 Review/package | Not started. |

## Pilot observations (single repetitions, for planning only, not results)
- n=1024: naive ≈ 1.8 s (1.2 GFLOP/s), ikj ≈ 0.64 s, blocked b=64 ≈ 0.85 s; block sizes 16/64/256 within ~10 %.
- n=2048 sparse: SpGEMM still faster than dense at d=50 % (3.6 s vs ≈5 s) → density grid extended to 100 %.
  Banded vs uniform at d=1 %: same flops (8.6e5) but 2.1 ms vs 14.3 ms; nnz(C) 83k vs 777k.
- Dense times at n=2048 varied 4.6–6.8 s for identical work: noise from the other agents (loadavg up to ~7).
- Lock waits are long (other agents benchmarking): the pilot took 14 min wall for ~1–2 min of own locked time.

## Files
- Done: `src/c/{common,baseline,dense,sparse}/*`, `src/c/bench_dense.c`, `src/c/bench_sparse.c`, `Makefile`,
  `scripts/gen_inputs.py`, `scripts/run_experiments.py` (now wraps each run in `prlimit --as=8 GiB`; this
  change has not been exercised yet), `tests/test_correctness.py`, `configs/pilot.json`, `configs/experiment.json`,
  `docs/experiment_plan.md`, `.gitignore` (+ *.f64, *.coo, results/logs/).
- Unfinished: `analysis/make_all.py` (never run), `README.md` (template), `report/main.tex` (template),
  `results/README.md` (needs a note on extra_json keys and timer boundaries), `docs/DECISIONS.md` (add: A1 not
  available → own baseline; C/-O2; methods; CSR+Gustavson; block-size rule; densities extended to 100 %;
  in-process reps; prlimit memory enforcement).
- Not yet created: `docs/OPEN_QUESTIONS.md`, `docs/review_checklist.md`, `docs/defensa_oral.md`, `report/references.bib` entries.

## Next steps to resume (exact commands, from the assignment folder)
```bash
cd /home/daniel/Documentos/Universidad/4Year/Big_Data/Teoria/Assigments/Assignment02_Optimised_and_Sparse
make build && make test                       # should print ALL CORRECTNESS TESTS PASSED
.venv/bin/python scripts/run_experiments.py --config configs/experiment.json --dry-run | head   # check prlimit wrapper
bash .claude/skills/benchmark-protocol/scripts/capture_env.sh results/environment.md
nohup .venv/bin/python scripts/run_experiments.py --config configs/experiment.json > results/logs/full.log 2>&1 &
# estimated own locked time ≈ 50 min (budget 90); wall time longer because of the shared lock
.venv/bin/python analysis/make_all.py --prefix pilot_   # debug the analysis on pilot data first
.venv/bin/python analysis/make_all.py                   # after the full run
```
Then write `report/main.tex` using `\val{...}` macros from `report/generated/numbers.tex`, fill `references.bib`
with the verified entries above, `make report`, run the report-review skill, write `docs/defensa_oral.md`,
`git commit`, `make package`.

## Open questions for Daniel
1. Confirm the "Use of Generative AI" statement once written (Claude Code by Anthropic, model Claude Opus 5.5:
   planning, C/Python code drafting, analysis scripts, LaTeX drafting).
2. Create the GitHub repo `bigdata-assignment02-optimised-sparse` and push (agent never pushes):
   `git remote add origin git@github.com:<user>/bigdata-assignment02-optimised-sparse.git && git push -u origin main`.
3. If A1 later publishes a validated naive C kernel, decide whether to cite it as equivalent (current baseline is
   self-implemented and validated here).
4. Optional: run the full benchmark when the other agents are idle, to reduce noise (loadavg recorded per row).

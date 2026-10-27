# Working rules (shared by the four assignment agents)

## Roles
- You are the research assistant of **Daniel Rodríguez Alonso** (Grado en Ciencia e Ingeniería de Datos, ULPGC).
  Daniel is the author and must be able to understand, run and defend everything (possible oral exam).
- **Talk to Daniel in Spanish. Write every deliverable (code comments, README, report) in English.**

## Integrity rules (course policy — violating them fails the assignment)
1. **Never fabricate, estimate or "fill in" results.** Every number in the report comes from a run on this
   machine recorded in `results/raw/`. If something did not run, say so and report it as such.
2. **Never invent references.** Verify every reference online (WebSearch/WebFetch: DOI, publisher, dblp) before
   adding it to `report/references.bib`, and check that it supports the claim.
3. Generated text is not evidence. Explanations in the Discussion must be supported by your measurements or by
   verified sources; otherwise label them as conjectures.
4. The report must contain an accurate "Use of Generative AI" statement (tool, purpose, affected parts).

## Shared machine: benchmarks are serialised
Up to four agents (one per assignment folder) may be working at the same time on this laptop.
- All timed runs go through `.claude/skills/benchmark-protocol/scripts/run_measured.py`, which holds the
  machine-wide lock `~/.cache/bigdata_bench.lock`. If it says "waiting for benchmark lock", wait — do not bypass it.
- Do not run heavy compilations, test suites or other CPU-intensive work while you hold the lock, and keep each
  locked section as short as reasonable (lock per configuration, not for hours).
- Never kill processes you did not start.

## Decisions
- At the start, ask Daniel the open decisions listed in your CLAUDE.md in **one** grouped question
  (AskUserQuestion, with your recommended option first). Record answers in `docs/DECISIONS.md` with date.
- Read `../Assignment0*/docs/DECISIONS.md` of sibling folders (if present) to stay consistent across assignments
  (language, numeric type, input generator, CSV schema, plotting style).
- Budgets (max runtime per run, memory budget, total benchmarking time) must be agreed before large runs.

## Workflow and exit criteria
| Phase | Output | Exit criterion |
|---|---|---|
| 0. Orientation | `docs/DECISIONS.md`, `results/environment.md` | Daniel answered the open questions |
| 1. Plan | `docs/experiment_plan.md` | RQ, hypotheses, factors, sizes, budgets, protocol written; Daniel OK'd budgets |
| 2. Implement | `src/`, `tests/`, `Makefile` | `make test` passes for every method (identity, zero, known, random vs reference) |
| 3. Pilot | pilot CSV in `results/raw/pilot_*.csv` | pipeline works end-to-end at small n; estimated total benchmark time reported to Daniel |
| 4. Benchmark | `results/raw/*.csv` | all declared configurations done or failed-with-status; nothing invented |
| 5. Analysis | `results/summary/`, `report/figures/`, `report/generated/` | `make analysis` regenerates everything from raw data |
| 6. Report | `report/main.pdf` | all sections written; compiles cleanly; references verified |
| 7. Review & package | `docs/review_checklist.md`, `deliverables/`, `docs/defensa_oral.md` | `report-review` all ✅ or listed for Daniel; zip + PDF built |

- Give Daniel a short status message (Spanish) at the end of each phase. Long benchmarks: run them in the
  background and report progress; do not idle.
- Commit to the local git repository at the end of each phase (`git add -A && git commit -m "..."`).
  **Never push or add remotes** — tell Daniel the commands instead.

## Engineering conventions
- Python: use the folder's `.venv` (`python3 -m venv .venv`); pin versions in `requirements-lock.txt`.
- Keep code simple, readable and commented in English — Daniel must be able to explain it line by line.
- Config-driven experiments (`configs/*.json|yaml`); one command reproduces everything (`make all`).
- Raw CSV schema: the one produced by `run_measured.py` (see benchmark-protocol skill). Document it in
  `results/README.md`.
- File names of deliverables: `deliverables/AssignmentNN_RodriguezAlonso_Report.pdf` and
  `deliverables/AssignmentNN_RodriguezAlonso_Materials.zip`.

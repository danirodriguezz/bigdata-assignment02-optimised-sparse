---
name: reproducibility-package
description: Build the reproducibility materials required by the ULPGC Big Data assignments — README with exact build/run commands, dependency and environment details, Makefile pipeline, raw data documentation, git repository, and the final AssignmentNN_RodriguezAlonso_Materials.zip. Use when setting up the project structure, when finishing the assignment, or when preparing the submission.
---

# Reproducibility package

## Target layout (already scaffolded in this folder)
```
AssignmentNN_.../
├── README.md                 # reproduction guide (templates/README_template.md)
├── Makefile                  # build / test / bench / analysis / report / package targets
├── requirements.txt          # Python deps (analysis, Python implementations)
├── src/                      # implementations (one sub-folder per language/framework)
├── tests/                    # correctness tests (must pass before benchmarking)
├── scripts/                  # input generation, run_experiments driver, env capture wrapper
├── configs/                  # experiment configuration (sizes, reps, budgets, threads/workers) as YAML/JSON
├── data/inputs/              # generated inputs (git-ignored if large) + checksums.sha256 (committed)
├── results/raw/              # raw CSVs (committed)  results/summary/ (generated)  results/environment.md
├── analysis/                 # scripts that produce tables/figures from results/raw
├── report/                   # main.tex, references.bib, figures/, generated/
├── docs/                     # experiment_plan.md, decisions, review checklist, defensa_oral.md
└── deliverables/             # final PDF + materials zip (git-ignored)
```

## Makefile contract
| Target | Does |
|---|---|
| `make setup` | create `.venv`, install `requirements.txt`, build Java/C code |
| `make test` | run correctness tests for every method (fails loudly) |
| `make inputs` | generate shared input files + checksums from `configs/` |
| `make bench` | full experiment via the driver (long; uses the machine-wide lock) |
| `make pilot` | quick end-to-end smoke run (small n, 1 rep) |
| `make analysis` | `results/raw` → `results/summary`, `report/figures`, `report/generated` |
| `make report` | compile the PDF and copy it to `deliverables/` |
| `make package` | build `deliverables/AssignmentNN_RodriguezAlonso_Materials.zip` |
| `make all` | setup test inputs bench analysis report package |

## README must contain (course requirement)
1. Title, author, assignment, research question (1–2 lines), link to the PDF.
2. Hardware/software used for the reported results (pointer to `results/environment.md`).
3. Dependencies with versions (gcc, JDK, Maven, Python + `requirements-lock.txt`, frameworks).
4. **Exact commands**: build, test, generate inputs, run experiments (and expected duration), analysis, report.
5. Configuration files and how to change sizes/reps/budgets/threads/workers.
6. Data: how inputs are generated (seed, generator) or obtained; raw CSV schema and units.
7. Reused materials: which earlier assignment, which files, which commit.
8. Repository layout and license (MIT suggested) + "Use of Generative AI" note (same as report).

## Git
- `git init` in this folder if not yet a repo (each assignment folder is its own repository).
  Commit at meaningful milestones with clear messages (implementation validated, benchmarks done, report draft…).
- Never commit `.venv/`, build outputs, large inputs (> 50 MB), `deliverables/`.
- **Do not create a remote or push without asking Daniel.** At the end, tell him the exact commands:
  `git remote add origin git@github.com:<user>/<repo>.git && git push -u origin main`, then put the URL in
  the README and the report, and tag the submitted version (`git tag -a v1.0-submission -m "..."`).

## Packaging
`bash .claude/skills/reproducibility-package/templates/package.sh NN` builds the zip from tracked files
(`git archive`), so what is in the zip is exactly what is in the repository. Check its size and list its contents.

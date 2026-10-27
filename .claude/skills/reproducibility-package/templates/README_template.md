# Assignment NN — <Research title>

**Author:** Daniel Rodríguez Alonso · Grado en Ciencia e Ingeniería de Datos · ULPGC
**Course:** Big Data, academic year 2026–2027 · **Report:** `deliverables/AssignmentNN_RodriguezAlonso_Report.pdf`

**Research question.** <one or two lines>

## 1. Environment used for the reported results
See `results/environment.md` (captured automatically). Summary: <CPU, cores/threads, RAM, OS, compilers/runtimes>.

## 2. Dependencies
| Tool | Version | Notes |
|---|---|---|
| gcc | | flags: |
| OpenJDK / Maven | | JVM flags: |
| Python | | packages pinned in `requirements-lock.txt` |
| <framework> | | |

## 3. Reproduce
```bash
make setup      # venv + builds
make test       # correctness tests (must pass)
make inputs     # shared inputs + checksums (seed ...)
make pilot      # optional smoke test (~1 min)
make bench      # full experiments (~<duration> on the machine above)
make analysis   # tables + figures from results/raw
make report     # PDF -> deliverables/
```
Configuration: `configs/<file>` (sizes, repetitions, warm-ups, budgets, threads/workers).

## 4. Data
- Inputs: <generator, distribution, range, dtype, seeds>; checksums in `data/inputs/checksums.sha256`.
- Raw results: `results/raw/*.csv` — schema documented in `results/README.md` (seconds, KiB, bytes).

## 5. Reused materials
<earlier assignment, files, repository + commit> (or "none").

## 6. Repository layout
<tree>

## 7. Use of Generative AI
<same statement as in the report>

## License
MIT

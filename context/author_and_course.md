# Author and course

| Field | Value |
|---|---|
| Author | Daniel Rodríguez Alonso |
| Degree | Grado en Ciencia e Ingeniería de Datos (Bachelor's Degree in Data Science and Engineering) |
| University | Universidad de Las Palmas de Gran Canaria (ULPGC) |
| Course | Big Data — 4th year |
| Academic year | 2026-2027 |
| Report language | **English** (all deliverables) |
| Conversation language with Daniel | **Spanish** |
| Surname token for file names | `RodriguezAlonso` (no accents, no spaces) |

## File naming convention (suggested by the course)

- Report: `AssignmentNN_RodriguezAlonso_Report.pdf`
- Materials: `AssignmentNN_RodriguezAlonso_Materials.zip`
- A public or private Git repository (e.g. GitHub) is **mandatory**. The URL goes in the report
  (section "References and materials") and in the README.

## Author block for the LaTeX report

```latex
\author{\IEEEauthorblockN{Daniel Rodríguez Alonso}
\IEEEauthorblockA{Grado en Ciencia e Ingeniería de Datos\\
Universidad de Las Palmas de Gran Canaria (ULPGC)\\
Big Data, Academic Year 2026--2027}}
```

The report title page must show: **name, assignment number and research title**.

## Reference machine (detected when these folders were created, 2026-10-27)

Always re-capture with `.claude/skills/benchmark-protocol/scripts/capture_env.sh` — this is only a hint.

- CPU: Intel Core i7-9750H @ 2.60 GHz, 1 socket, 6 physical cores / 12 logical (Hyper-Threading), AVX2 + FMA
- RAM: ~15 GiB
- OS: Ubuntu 24.04 (Linux kernel 7.x), CPU governor `powersave` by default (laptop: watch thermal throttling, plug in AC power)
- Toolchain: gcc 13.3, OpenJDK 21, Maven 3.8.7, Python 3.12.3 (no numpy/matplotlib system-wide → use a venv), Docker available,
  `perf` available, `/usr/bin/time` available
- Not installed: clang, MPI, Spark, hyperfine, valgrind, gh
- LaTeX: TinyTeX with IEEEtran, booktabs, siunitx, subcaption, cleveref, listings, microtype, hyperref

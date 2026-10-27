# Common experimental protocol (applies to all four assignments)

Source: *BD_Individual_Assignments_2026_2027.pdf*, pages 1–3 (Big Data, ULPGC, 2026-2027).
This is a faithful transcription; the original PDF is in this folder. When in doubt, the PDF wins.

## Purpose
Four individual empirical studies of matrix multiplication. Each study must begin with a focused
research question, use controlled measurements, and draw conclusions supported by the observed
results. The goal is to understand performance and scalability and to communicate a reproducible
investigation. Benchmarking measures and compares implementations under specified conditions.
The assignments examine execution time and memory use, then extend the investigation to
optimisation, sparse representations, parallel execution and distributed execution.

| Assignment | Submission week | 2026 date window |
|---|---|---|
| 1. Basic implementations in Python, Java and C | Week 6 | 12–16 October |
| 2. Optimised approaches and sparse matrices | Week 8 | 26–30 October |
| 3. Parallel multiplication; optional vectorisation | Week 10 | 9–13 November |
| 4. Distributed multiplication | Week 12 | 23–27 November |

These are submission windows, not exact deadlines.

## How the assignments connect
Reuse validated implementations and experimental scripts across stages. **Each submission must remain
understandable on its own and identify the earlier implementation or dataset it reuses.** The number of
required methods is specified in each assignment; there is no blanket three-method requirement.

## 1. Define the question and comparison
State what you will investigate, the factor you will change, and the outcome you will measure
(e.g. "How does matrix size affect runtime and memory use for the three basic implementations?").
Define **n as the side length of an n × n square matrix**. **Distinguish hypotheses or predictions from results.**

## 2. Control the inputs and environment
- Use the same logical input matrices across methods for each comparison. Record the random seed,
  generator, value range, dimensions and numeric type. Cross-language random generators may differ,
  so **a shared input file or a verified common generator is preferable**.
- Document CPU model, physical cores and logical processors, RAM, OS, language and library versions,
  compiler flags, and relevant runtime settings. Record thread counts, including threads that numerical
  libraries create internally.
- Keep the algorithm and arithmetic comparable when the comparison requires it. Report unavoidable
  differences in storage or runtime behaviour. Do not treat different machines as an isolated comparison
  of programming languages.

## 3. Define what the timer includes
State whether you measure the multiplication **kernel** or the **whole application**. For kernel
measurements, generate inputs outside the timed region. Explain whether allocation and output
initialisation are included. For end-to-end measurements, specify data loading, setup, transfers and
result collection. **Never combine different timing boundaries in one unqualified comparison.**

## 4. Repeat and summarise
- Use a benchmarking tool or a documented timing harness. Use a **monotonic timer** and ensure the
  computation actually executes and its result is consumed or checked (no dead-code elimination).
- Use warm-up runs when JIT compilation, caching or framework startup can affect the measurement.
  Exclude warm-up runs from reported samples and **record their number**.
- Recommended: **at least five measured repetitions per configuration**. Justify fewer repetitions for
  costly runs and report the resulting uncertainty. Very short tasks may require repeated batches with a
  clearly reported time per multiplication.
- **Keep every raw measurement.** Report a central measure, preferably the **median**, and variability,
  such as the **interquartile range (IQR)**. Include units and number of repetitions. Explain exclusions
  rather than removing inconvenient observations.

## Correctness, resources and reproducibility

### Validate before benchmarking
Test small matrices with known answers, including **identity and zero matrices**. Compare results
against a trusted reference implementation. A reference library used for checking does not count as a
required student implementation. For floating point, **define absolute and relative tolerances and
justify them** (different evaluation orders give small differences). For integers, consider overflow and
document the value range.

### Choose feasible sizes
Begin with small correctness tests, then increase n using a **declared size sequence**. 10, 100, 1000 are
examples, not targets. Add sizes that reveal a trend and stop when the declared time or memory budget
is reached. A dense n × n float64 matrix needs 8n² bytes; at n = 10 000, three matrices ≈ 2.4 GB before
overheads (planning aid only).

**Define a maximum runtime and a memory budget before large tests.** State the **largest tested size
that meets those limits, separately from the largest size attempted.** Report timeouts and memory
failures as results with their limits; **never assign them an invented execution time**.

### Memory and resource measurements
**Measure execution time and memory in every assignment.** Identify the memory metric and tool (peak
process resident memory, managed heap use, or an estimate of array storage). These quantities differ
and must not be compared as if identical. Report measurement limitations. CPU utilisation is optional
unless needed to explain a result.

### Make the study reproducible
- Source code, a README with exact build and run commands, dependency versions and configuration
  files. Explain how to regenerate datasets or obtain shared inputs.
- Raw measurements as CSV (or another documented machine-readable format), plus scripts/notebooks
  that generate the tables and plots.
- Label every configuration with matrix size, method, numeric type, repetition and relevant thread or
  worker count. For sparse tests, include density and representation.

Keep each study small enough to complete and inspect carefully. **A defensible controlled comparison is
the core requirement**; an inaccessible large configuration does not improve the investigation.

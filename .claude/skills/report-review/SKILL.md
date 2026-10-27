---
name: report-review
description: Final quality gate for a Big Data assignment submission — checks the PDF report and materials against the course rubric (correctness, experimental design, analysis, reproducibility, communication), the mandatory section structure, number traceability, verified references and the AI disclosure. Use before declaring the assignment finished or when Daniel asks for a review.
---

# Report review (rubric gate)

Run this as a critical reviewer, not as the author. Produce `docs/review_checklist.md` with every item marked
✅ / ❌ (+ fix applied or reason). Fix every ❌ that you can; list what needs Daniel's input.

## A. Mandatory structure (`context/report_requirements.md`)
- [ ] Title page: Daniel Rodríguez Alonso, assignment number, research title.
- [ ] Abstract states question, method, main result **with variability**, scope.
- [ ] Introduction has one focused RQ, factor varied, outcome measured, labelled hypotheses.
- [ ] Background: every technique explained is cited.
- [ ] Methodology covers implementations, inputs, environment, correctness, protocol, **budgets**.
- [ ] Results: labelled tables/figures, units, k repetitions, variability, failures/timeouts as results.
- [ ] Discussion answers the RQ explicitly, verdict per hypothesis, explanations supported by evidence, limitations.
- [ ] Conclusions scoped to tested implementations/settings/hardware; unresolved questions stated.
- [ ] References (IEEE, consistent) + Reproducibility Materials (repo URL + commit/tag) + Use of Generative AI.

## B. Assignment-specific requirements
- [ ] Every bullet of "Required implementations", "Required evidence/Metrics" and "Analysis expected" in
      `context/assignment_brief.md` is satisfied and you can point to the section/figure where it is.

## C. Experimental design & correctness (protocol)
- [ ] Same logical inputs across methods; seed, generator, range, numeric type documented.
- [ ] Environment fully documented (CPU, cores/threads, RAM, OS, versions, flags, thread settings).
- [ ] Timing boundary stated; never mixed in one comparison; inputs generated outside kernel timing.
- [ ] Warm-ups (number) excluded; ≥ 5 measured reps or justified; median + IQR reported.
- [ ] Memory measured in every configuration with a **named metric and tool**; metrics not mixed.
- [ ] Correctness tests (identity, zero, known, vs reference) with tolerances justified; results reported.
- [ ] Largest tested feasible size vs largest attempted size, with budgets; timeouts/OOM not given invented times.

## D. Integrity (zero tolerance)
- [ ] Every number in the PDF traces to `results/` (spot-check ≥ 10 numbers against the CSVs; list them).
- [ ] No placeholder or `\todo` left: `grep -n "TODO\|todo{\|XX\|??" report/main.tex` and check the PDF text
      (`pdftotext report/main.pdf - | grep -n "TODO\|??"`).
- [ ] Every reference verified (exists, metadata correct, supports the claim). Remove any you cannot verify.
- [ ] AI disclosure present, specific and confirmed by Daniel.
- [ ] No claim of universality ("language X is faster") — all conclusions scoped.

## E. Communication
- [ ] Figures: axis labels with units, legends naming configurations, readable at print size, caption explains
      statistic/k/boundary; colour-blind safe; referenced in text.
- [ ] English: clear, concise, consistent tense and terminology; defined abbreviations; no typos
      (read the extracted text once fully).
- [ ] 5–8 pages main body; LaTeX log free of errors, undefined references and large overfull boxes.

## F. Reproducibility package
- [ ] README with exact build/run/analysis commands, dependency versions, hardware used, expected runtime.
- [ ] `make all` (or the documented commands) regenerates results → summary → figures → PDF (test the analysis +
      report part from scratch; full benchmark re-run not required during review).
- [ ] Raw CSVs present with documented schema; input generation instructions/checksums present.
- [ ] Reused materials from earlier assignments identified with exact version (path + commit).
- [ ] `deliverables/AssignmentNN_RodriguezAlonso_Report.pdf` and `..._Materials.zip` built; zip excludes
      `.venv`, build outputs and huge input files.
- [ ] Git repository initialised, everything committed; remote URL present (ask Daniel to create/push).

## G. Oral defence readiness
- [ ] `docs/defensa_oral.md` (Spanish) exists: RQ, why the comparison is fair, 3 key results, limitations,
      how to run one experiment live, likely questions with short answers, and a walkthrough of the code.

# Review checklist — Assignment 02 (report-review gate, 2026-10-29)

Reviewed as a critical reader against `context/report_requirements.md`, `context/assignment_brief.md` and the
common protocol. ✅ = satisfied (where in the report); 🔧 = was ❌, fixed during review; 👤 = needs Daniel.

## A. Mandatory structure
- ✅ Title page: name, "Individual Assignment 02", research title.
- ✅ Abstract: question, method, main result with 95 % CI, scope sentence.
- ✅ Introduction: RQ-A / RQ-B, factors and outcomes, H1–H4 labelled as predictions written before the run.
- ✅ Background: blocking (Lam), library kernels (Goto), roofline (Williams), Strassen, CSR (Saad), Gustavson,
  SpGEMM fill-in (Buluç), benchmarking (Hoefler, Mytkowicz), gcc -O2 vectoriser (GCC 12 notes) — all cited.
- ✅ Methodology: implementations, inputs, Table I environment, correctness, protocol, budgets (600 s, 8 GiB, 90 min).
- ✅ Results: Tables II–V, Figs. 1–7, units, k, IQR / bootstrap CI; naive n=4096 timeout reported as a result.
- ✅ Discussion: explicit answers to RQ-A and RQ-B; verdicts H1 supported, H2 partly supported, H3 supported,
  H4 supported; conjectures labelled; Limitations subsection.
- ✅ Conclusions scoped to machine/compiler/inputs; unresolved questions listed.
- ✅ IEEE references (14, IEEEtran), Reproducibility Materials (repo URL + tag `a2-submission`), Use of Generative AI.

## B. Assignment-specific requirements (brief → location)
- ✅ One validated baseline + ≥ 2 optimised versions → naive_ijk, reorder_ikj, blocked_ikj (§III-A).
- ✅ Actual change and expected effect of each optimisation identified (§II, §III-A); no SIMD verified in assembly.
- ✅ Same inputs, numeric type, timing boundary; sequential (§III-B, §III-E).
- ✅ Sparse approach + storage format + own code vs library identified (§III-A: own CSR + Gustavson; SciPy only reference).
- ✅ Multiple declared sparsity levels; density/sparsity defined as % nonzero / % zero (§I); generation, distribution, seeds (§III-B).
- ✅ Sparse vs dense on matched logical inputs (Table IV, Fig. 4).
- ✅ Conversion costs measured separately and added explicitly (§III-E, Table IV).
- ✅ Input and output nnz reported (Tables IV, V; Fig. 5).
- ✅ Time and memory with repeated measurements (Tables III–V, Fig. 6).
- ✅ Largest feasible tested size under budget (§IV-B: naive 3072, optimised 4096; sparse 32768 at 0.1 %).
- ✅ Observed bottlenecks (§V: strided access/memory-bound baseline, B leaving L3, per-row overheads, fill-in).
- ✅ Optimisation effects discussed separately from sparse-storage/structure effects (§V "Optimisation vs storage").
- ✅ Where sparse helps and where indexing/conversion/output costs reduce it (§V H4 paragraph).
- ✅ No claim that % zeros alone determines performance (explicitly argued against in §V).

## C. Experimental design & correctness
- ✅ Byte-identical shared inputs; generator PCG64, seeds, U[-1,1), float64; regeneration checked on 2026-10-29
  (SHA-256 of a regenerated dense and a regenerated banded input match `checksums.sha256`).
- ✅ Environment: CPU, caches, RAM, OS, gcc + flags, single thread, governor/turbo, AC power, Python libs.
- ✅ Timing boundaries defined and never mixed; input loading/generation outside timers.
- ✅ 1 warm-up excluded, k = 5 (k = 3 for n ≥ 3072, declared in advance and justified); median + IQR.
- ✅ Memory in every configuration: peak RSS (GNU time) + analytical storage model; never mixed.
- ✅ Correctness tests: identity, zero, known 2×2/3×3, empty rows/cols, NumPy/SciPy references; Higham bound
  justified; max error 0.30 of the bound; all pass.
- ✅ Largest attempted vs completed sizes; timeout row carries no time; dense n = 32768 (24 GiB) declared not attempted.

## D. Integrity
- ✅ 12 numbers spot-checked directly against `results/raw/*.csv` (not the summaries), all match:
  naive n=2048 39.2 s; blocked n=4096 29.7 s; ikj n=4096 46.5 s; blocked speedup n=3072 12.0×; naive GFLOP/s
  n=3072 0.340; naive n=4096 timeout with no time; RSS n=4096 386 MiB; SpGEMM uniform 50 % 3.27 s; dense/SpGEMM
  uniform 100 % 0.298; nnz(C) uniform/banded at 2 % 13.7×; SpGEMM RSS uniform 1 % 12.1 MiB; scaling uniform 1 %
  n=16384 4.71 s / 2579 MiB.
- ✅ All numbers in Results/Discussion come from `\val{}` macros of `analysis/make_all.py`, except range
  statements derived from tables (checked by hand: 3.5–3.7 / 2.9 GFLOP/s, 11–48 ms / 1–6 ms conversions,
  1.2–1.5 ns, 4–7 ns, up to 15 % between-process spread, ~20 % / ~10 % throughput loss).
- 🔧 Placeholders: commit TODO replaced by git tag; `pdftotext | grep TODO|??` → none.
- ✅ 14 references re-verified on api.crossref.org (DOIs) / official page (GCC 12 notes, ISBN for H&P).
- ✅ AI disclosure confirmed by Daniel (2026-10-29).
- ✅ All conclusions scoped ("on this machine", "at n = 2048", "for the tested patterns").
- 🔧 Plan claimed i-k-j is auto-vectorised at -O2: false (assembly); corrected in plan, report, oral notes.
- 🔧 Blocked-vs-ikj gain at n=256 (single tile) is not a cache effect: reported as such, H2 only partly supported.

## E. Communication
- 🔧 Figures: legends overlapping data (GFLOP/s, memory, block sweep, scaling) and a literal `\%` fixed; all
  axes labelled with units; captions state statistic, k, boundary; Okabe–Ito palette + markers/line styles.
- 🔧 Abbreviations SpGEMM, CI (abstract), COO, GFLOP/s defined at first use.
- ✅ 8 pages incl. references (main text ends on p. 8); log: no errors, no undefined refs/citations.
- 🔧 Overfull boxes (Table V 23 pt, Table I 7 pt) removed.

## F. Reproducibility package
- ✅ README: exact commands, versions, hardware, expected runtime, data description, AI statement.
- ✅ `rm -rf report/figures/* report/generated/* results/summary/*; make analysis; make report` regenerates
  everything from raw data (tested 2026-10-29).
- ✅ Raw CSVs + schema (`results/README.md`), input sidecars + checksums.
- ✅ Reused materials: none (own baseline); A1's later equivalent kernel cited with commit `dfb18bf`; course
  harness scripts included under `.claude/skills/`.
- ✅ Deliverables built from the committed tree (`make package`, `git archive` → excludes .venv, build/, binary inputs).
- 👤 Push: remote not added by the agent (working rules). Daniel runs the commands in the final message.

## G. Oral defence
- ✅ `docs/defensa_oral.md` (Spanish): RQ, fairness, code walkthrough, validation, protocol, key results with
  numbers, limitations, likely questions, one live command.

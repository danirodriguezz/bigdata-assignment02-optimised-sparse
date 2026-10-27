# Assignment 2 — Optimised Matrix Multiplication Approaches and Sparse Matrices

Source: *BD_Individual_Assignments_2026_2027.pdf*, page 5 (transcribed). Submission window: **Week 8, 26–30 October 2026**.

## Research objective
Investigate two questions: **how selected optimisations affect dense multiplication**, and **under which tested
sparsity conditions a sparse representation offers an advantage**.

## Part A: dense optimisation
- Use **one validated basic implementation as the baseline**. Implement **at least two distinct optimised
  versions**, giving **at least three dense methods** in total.
- Possible techniques include cache blocking, loop reordering, loop unrolling, or an algorithmic approach such as
  Strassen. **Identify the actual change and explain its expected effect.** These are examples, not compulsory.
- Compare the baseline and both optimised methods with the **same input matrices, numeric type and timing
  boundary**. Keep the comparison **sequential** unless a parallel variant is explicitly identified and analysed
  separately.

## Part B: sparse matrices
- Implement a sparse multiplication approach. **State the storage format** (CSR, COO or another documented
  representation), and **identify your own code and any library functionality**.
- Test **multiple declared sparsity levels**. Define **sparsity as the percentage of zero entries** and **density as
  the percentage of nonzero entries**. Record the input generation process, nonzero distribution and seeds.
- For matched logical inputs, **compare the sparse approach with a dense method**. Specify whether **conversion
  costs** are excluded, included, or measured separately. **Report input and output nonzero counts** because the
  product can become denser.

## Required evidence and analysis
Report **time and memory** with repeated measurements, the **largest feasible tested size** under the declared
budget, and **observed bottlenecks**. Discuss the **effects of optimisation separately from the effects of sparse
storage and input structure**.

Identify where sparse multiplication helps in your experiments and where its **indexing, conversion or output costs
reduce the advantage**. **Do not claim that a percentage of zeros alone determines performance in every case.**

## Submission
Research report, implementations, input configurations and raw measurements (see `report_requirements.md`).

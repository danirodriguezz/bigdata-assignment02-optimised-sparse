/*
 * matmul_dense.h -- sequential dense matrix multiplication kernels (Assignment 2).
 *
 * All kernels compute C = A * B for square n x n matrices of float64 stored in
 * row-major order (element (i, j) at index i*n + j). C is overwritten; it does not
 * need to be initialised by the caller. A, B and C must not overlap.
 *
 * This header is the reusable interface for Assignments 3 and 4: the best sequential
 * kernel measured in Assignment 2 is matmul_blocked_ikj() with the block size chosen
 * by the block-size study (see docs/DECISIONS.md).
 */
#ifndef MATMUL_DENSE_H
#define MATMUL_DENSE_H

#include <stddef.h>

/* Baseline: classical triple loop, order i-j-k, scalar accumulator per C(i, j).
 * The inner loop walks a column of B with stride n (cache-unfriendly for large n). */
void matmul_naive_ijk(int n, const double *restrict A, const double *restrict B,
                      double *restrict C);

/* Optimisation 1 -- loop reordering i-k-j: C(i, :) += A(i, k) * B(k, :).
 * The inner loop has unit stride on B and C. Same arithmetic, different order. */
void matmul_reorder_ikj(int n, const double *restrict A, const double *restrict B,
                        double *restrict C);

/* Optimisation 2 -- cache blocking (tiling) of the i, k and j loops into bs x bs tiles,
 * with the i-k-j order inside each tile. bs need not divide n (edge tiles are smaller). */
void matmul_blocked_ikj(int n, int bs, const double *restrict A, const double *restrict B,
                        double *restrict C);

#endif /* MATMUL_DENSE_H */

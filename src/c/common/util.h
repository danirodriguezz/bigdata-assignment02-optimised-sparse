/*
 * util.h -- timer and input/output helpers shared by the benchmark programs.
 *
 * File formats (all little-endian, written by scripts/gen_inputs.py):
 *   dense  (.f64): n*n float64 values, row-major, no header (n is given on the command line)
 *   sparse (.coo): int64 n, int64 nnz, int32 rows[nnz], int32 cols[nnz], float64 vals[nnz],
 *                  sorted by (row, col), no duplicates
 */
#ifndef UTIL_H
#define UTIL_H

#include <stdint.h>
#include <stddef.h>

/* Monotonic clock in seconds (clock_gettime(CLOCK_MONOTONIC)). */
double now_s(void);

/* 64-byte aligned allocation of count doubles, touched (zeroed) so pages are resident. */
double *alloc_doubles(size_t count);

/* Read a dense n x n float64 file; returns NULL on error (message on stderr). */
double *read_dense(const char *path, int n);

/* Write count doubles to path (used by the correctness tests). */
int write_doubles(const char *path, const double *x, size_t count);

/* Read a COO file; arrays are malloc'ed. Returns 0 on success. */
int read_coo(const char *path, int64_t *n, int64_t *nnz, int32_t **rows, int32_t **cols,
             double **vals);

/* Sum of all entries (consumes the result so the kernel cannot be eliminated). */
double checksum(const double *x, size_t count);

#endif /* UTIL_H */

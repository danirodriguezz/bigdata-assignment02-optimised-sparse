/*
 * csr.h -- Compressed Sparse Row (CSR) matrices and Gustavson's row-wise SpGEMM (own code).
 *
 * Storage of an n x n CSR matrix with nnz stored entries:
 *   row_ptr[n + 1]  int64  -- entries of row i are at positions row_ptr[i] .. row_ptr[i+1]-1
 *   col_idx[nnz]    int32  -- column index of each stored entry
 *   val[nnz]        double -- value of each stored entry
 * Storage model: 8*nnz + 4*nnz + 8*(n+1) bytes (see csr_bytes()).
 */
#ifndef CSR_H
#define CSR_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    int n;            /* square matrix side */
    int64_t nnz;      /* number of stored entries */
    int64_t *row_ptr; /* n + 1 */
    int32_t *col_idx; /* nnz */
    double *val;      /* nnz */
} csr_t;

/* Free the arrays of a CSR matrix and reset it to an empty state. */
void csr_free(csr_t *M);

/* Analytical storage of the CSR arrays in bytes. */
size_t csr_bytes(const csr_t *M);

/* Build CSR from a dense row-major n x n matrix, keeping entries != 0.0.
 * Two passes: count nonzeros per row, then fill (columns sorted ascending). */
int csr_from_dense(int n, const double *D, csr_t *out);

/* Build CSR from COO triplets sorted by (row, col) with no duplicates. */
int csr_from_coo_sorted(int n, int64_t nnz, const int32_t *rows, const int32_t *cols,
                        const double *vals, csr_t *out);

/* Scatter a CSR matrix into a dense row-major n x n array (D is fully overwritten). */
void csr_to_dense(const csr_t *M, double *D);

/* Gustavson's SpGEMM: C = A * B for CSR A, B (C is allocated here).
 * Two-phase: (1) symbolic pass counts the distinct columns of every output row with a
 * marker array, so C is allocated exactly; (2) numeric pass accumulates a_ik * B(k, :)
 * into a dense accumulator of length n (sparse accumulator, SPA) and gathers the touched
 * columns. Output column indices of each row are in first-touch order (NOT sorted).
 * Structural nonzeros are kept even if a sum cancels to 0.0. Returns 0 on success. */
int spgemm_gustavson(const csr_t *A, const csr_t *B, csr_t *C);

/* Number of scalar multiply-add operations of A*B: sum over a_ik of nnz(B(k, :)). */
int64_t spgemm_flops(const csr_t *A, const csr_t *B);

#endif /* CSR_H */

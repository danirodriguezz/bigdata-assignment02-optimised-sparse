/*
 * csr.c -- CSR conversion routines and Gustavson's row-wise SpGEMM (own implementation).
 */
#include <stdlib.h>
#include <string.h>

#include "csr.h"

void csr_free(csr_t *M)
{
    free(M->row_ptr);
    free(M->col_idx);
    free(M->val);
    M->row_ptr = NULL;
    M->col_idx = NULL;
    M->val = NULL;
    M->nnz = 0;
}

size_t csr_bytes(const csr_t *M)
{
    return (size_t)M->nnz * (sizeof(double) + sizeof(int32_t)) +
           (size_t)(M->n + 1) * sizeof(int64_t);
}

/* allocate the three arrays; malloc(0) may return NULL, so allocate at least one element */
static int csr_alloc(csr_t *M, int n, int64_t nnz)
{
    M->n = n;
    M->nnz = nnz;
    M->row_ptr = malloc((size_t)(n + 1) * sizeof(int64_t));
    M->col_idx = malloc((size_t)(nnz > 0 ? nnz : 1) * sizeof(int32_t));
    M->val = malloc((size_t)(nnz > 0 ? nnz : 1) * sizeof(double));
    if (!M->row_ptr || !M->col_idx || !M->val) {
        csr_free(M);
        return -1;
    }
    return 0;
}

int csr_from_dense(int n, const double *D, csr_t *out)
{
    /* pass 1: count nonzeros per row -> row_ptr */
    int64_t *row_ptr = malloc((size_t)(n + 1) * sizeof(int64_t));
    if (!row_ptr)
        return -1;
    row_ptr[0] = 0;
    for (int i = 0; i < n; i++) {
        const double *Di = D + (size_t)i * n;
        int64_t c = 0;
        for (int j = 0; j < n; j++)
            c += (Di[j] != 0.0);
        row_ptr[i + 1] = row_ptr[i] + c;
    }
    const int64_t nnz = row_ptr[n];
    out->n = n;
    out->nnz = nnz;
    out->row_ptr = row_ptr;
    out->col_idx = malloc((size_t)(nnz > 0 ? nnz : 1) * sizeof(int32_t));
    out->val = malloc((size_t)(nnz > 0 ? nnz : 1) * sizeof(double));
    if (!out->col_idx || !out->val) {
        csr_free(out);
        return -1;
    }
    /* pass 2: copy column indices and values */
    for (int i = 0; i < n; i++) {
        const double *Di = D + (size_t)i * n;
        int64_t p = row_ptr[i];
        for (int j = 0; j < n; j++) {
            if (Di[j] != 0.0) {
                out->col_idx[p] = j;
                out->val[p] = Di[j];
                p++;
            }
        }
    }
    return 0;
}

int csr_from_coo_sorted(int n, int64_t nnz, const int32_t *rows, const int32_t *cols,
                        const double *vals, csr_t *out)
{
    if (csr_alloc(out, n, nnz) != 0)
        return -1;
    memset(out->row_ptr, 0, (size_t)(n + 1) * sizeof(int64_t));
    for (int64_t p = 0; p < nnz; p++)
        out->row_ptr[rows[p] + 1]++;
    for (int i = 0; i < n; i++)
        out->row_ptr[i + 1] += out->row_ptr[i];
    memcpy(out->col_idx, cols, (size_t)nnz * sizeof(int32_t));
    memcpy(out->val, vals, (size_t)nnz * sizeof(double));
    return 0;
}

void csr_to_dense(const csr_t *M, double *D)
{
    const int n = M->n;
    memset(D, 0, (size_t)n * n * sizeof(double));
    for (int i = 0; i < n; i++) {
        double *Di = D + (size_t)i * n;
        for (int64_t p = M->row_ptr[i]; p < M->row_ptr[i + 1]; p++)
            Di[M->col_idx[p]] = M->val[p];
    }
}

int64_t spgemm_flops(const csr_t *A, const csr_t *B)
{
    int64_t f = 0;
    for (int64_t p = 0; p < A->nnz; p++) {
        const int k = A->col_idx[p];
        f += B->row_ptr[k + 1] - B->row_ptr[k];
    }
    return f;
}

int spgemm_gustavson(const csr_t *A, const csr_t *B, csr_t *C)
{
    const int n = A->n;
    /* marker[j] == i means column j has already been touched while building row i */
    int32_t *marker = malloc((size_t)n * sizeof(int32_t));
    double *acc = malloc((size_t)n * sizeof(double)); /* dense accumulator (SPA values) */
    int64_t *row_ptr = malloc((size_t)(n + 1) * sizeof(int64_t));
    if (!marker || !acc || !row_ptr) {
        free(marker);
        free(acc);
        free(row_ptr);
        return -1;
    }
    for (int j = 0; j < n; j++) {
        marker[j] = -1;
        acc[j] = 0.0;
    }

    /* ---- phase 1 (symbolic): nnz of every output row ---- */
    row_ptr[0] = 0;
    for (int i = 0; i < n; i++) {
        int64_t count = 0;
        for (int64_t pa = A->row_ptr[i]; pa < A->row_ptr[i + 1]; pa++) {
            const int k = A->col_idx[pa];
            for (int64_t pb = B->row_ptr[k]; pb < B->row_ptr[k + 1]; pb++) {
                const int j = B->col_idx[pb];
                if (marker[j] != i) {
                    marker[j] = i;
                    count++;
                }
            }
        }
        row_ptr[i + 1] = row_ptr[i] + count;
    }
    const int64_t nnz = row_ptr[n];

    C->n = n;
    C->nnz = nnz;
    C->row_ptr = row_ptr;
    C->col_idx = malloc((size_t)(nnz > 0 ? nnz : 1) * sizeof(int32_t));
    C->val = malloc((size_t)(nnz > 0 ? nnz : 1) * sizeof(double));
    if (!C->col_idx || !C->val) {
        csr_free(C);
        free(marker);
        free(acc);
        return -1;
    }

    /* ---- phase 2 (numeric): scatter a_ik * B(k, :) into acc, then gather ---- */
    for (int j = 0; j < n; j++)
        marker[j] = -1;
    for (int i = 0; i < n; i++) {
        int64_t q = row_ptr[i];             /* next free slot of output row i */
        for (int64_t pa = A->row_ptr[i]; pa < A->row_ptr[i + 1]; pa++) {
            const int k = A->col_idx[pa];
            const double a = A->val[pa];
            for (int64_t pb = B->row_ptr[k]; pb < B->row_ptr[k + 1]; pb++) {
                const int j = B->col_idx[pb];
                if (marker[j] != i) {       /* first contribution to C(i, j) */
                    marker[j] = i;
                    C->col_idx[q++] = j;    /* record touched column */
                }
                acc[j] += a * B->val[pb];
            }
        }
        /* gather the touched columns and reset the accumulator for the next row */
        for (int64_t p = row_ptr[i]; p < row_ptr[i + 1]; p++) {
            const int j = C->col_idx[p];
            C->val[p] = acc[j];
            acc[j] = 0.0;
        }
    }
    free(marker);
    free(acc);
    return 0;
}

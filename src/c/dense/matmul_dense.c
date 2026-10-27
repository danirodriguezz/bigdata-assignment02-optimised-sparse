/*
 * matmul_dense.c -- optimised sequential dense kernels (loop reordering, cache blocking).
 * See matmul_dense.h for the interface contract.
 */
#include <string.h>

#include "matmul_dense.h"

void matmul_reorder_ikj(int n, const double *restrict A, const double *restrict B,
                        double *restrict C)
{
    memset(C, 0, (size_t)n * n * sizeof(double));      /* C accumulates partial sums */
    for (int i = 0; i < n; i++) {
        double *restrict Ci = C + (size_t)i * n;
        for (int k = 0; k < n; k++) {
            const double a = A[(size_t)i * n + k];     /* reused for the whole j loop */
            const double *restrict Bk = B + (size_t)k * n;
            for (int j = 0; j < n; j++)                /* unit stride on B and C */
                Ci[j] += a * Bk[j];
        }
    }
}

static inline int min_int(int a, int b) { return a < b ? a : b; }

void matmul_blocked_ikj(int n, int bs, const double *restrict A, const double *restrict B,
                        double *restrict C)
{
    memset(C, 0, (size_t)n * n * sizeof(double));
    for (int ii = 0; ii < n; ii += bs) {
        const int imax = min_int(ii + bs, n);
        for (int kk = 0; kk < n; kk += bs) {
            const int kmax = min_int(kk + bs, n);
            for (int jj = 0; jj < n; jj += bs) {
                const int jmax = min_int(jj + bs, n);
                /* one tile update: C[ii:imax, jj:jmax] += A[ii:imax, kk:kmax] * B[kk:kmax, jj:jmax]
                 * working set ~ 3 * 8 * bs^2 bytes, reused while it stays in cache */
                for (int i = ii; i < imax; i++) {
                    double *restrict Ci = C + (size_t)i * n;
                    for (int k = kk; k < kmax; k++) {
                        const double a = A[(size_t)i * n + k];
                        const double *restrict Bk = B + (size_t)k * n;
                        for (int j = jj; j < jmax; j++)
                            Ci[j] += a * Bk[j];
                    }
                }
            }
        }
    }
}

/*
 * matmul_naive.c -- baseline dense kernel (naive i-j-k triple loop).
 *
 * Provenance: Assignment 1 had no validated C implementation available when this file
 * was written (2026-10-27), so this equivalent naive kernel was implemented here and
 * validated with tests/test_correctness.py (see docs/DECISIONS.md).
 */
#include "../dense/matmul_dense.h"

void matmul_naive_ijk(int n, const double *restrict A, const double *restrict B,
                      double *restrict C)
{
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            double sum = 0.0;
            /* B is read down column j: consecutive k touch addresses 8n bytes apart */
            for (int k = 0; k < n; k++)
                sum += A[(size_t)i * n + k] * B[(size_t)k * n + j];
            C[(size_t)i * n + j] = sum;
        }
    }
}

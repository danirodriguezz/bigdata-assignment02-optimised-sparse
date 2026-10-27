/*
 * bench_sparse.c -- timing harness for Part B (sparse inputs).
 *
 * Usage:
 *   bench_sparse --mode spgemm|dense|convert --a A.coo --b B.coo [--bs 64]
 *                [--warmup 1] [--reps 5] [--dump C.f64]
 *
 * The same logical matrices (COO files) are used by all three modes. Loading the file and
 * building the input representation (CSR for spgemm, dense for dense/convert) is done
 * BEFORE any timer. Each mode runs in its own process so that its peak RSS reflects only
 * the data structures that mode needs.
 *
 *   spgemm  : timer_boundary "spgemm_kernel"   -- C = A*B with Gustavson's two-phase SpGEMM,
 *             CSR x CSR -> CSR, including the allocation of C (its size is only known after
 *             the symbolic phase). C is freed outside the timer between repetitions.
 *   dense   : timer_boundary "dense_kernel"    -- blocked i-k-j dense kernel (bs) on the
 *             densified matrices; C allocated outside the timer.
 *   convert : two boundaries per repetition, reported as separate rows:
 *             "convert_dense_to_csr" -- dense -> CSR of BOTH inputs A and B;
 *             "convert_csr_to_dense" -- CSR output C -> dense array (C computed untimed).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common/util.h"
#include "dense/matmul_dense.h"
#include "sparse/csr.h"

static void usage(void)
{
    fprintf(stderr, "usage: bench_sparse --mode spgemm|dense|convert --a A.coo --b B.coo "
                    "[--bs 64] [--warmup 1] [--reps 5] [--dump C.f64]\n");
    exit(2);
}

static int load_csr(const char *path, csr_t *M)
{
    int64_t n, nnz;
    int32_t *r, *c;
    double *v;
    if (read_coo(path, &n, &nnz, &r, &c, &v) != 0)
        return -1;
    int rc = csr_from_coo_sorted((int)n, nnz, r, c, v, M);
    free(r);
    free(c);
    free(v);
    return rc;
}

static double *load_dense_from_coo(const char *path, int *n_out, int64_t *nnz_out)
{
    int64_t n, nnz;
    int32_t *r, *c;
    double *v;
    if (read_coo(path, &n, &nnz, &r, &c, &v) != 0)
        return NULL;
    double *D = alloc_doubles((size_t)n * n);
    if (D)
        for (int64_t p = 0; p < nnz; p++)
            D[(size_t)r[p] * n + c[p]] = v[p];
    free(r);
    free(c);
    free(v);
    *n_out = (int)n;
    *nnz_out = nnz;
    return D;
}

static void emit(const char *boundary, double t, int r, int warmup, double cs, double mem,
                 const char *extra)
{
    printf("{\"time_s\": %.9f, \"timer_boundary\": \"%s\", \"repetition\": %d, \"is_warmup\": %s, "
           "\"checksum\": %.17g, \"memory_metric\": \"array_storage_estimate\", "
           "\"memory_bytes\": %.0f%s}\n",
           t, boundary, r < warmup ? r : r - warmup, r < warmup ? "true" : "false", cs, mem, extra);
    fflush(stdout);
}

int main(int argc, char **argv)
{
    const char *mode = NULL, *pa = NULL, *pb = NULL, *dump = NULL;
    int bs = 64, warmup = 1, reps = 5;
    for (int i = 1; i < argc; i++) {
        if (i + 1 >= argc)
            usage();
        if (!strcmp(argv[i], "--mode")) mode = argv[++i];
        else if (!strcmp(argv[i], "--a")) pa = argv[++i];
        else if (!strcmp(argv[i], "--b")) pb = argv[++i];
        else if (!strcmp(argv[i], "--bs")) bs = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--warmup")) warmup = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--reps")) reps = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--dump")) dump = argv[++i];
        else usage();
    }
    if (!mode || !pa || !pb || reps < 1 || warmup < 0 || bs <= 0)
        usage();
    char extra[512];

    if (!strcmp(mode, "spgemm")) {
        csr_t A = {0}, B = {0};
        if (load_csr(pa, &A) != 0 || load_csr(pb, &B) != 0) {
            fprintf(stderr, "Cannot allocate memory or read inputs\n");
            return 1;
        }
        const int n = A.n;
        const int64_t flops = spgemm_flops(&A, &B);   /* computed outside the timer */
        for (int r = 0; r < warmup + reps; r++) {
            csr_t C = {0};
            const double t0 = now_s();
            if (spgemm_gustavson(&A, &B, &C) != 0) {
                fprintf(stderr, "Cannot allocate memory for C\n");
                return 1;
            }
            const double t = now_s() - t0;
            const double cs = checksum(C.val, (size_t)C.nnz);
            /* storage of A, B, C in CSR + SPA workspace (marker int32[n] + acc double[n]) */
            const double mem = (double)(csr_bytes(&A) + csr_bytes(&B) + csr_bytes(&C)) + 12.0 * n;
            snprintf(extra, sizeof extra,
                     ", \"n\": %d, \"nnz_a\": %lld, \"nnz_b\": %lld, \"nnz_c\": %lld, "
                     "\"flops_madd\": %lld, \"csr_bytes_c\": %zu",
                     n, (long long)A.nnz, (long long)B.nnz, (long long)C.nnz, (long long)flops,
                     csr_bytes(&C));
            emit("spgemm_kernel", t, r, warmup, cs, mem, extra);
            if (dump && r == warmup + reps - 1) {
                double *D = alloc_doubles((size_t)n * n);
                csr_to_dense(&C, D);
                if (write_doubles(dump, D, (size_t)n * n) != 0)
                    return 1;
                free(D);
            }
            csr_free(&C);
        }
        csr_free(&A);
        csr_free(&B);
        return 0;
    }

    int n, nb;
    int64_t nnz_a, nnz_b;
    double *A = load_dense_from_coo(pa, &n, &nnz_a);
    double *B = load_dense_from_coo(pb, &nb, &nnz_b);
    if (!A || !B || nb != n) {
        fprintf(stderr, "Cannot allocate memory or read inputs\n");
        return 1;
    }
    const size_t nn = (size_t)n * n;

    if (!strcmp(mode, "dense")) {
        double *C = alloc_doubles(nn);
        if (!C) {
            fprintf(stderr, "Cannot allocate memory for C\n");
            return 1;
        }
        for (int r = 0; r < warmup + reps; r++) {
            const double t0 = now_s();
            matmul_blocked_ikj(n, bs, A, B, C);
            const double t = now_s() - t0;
            size_t nz = 0;                       /* output nonzeros, counted untimed */
            for (size_t p = 0; p < nn; p++)
                nz += (C[p] != 0.0);
            snprintf(extra, sizeof extra,
                     ", \"n\": %d, \"nnz_a\": %lld, \"nnz_b\": %lld, \"nnz_c_numeric\": %zu, "
                     "\"block_size\": %d",
                     n, (long long)nnz_a, (long long)nnz_b, nz, bs);
            emit("dense_kernel", t, r, warmup, checksum(C, nn), 3.0 * 8.0 * (double)nn, extra);
        }
        if (dump && write_doubles(dump, C, nn) != 0)
            return 1;
        free(C);
    } else if (!strcmp(mode, "convert")) {
        csr_t Cs = {0}, As0 = {0}, Bs0 = {0};
        /* reference C for the csr->dense conversion, computed untimed */
        if (csr_from_dense(n, A, &As0) != 0 || csr_from_dense(n, B, &Bs0) != 0 ||
            spgemm_gustavson(&As0, &Bs0, &Cs) != 0) {
            fprintf(stderr, "Cannot allocate memory\n");
            return 1;
        }
        csr_free(&As0);
        csr_free(&Bs0);
        double *Cd = alloc_doubles(nn);
        if (!Cd) {
            fprintf(stderr, "Cannot allocate memory\n");
            return 1;
        }
        for (int r = 0; r < warmup + reps; r++) {
            csr_t As = {0}, Bs = {0};
            double t0 = now_s();
            if (csr_from_dense(n, A, &As) != 0 || csr_from_dense(n, B, &Bs) != 0) {
                fprintf(stderr, "Cannot allocate memory\n");
                return 1;
            }
            double t = now_s() - t0;
            snprintf(extra, sizeof extra, ", \"n\": %d, \"nnz_a\": %lld, \"nnz_b\": %lld",
                     n, (long long)As.nnz, (long long)Bs.nnz);
            emit("convert_dense_to_csr", t, r, warmup,
                 checksum(As.val, (size_t)As.nnz) + checksum(Bs.val, (size_t)Bs.nnz),
                 2.0 * 8.0 * (double)nn + (double)(csr_bytes(&As) + csr_bytes(&Bs)), extra);
            csr_free(&As);
            csr_free(&Bs);

            t0 = now_s();
            csr_to_dense(&Cs, Cd);
            t = now_s() - t0;
            snprintf(extra, sizeof extra, ", \"n\": %d, \"nnz_c\": %lld", n, (long long)Cs.nnz);
            emit("convert_csr_to_dense", t, r, warmup, checksum(Cd, nn),
                 8.0 * (double)nn + (double)csr_bytes(&Cs), extra);
        }
        if (dump && write_doubles(dump, Cd, nn) != 0)
            return 1;
        free(Cd);
        csr_free(&Cs);
    } else {
        usage();
    }
    free(A);
    free(B);
    return 0;
}

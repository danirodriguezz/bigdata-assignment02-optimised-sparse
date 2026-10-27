/*
 * bench_dense.c -- timing harness for the dense kernels (Part A).
 *
 * Usage:
 *   bench_dense --method naive_ijk|reorder_ikj|blocked_ikj --n N --a A.f64 --b B.f64
 *               [--bs 64] [--warmup 1] [--reps 5] [--dump C.f64]
 *
 * Timing boundary "kernel": inputs are read and C is allocated and zeroed BEFORE the timer;
 * the timer covers exactly one call of the kernel (for ikj/blocked this includes their
 * internal O(n^2) memset of C). One JSON line is printed per in-process repetition
 * (warm-ups flagged with "is_warmup": true). The checksum (sum of C) consumes the result.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common/util.h"
#include "dense/matmul_dense.h"

static void usage(void)
{
    fprintf(stderr, "usage: bench_dense --method naive_ijk|reorder_ikj|blocked_ikj --n N "
                    "--a A.f64 --b B.f64 [--bs 64] [--warmup 1] [--reps 5] [--dump C.f64]\n");
    exit(2);
}

int main(int argc, char **argv)
{
    const char *method = NULL, *pa = NULL, *pb = NULL, *dump = NULL;
    int n = 0, bs = 64, warmup = 1, reps = 5;
    for (int i = 1; i < argc; i++) {
        if (i + 1 >= argc)
            usage();
        if (!strcmp(argv[i], "--method")) method = argv[++i];
        else if (!strcmp(argv[i], "--n")) n = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--a")) pa = argv[++i];
        else if (!strcmp(argv[i], "--b")) pb = argv[++i];
        else if (!strcmp(argv[i], "--bs")) bs = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--warmup")) warmup = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--reps")) reps = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--dump")) dump = argv[++i];
        else usage();
    }
    if (!method || !pa || !pb || n <= 0 || bs <= 0 || reps < 1 || warmup < 0)
        usage();
    int id;
    if (!strcmp(method, "naive_ijk")) id = 0;
    else if (!strcmp(method, "reorder_ikj")) id = 1;
    else if (!strcmp(method, "blocked_ikj")) id = 2;
    else usage();

    double *A = read_dense(pa, n);
    double *B = read_dense(pb, n);
    double *C = alloc_doubles((size_t)n * n);   /* allocated + zeroed outside the timer */
    if (!A || !B || !C) {
        fprintf(stderr, "Cannot allocate memory or read inputs\n");
        return 1;
    }
    const double storage = 3.0 * 8.0 * (double)n * (double)n;

    for (int r = 0; r < warmup + reps; r++) {
        const double t0 = now_s();
        if (id == 0) matmul_naive_ijk(n, A, B, C);
        else if (id == 1) matmul_reorder_ikj(n, A, B, C);
        else matmul_blocked_ikj(n, bs, A, B, C);
        const double t = now_s() - t0;
        const double cs = checksum(C, (size_t)n * n);
        printf("{\"time_s\": %.9f, \"timer_boundary\": \"kernel\", \"repetition\": %d, "
               "\"is_warmup\": %s, \"checksum\": %.17g, \"memory_metric\": \"array_storage_estimate\", "
               "\"memory_bytes\": %.0f, \"block_size\": %d, \"gflops\": %.4f}\n",
               t, r < warmup ? r : r - warmup, r < warmup ? "true" : "false", cs, storage,
               id == 2 ? bs : 0, 2.0 * n * (double)n * n / t / 1e9);
        fflush(stdout);
    }
    if (dump && write_doubles(dump, C, (size_t)n * n) != 0) {
        fprintf(stderr, "cannot write %s\n", dump);
        return 1;
    }
    free(A);
    free(B);
    free(C);
    return 0;
}

#define _POSIX_C_SOURCE 200112L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "util.h"

double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + 1e-9 * (double)ts.tv_nsec;
}

double *alloc_doubles(size_t count)
{
    void *p = NULL;
    if (posix_memalign(&p, 64, (count > 0 ? count : 1) * sizeof(double)) != 0)
        return NULL;
    memset(p, 0, (count > 0 ? count : 1) * sizeof(double));
    return (double *)p;
}

double *read_dense(const char *path, int n)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "cannot open %s\n", path);
        return NULL;
    }
    const size_t count = (size_t)n * n;
    double *x = alloc_doubles(count);
    if (!x) {
        fprintf(stderr, "Cannot allocate memory for %s\n", path);
        fclose(f);
        return NULL;
    }
    size_t got = fread(x, sizeof(double), count, f);
    int extra = fgetc(f);
    fclose(f);
    if (got != count || extra != EOF) {
        fprintf(stderr, "%s: expected exactly %zu doubles (n=%d)\n", path, count, n);
        free(x);
        return NULL;
    }
    return x;
}

int write_doubles(const char *path, const double *x, size_t count)
{
    FILE *f = fopen(path, "wb");
    if (!f)
        return -1;
    size_t put = fwrite(x, sizeof(double), count, f);
    fclose(f);
    return put == count ? 0 : -1;
}

int read_coo(const char *path, int64_t *n, int64_t *nnz, int32_t **rows, int32_t **cols,
             double **vals)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "cannot open %s\n", path);
        return -1;
    }
    int64_t hdr[2];
    if (fread(hdr, sizeof(int64_t), 2, f) != 2) {
        fclose(f);
        return -1;
    }
    *n = hdr[0];
    *nnz = hdr[1];
    const size_t m = (size_t)(*nnz > 0 ? *nnz : 1);
    *rows = malloc(m * sizeof(int32_t));
    *cols = malloc(m * sizeof(int32_t));
    *vals = malloc(m * sizeof(double));
    if (!*rows || !*cols || !*vals) {
        fprintf(stderr, "Cannot allocate memory for %s\n", path);
        fclose(f);
        return -1;
    }
    const size_t k = (size_t)*nnz;
    int ok = fread(*rows, sizeof(int32_t), k, f) == k && fread(*cols, sizeof(int32_t), k, f) == k &&
             fread(*vals, sizeof(double), k, f) == k;
    fclose(f);
    if (!ok) {
        fprintf(stderr, "%s: truncated COO file\n", path);
        return -1;
    }
    return 0;
}

double checksum(const double *x, size_t count)
{
    double s = 0.0;
    for (size_t i = 0; i < count; i++)
        s += x[i];
    return s;
}

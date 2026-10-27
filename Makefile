# Reproducibility pipeline — Assignment 02 (Daniel Rodríguez Alonso, Big Data ULPGC 2026-2027)
NN      := 02
NAME    := Assignment$(NN)_RodriguezAlonso
VENV    := .venv
PY      := $(VENV)/bin/python
SKILLS  := .claude/skills

# Same compiler and flags for every method (single thread, no BLAS, no -march=native)
CC      := gcc
CFLAGS  := -O2 -std=c11 -Wall -Wextra
SRC     := src/c
COMMON  := $(SRC)/common/util.c
DENSE   := $(SRC)/baseline/matmul_naive.c $(SRC)/dense/matmul_dense.c
SPARSE  := $(SRC)/sparse/csr.c
HDRS    := $(wildcard $(SRC)/*/*.h)

.PHONY: all setup build test inputs pilot bench env analysis report package clean

all: setup test inputs bench analysis report package

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PY) -m pip install -q -r requirements.txt
	$(PY) -m pip freeze > requirements-lock.txt
	touch $(VENV)/bin/activate

build/bench_dense: $(SRC)/bench_dense.c $(COMMON) $(DENSE) $(HDRS)
	@mkdir -p build
	$(CC) $(CFLAGS) -I$(SRC) -o $@ $(SRC)/bench_dense.c $(COMMON) $(DENSE)

build/bench_sparse: $(SRC)/bench_sparse.c $(COMMON) $(DENSE) $(SPARSE) $(HDRS)
	@mkdir -p build
	$(CC) $(CFLAGS) -I$(SRC) -o $@ $(SRC)/bench_sparse.c $(COMMON) $(DENSE) $(SPARSE)

build: build/bench_dense build/bench_sparse

setup: $(VENV)/bin/activate build    ## venv + compile implementations

test: setup                          ## correctness tests — must pass before any benchmark
	$(PY) tests/test_correctness.py

inputs: setup                        ## shared input files + checksums (all configured inputs)
	$(PY) scripts/run_experiments.py --config configs/experiment.json --inputs-only

env:
	bash $(SKILLS)/benchmark-protocol/scripts/capture_env.sh results/environment.md

pilot: test env                      ## quick end-to-end smoke run (small n, 1 rep)
	$(PY) scripts/run_experiments.py --config configs/pilot.json

bench: test env                      ## full experiment (long; serialised by the machine-wide lock)
	$(PY) scripts/run_experiments.py --config configs/experiment.json

analysis: setup                      ## results/raw -> results/summary, report/figures, report/generated
	$(PY) analysis/make_all.py

report:                              ## compile PDF and copy to deliverables/
	cd report && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
	mkdir -p deliverables && cp report/main.pdf deliverables/$(NAME)_Report.pdf

package: report                      ## materials zip from the committed git tree
	bash $(SKILLS)/reproducibility-package/templates/package.sh $(NN)

clean:
	cd report && latexmk -C || true
	rm -rf build

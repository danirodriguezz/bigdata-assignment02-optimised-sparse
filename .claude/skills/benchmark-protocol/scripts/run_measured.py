#!/usr/bin/env python3
"""Run a benchmark command under the common protocol and append raw rows to a CSV.

Features
- Holds a machine-wide exclusive lock (~/.cache/bigdata_bench.lock) while measuring, so that
  benchmarks launched from different assignment folders never run at the same time.
- Launches the command once per process run (--warmup + --reps), measures the process wall time
  with a monotonic clock and the peak resident set size (ru_maxrss of that child, via os.wait4).
- Parses JSON lines printed by the program on stdout. Each JSON line becomes one CSV row, so a
  program may run several in-process repetitions (needed for JIT warm-up in Java) and print one
  line per repetition. Recognised keys: time_s, timer_boundary, repetition, is_warmup, checksum,
  memory_metric, memory_bytes, status. Any other key goes to the extra_json column.
- If the program prints no JSON line, one row is written using the process wall time
  (timer_boundary = "process_wall").
- Timeouts and out-of-memory failures are recorded as rows with status timeout/oom and an EMPTY
  time; they are never given an invented time.

Example
  python3 run_measured.py --out results/raw/a1.csv --warmup 1 --reps 5 --timeout 600 \
      --label experiment=size_sweep method=naive_ijk language=c n=512 dtype=float64 seed=42 \
      -- ./build/matmul_c --n 512 --seed 42
"""
import argparse
import csv
import datetime as dt
import fcntl
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

LOCK_PATH = Path.home() / ".cache" / "bigdata_bench.lock"
GNU_TIME = "/usr/bin/time" if os.access("/usr/bin/time", os.X_OK) else None

COLUMNS = [
    "run_id", "timestamp", "host", "assignment", "experiment", "method", "language",
    "n", "dtype", "density", "representation", "threads", "workers", "nodes",
    "process_run", "repetition", "is_warmup", "timer_boundary", "time_s",
    "process_wall_s", "peak_rss_kib", "memory_metric", "memory_bytes",
    "status", "returncode", "seed", "checksum", "loadavg_1m", "cmd", "extra_json",
]
KNOWN_JSON = {"time_s", "timer_boundary", "repetition", "is_warmup", "checksum",
              "memory_metric", "memory_bytes", "status"}
OOM_MARKERS = ("MemoryError", "OutOfMemoryError", "std::bad_alloc", "Cannot allocate memory")


def parse_labels(items):
    labels = {}
    for item in items or []:
        if "=" not in item:
            sys.exit(f"--label expects key=value, got {item!r}")
        key, value = item.split("=", 1)
        if key not in COLUMNS:
            sys.exit(f"unknown label {key!r}; allowed: {', '.join(COLUMNS)}")
        labels[key] = value
    return labels


def run_once(cmd, timeout, env):
    """Return (returncode, wall_s, peak_rss_kib, stdout, stderr, timed_out).

    stdout/stderr go to temporary files. Peak RSS comes from GNU time (%M, KiB), which measures
    the exec'ed program only. Without GNU time we fall back to os.wait4 ru_maxrss, which also
    counts the ~12 MiB of the forked Python child before exec (a floor that matters for tiny runs).
    """
    with tempfile.TemporaryFile("w+") as out_f, tempfile.TemporaryFile("w+") as err_f, \
            tempfile.NamedTemporaryFile("r", suffix=".time") as time_f:
        full_cmd = cmd
        if GNU_TIME:
            full_cmd = [GNU_TIME, "-f", "%M", "-o", time_f.name] + list(cmd)
        start = time.perf_counter()
        proc = subprocess.Popen(full_cmd, stdout=out_f, stderr=err_f, text=True, env=env,
                                start_new_session=True)
        deadline = start + timeout
        timed_out = False
        nap = 0.0005
        while True:
            pid, status, rusage = os.wait4(proc.pid, os.WNOHANG)
            if pid == proc.pid:
                break
            if time.perf_counter() > deadline:
                timed_out = True
                os.killpg(proc.pid, signal.SIGKILL)
                pid, status, rusage = os.wait4(proc.pid, 0)
                break
            time.sleep(nap)
            nap = min(nap * 2, 0.01)
        wall = time.perf_counter() - start
        rc = os.waitstatus_to_exitcode(status)
        proc.returncode = rc  # already reaped; keep Popen from waiting again
        peak = None if timed_out else rusage.ru_maxrss  # killed run: no trustworthy peak
        if GNU_TIME and not timed_out:
            lines = [ln.strip() for ln in open(time_f.name).read().splitlines() if ln.strip()]
            if lines and lines[-1].isdigit():
                peak = int(lines[-1])
        out_f.seek(0)
        err_f.seek(0)
        return rc, wall, peak, out_f.read(), err_f.read(), timed_out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="raw CSV to append to (created with header if missing)")
    ap.add_argument("--warmup", type=int, default=0, help="process-level warm-up runs (rows flagged is_warmup=1)")
    ap.add_argument("--reps", type=int, default=5, help="measured process runs")
    ap.add_argument("--timeout", type=float, default=600, help="seconds per process run")
    ap.add_argument("--label", nargs="*", default=[], help="key=value configuration labels")
    ap.add_argument("--env", nargs="*", default=[], help="extra KEY=VALUE environment variables")
    ap.add_argument("--no-lock", action="store_true", help="do not take the machine-wide lock (tests only)")
    ap.add_argument("--stop-on-failure", action="store_true", default=True)
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- command to run")
    args = ap.parse_args()

    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        sys.exit("missing command after --")
    labels = parse_labels(args.label)
    env = os.environ.copy()
    for item in args.env:
        k, v = item.split("=", 1)
        env[k] = v

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out.exists() or out.stat().st_size == 0

    lock_fh = None
    if not args.no_lock:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        lock_fh = open(LOCK_PATH, "w")
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"[run_measured] waiting for benchmark lock {LOCK_PATH} "
                  "(another assignment is benchmarking)...", file=sys.stderr, flush=True)
            fcntl.flock(lock_fh, fcntl.LOCK_EX)

    host = socket.gethostname()
    rows_written = 0
    failures = 0
    with open(out, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        total = args.warmup + args.reps
        for i in range(total):
            proc_warm = i < args.warmup
            load1 = os.getloadavg()[0]
            rc, wall, rss, stdout, stderr, timed_out = run_once(cmd, args.timeout, env)
            base = {c: "" for c in COLUMNS}
            base.update(labels)
            base.update({
                "run_id": uuid.uuid4().hex[:12],
                "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
                "host": host, "process_run": i, "process_wall_s": f"{wall:.9f}",
                "peak_rss_kib": rss if rss is not None else "", "returncode": rc,
                "loadavg_1m": f"{load1:.2f}", "cmd": shlex.join(cmd),
            })
            if timed_out:
                status = "timeout"
            elif rc != 0 and (rc in (-9, 137) or any(m in stderr for m in OOM_MARKERS)):
                status = "oom"
            elif rc != 0:
                status = "error"
            else:
                status = "ok"

            json_rows = []
            if status == "ok":
                for line in stdout.splitlines():
                    line = line.strip()
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            json_rows.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            if not json_rows:
                row = dict(base)
                row.update({"repetition": 0, "is_warmup": int(proc_warm), "status": status})
                if status == "ok":
                    row.update({"time_s": f"{wall:.9f}", "timer_boundary": "process_wall"})
                writer.writerow(row)
                rows_written += 1
            for j, rec in enumerate(json_rows):
                row = dict(base)
                row["repetition"] = rec.get("repetition", j)
                row["is_warmup"] = int(proc_warm or bool(rec.get("is_warmup", False)))
                for key in ("time_s", "timer_boundary", "checksum", "memory_metric", "memory_bytes"):
                    if key in rec:
                        row[key] = rec[key]
                row["status"] = rec.get("status", status)
                extra = {k: v for k, v in rec.items() if k not in KNOWN_JSON}
                row["extra_json"] = json.dumps(extra, separators=(",", ":")) if extra else ""
                writer.writerow(row)
                rows_written += 1
            fh.flush()

            tag = "warmup" if proc_warm else "measured"
            print(f"[run_measured] {tag} run {i}: status={status} wall={wall:.3f}s "
                  f"peak_rss={rss} KiB", file=sys.stderr, flush=True)
            if status != "ok":
                failures += 1
                if stderr.strip():
                    print(stderr.strip()[-2000:], file=sys.stderr)
                if args.stop_on_failure:
                    print("[run_measured] stopping this configuration after a failure "
                          "(recorded as a result, no time invented)", file=sys.stderr)
                    break

    if lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()
    print(f"[run_measured] wrote {rows_written} rows to {out}", file=sys.stderr)
    # exit code 3 tells a driver script that this size failed (timeout/oom/error) -> stop escalating n
    sys.exit(3 if failures else 0)


if __name__ == "__main__":
    main()

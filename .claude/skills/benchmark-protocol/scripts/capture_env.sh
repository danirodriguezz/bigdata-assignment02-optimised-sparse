#!/usr/bin/env bash
# Capture the execution environment required by the common protocol.
# Usage: bash capture_env.sh [output_file]   (default: results/environment.md)
set -u
OUT="${1:-results/environment.md}"
mkdir -p "$(dirname "$OUT")"

section() { printf '\n## %s\n\n```\n' "$1"; }
endsec() { printf '```\n'; }
try() { "$@" 2>&1 || true; }

{
  echo "# Execution environment"
  echo
  echo "Captured: $(date --iso-8601=seconds) on host \`$(hostname)\`"

  section "CPU (lscpu)"
  try env LC_ALL=C lscpu | grep -E 'Model name|Architecture|^CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|NUMA node\(s\)|L1d|L1i|L2|L3|CPU max MHz|CPU min MHz'
  echo "SIMD flags: $(grep -o -w -E 'sse4_2|avx|avx2|fma|avx512f' /proc/cpuinfo | sort -u | tr '\n' ' ')"
  echo "nproc (online logical CPUs): $(nproc)"
  endsec

  section "Frequency scaling / turbo"
  echo "governor(cpu0): $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo n/a)"
  echo "intel_pstate no_turbo: $(cat /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || echo n/a)"
  ac="n/a"
  for ps in /sys/class/power_supply/*; do
    [ "$(cat "$ps/type" 2>/dev/null)" = "Mains" ] && ac="$(cat "$ps/online")"
  done
  echo "AC power online (1=plugged): $ac"
  endsec

  section "Memory"
  try free -h
  endsec

  section "Operating system"
  try uname -a
  try grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release
  endsec

  section "Toolchain versions"
  for c in gcc clang java javac mvn python3 pip docker mpicc mpirun spark-submit perf; do
    if command -v "$c" >/dev/null 2>&1; then
      case "$c" in
        java|javac) v=$("$c" -version 2>&1 | head -1) ;;
        mvn) v=$(mvn -v 2>&1 | head -1 | sed 's/\x1b\[[0-9;]*m//g') ;;
        mpirun) v=$(mpirun --version 2>&1 | head -1) ;;
        spark-submit) v=$(spark-submit --version 2>&1 | grep -m1 version) ;;
        *) v=$("$c" --version 2>&1 | head -1) ;;
      esac
      printf '%-13s %s\n' "$c" "$v"
    else
      printf '%-13s %s\n' "$c" "not installed"
    fi
  done
  endsec

  section "Python packages (active interpreter: $(command -v python3))"
  try python3 -m pip freeze 2>/dev/null | head -100
  endsec

  section "Threading-related environment variables"
  env | grep -E '^(OMP_|MKL_|OPENBLAS_|BLIS_|NUMEXPR_|GOMP_|KMP_|JAVA_TOOL_OPTIONS|_JAVA_OPTIONS)' || echo "(none set)"
  endsec

  section "Load at capture time"
  try uptime
  endsec
} > "$OUT"

echo "environment written to $OUT"

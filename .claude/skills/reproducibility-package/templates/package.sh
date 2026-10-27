#!/usr/bin/env bash
# Build deliverables/AssignmentNN_RodriguezAlonso_Materials.zip from the files tracked by git,
# and copy the compiled report next to it.
# Usage: bash package.sh NN        (run from the assignment folder root)
set -euo pipefail
NN="${1:?usage: package.sh NN (e.g. 01)}"
NAME="Assignment${NN}_RodriguezAlonso"
mkdir -p deliverables

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "not a git repository: run git init and commit first"; exit 1; }
if [ -n "$(git status --porcelain)" ]; then
  echo "WARNING: uncommitted changes are NOT included in the zip:"; git status --short
fi

git archive --format=zip --prefix="${NAME}_Materials/" -o "deliverables/${NAME}_Materials.zip" HEAD
[ -f report/main.pdf ] && cp report/main.pdf "deliverables/${NAME}_Report.pdf"

echo "commit: $(git rev-parse --short HEAD)"
ls -lh deliverables/
unzip -l "deliverables/${NAME}_Materials.zip" | tail -1

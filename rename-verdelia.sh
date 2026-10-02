#!/usr/bin/env bash
# Rename every file and directory whose name contains "verdelia"
# (any of the three cases), then rewrite every reference inside the
# file contents. Recursive from the current directory.
#
# Re-runnable: does nothing on a tree that's already been renamed.

set -euo pipefail

# Directories to skip entirely.
SKIP_DIRS=(
  ".git" "build" ".dart_tool" "node_modules" "__pycache__"
  ".venv" "venv" ".idea" ".vscode" "dist" ".next"
)

# Build the find `-not -path` clauses once.
skip_args=()
for d in "${SKIP_DIRS[@]}"; do
  skip_args+=(-not -path "./$d/*" -not -path "./$d")
done

# ─────────────────────────────────────────────────────────────────
# 1. Rename deepest-first.
#
# `find -depth` yields children before their parents, so a renamed
# directory still has its (already-renamed) children in place when
# `mv` runs on it.
#
# The inner loop handles names with spaces correctly by quoting each
# path. Names with newlines are pathological; if your tree has them,
# use the NUL-separated variant at the bottom of this file.
# ─────────────────────────────────────────────────────────────────

echo "Renaming paths..."
find . -depth -iname '*verdelia*' "${skip_args[@]}" -print0 \
| while IFS= read -r -d '' path; do
  dir=$(dirname "$path")
  base=$(basename "$path")
  new_base=$(printf '%s' "$base" \
    | sed -e 's/verdelia/verdelia/g' \
          -e 's/Verdelia/Verdelia/g' \
          -e 's/VERDELIA/VERDELIA/g')
  if [ "$base" != "$new_base" ]; then
    mv -- "$path" "$dir/$new_base"
    printf '  renamed: %s -> %s\n' "$path" "$dir/$new_base"
  fi
done

# ─────────────────────────────────────────────────────────────────
# 2. Rewrite contents of every text file that references the token.
#
# `grep -rI` recurses, `-I` skips binaries, `-l` prints filenames.
# `xargs -0` is newline-safe.
# ─────────────────────────────────────────────────────────────────

echo "Rewriting contents..."
grep -rIlZ -E 'verdelia|Verdelia|VERDELIA' . \
  $(for d in "${SKIP_DIRS[@]}"; do printf '%s ' "--exclude-dir=$d"; done) \
| xargs -0 -r sed -i \
    -e 's/verdelia/verdelia/g' \
    -e 's/Verdelia/Verdelia/g' \
    -e 's/VERDELIA/VERDELIA/g'

echo "Done."
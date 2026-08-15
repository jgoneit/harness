#!/bin/sh
set -eu

repo_root=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
cd "$repo_root"

if harness_commit=$(git rev-parse --verify HEAD 2>/dev/null); then
  :
else
  harness_commit=unborn
fi

printf 'harness_commit\t%s\n' "$harness_commit"

git config -f .gitmodules --get-regexp '^submodule\..*\.path$' |
while IFS=' ' read -r key path; do
  [ -n "$key" ] || continue
  [ -n "$path" ] || continue

  if [ "$harness_commit" = unborn ]; then
    recorded_commit=$(git ls-files --stage -- "$path" | awk '$1 == "160000" { print $2 }')
  else
    recorded_commit=$(git ls-tree HEAD -- "$path" | awk '$1 == "160000" { print $3 }')
  fi
  if [ -z "$recorded_commit" ]; then
    recorded_commit=not-recorded
  fi

  if [ -e "$path/.git" ]; then
    checked_out_commit=$(git -C "$path" rev-parse --verify HEAD)
    if [ "$recorded_commit" = "$checked_out_commit" ] &&
       [ -z "$(git -C "$path" status --porcelain)" ]; then
      worktree_state=clean
    else
      worktree_state=dirty
    fi
  else
    checked_out_commit=not-initialized
    worktree_state=uninitialized
  fi

  printf 'submodule_path\t%s\n' "$path"
  printf 'recorded_commit\t%s\n' "$recorded_commit"
  printf 'checked_out_commit\t%s\n' "$checked_out_commit"
  printf 'worktree_state\t%s\n' "$worktree_state"
done

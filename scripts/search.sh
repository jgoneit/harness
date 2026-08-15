#!/bin/sh
set -eu

repo_root=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
cd "$repo_root"

if [ "$#" -lt 1 ]; then
  printf 'usage: %s PATTERN [PATHSPEC ...]\n' "$0" >&2
  exit 2
fi

pattern=$1
shift

if [ "$#" -eq 0 ]; then
  exec git grep --recurse-submodules -e "$pattern"
fi

exec git grep --recurse-submodules -e "$pattern" -- "$@"

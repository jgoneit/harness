#!/bin/sh
set -eu

repo_root=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
cd "$repo_root"

git submodule sync --recursive
git submodule update --init --recursive
git submodule status --recursive

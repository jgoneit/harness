# Adding a Module

Module admission is intentionally manual. Harness has no module generator,
scaffold engine, or automatic discovery service.

## Procedure

1. Confirm that the independent module repository actually exists.
2. Review the module boundary and its one-sentence responsibility.
3. Validate every requirement in [the module contract](module-contract.md).
4. Add one exact entry to `catalog/modules.json`.
5. Add the repository as a Git submodule at its Plane-specific path.
6. Check out and record the reviewed exact module commit.
7. Smoke-test a fresh recursive clone and the read-only Harness scripts.
8. Submit the catalog, `.gitmodules`, and gitlink change for Harness review.

## Pinning rules

- Prefer a relative submodule URL when the repository shares the GitHub owner.
- Record one reviewed commit; do not configure automatic branch following.
- A later module update is a new explicit Harness commit or pull request.
- Do not modify the module repository while preparing the Harness pin.
- Do not add a planned entry, empty directory, or empty submodule for a future
  module.

## Validation checklist

Before review, verify:

```bash
python3 -m json.tool catalog/modules.json >/dev/null
git config -f .gitmodules --get-regexp '^submodule\..*\.(path|url)$'
git submodule status --recursive
scripts/bootstrap.sh
scripts/status.sh
scripts/search.sh '<known read-only pattern>'
```

Then clone the proposed Harness commit into a new temporary directory with
`--recurse-submodules`. Confirm the catalog repository/path, `.gitmodules`, and
recorded gitlink all describe the same module and that every worktree is clean.

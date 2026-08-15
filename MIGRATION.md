# Harness URL Migration

## Meaning of `jgoneit/harness`

Before this registry was created, the historical `jgoneit/harness` URL
redirected to the repository that is now `jgoneit/seal-legacy`. That redirect
represented the rename history of Outcome Harness and Python Seal.

The URL now identifies a new and distinct repository:

```text
https://github.com/jgoneit/harness
→ Jgoneit Agent Toolkit registry and pinned source workspace
```

This repository does not contain or replace the historical product Git history.

## Preserved and successor repositories

```text
https://github.com/jgoneit/seal-legacy
→ Python behavioral reference and historical Outcome Harness / Seal history

https://github.com/jgoneit/seal
→ experimental Go Seal successor candidate
```

The Python reference is frozen at commit
`94bb931a7934efe31549d4c21dc7153e43f27a08`, branch `seal-legacy`, and annotated
tag `python-reference-v0.3.0-dev.0-94bb931`. Historical releases remain in the
Legacy repository.

The initial Toolkit pin for Go Seal is
`2391d1c4d77cdf348a0842c0cb7fd1d2e80f8ef5`.

## What did not move

- No Python source or Evidence was copied into this registry.
- No historical tag or release was moved, deleted, or reinterpreted.
- No Plugin marketplace or cache state was migrated.
- No existing repository was archived or deleted.
- Harness did not become a runtime, workflow engine, or compatibility layer.

Old bookmarks that relied on the former redirect must be updated explicitly to
`jgoneit/seal-legacy`. Consumers must not infer repository identity from the old
redirect behavior.

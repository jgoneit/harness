# Jgoneit Agent Toolkit

**Registry and workspace for the modular Jgoneit Agent Toolkit.**

It provides a pinned source workspace for independent tools that improve Native
Coding Agent work.

The Native Agent remains at the center: it owns planning, implementation,
execution, tool choice, and any Agent Team topology. The user, Native Agent, or
CI chooses which modules to install and how to compose them. Harness catalogs
module state; it does not run modules or own workflow transitions.

## Current modules

Only repositories that actually exist are listed.

| Module | Plane | Status | Repository | Pinned commit | Workspace path |
| --- | --- | --- | --- | --- | --- |
| Seal | Acceptance | Experimental | <https://github.com/jgoneit/seal> | `bd86a683675fd14e38dc51899fa2489e4f0be985` | `modules/acceptance/seal` |

The pinned Seal candidate provides Task creation and reads, manifest-valid
verification, canonical Run reads, and Basic-profile completion over `.seal`
state. The Go repository remains experimental; Bundle, Verdict, and Reviewer
behavior are not implemented. The frozen Python behavioral reference remains
[Seal Legacy](https://github.com/jgoneit/seal-legacy).

## Clone the pinned workspace

Clone the registry and its exact module pins in one command:

```bash
git clone --recurse-submodules https://github.com/jgoneit/harness.git
cd harness
```

For an existing clone, initialize the recorded pins without building or running
any module:

```bash
scripts/bootstrap.sh
```

The bootstrap script performs only recursive submodule sync, initialization,
and status reporting. It does not install packages, select a newer module
commit, or execute Seal.

## Inspect exact pins

```bash
scripts/status.sh
git submodule status --recursive
git ls-tree HEAD modules/acceptance/seal
```

The superproject gitlink is the module version contract for this workspace. A
module update requires an explicit Harness commit or pull request; submodules do
not automatically follow `main`.

## Search local module sources

Use the read-only wrapper around `git grep --recurse-submodules`:

```bash
scripts/search.sh 'Seal exposes state'
scripts/search.sh 'conformance'
```

Search results are not indexed, persisted, or treated as module state.

## Install modules independently

Harness is not an installer. Follow each module's repository-owned setup and
removal guidance:

- [Seal README](https://github.com/jgoneit/seal#readme)

Harness does not copy or wrap module installers.

## What Harness does not do

Harness does not execute agents, Seal, reviews, CI, deployment, retries, or
repairs. It has no common runtime, event bus, provider registry, workflow
history, central state machine, module enable flag, or shared mutable lifecycle
state. It does not choose execution order or enforce model reasoning formats.

## Adding a future module

A future module must already have an independent repository, one clear Plane,
its own README and lifecycle, deterministic output or artifacts, a defined
error contract, and an evaluation plan. It must not auto-invoke another module
or require Harness as a runtime.

See [the module contract](docs/module-contract.md) and
[the manual addition procedure](docs/adding-a-module.md). Do not add planned
catalog entries or empty submodules before their repositories exist.

## Historical Python implementation

Past Outcome Harness and Python Seal history, tags, and releases are preserved
at [jgoneit/seal-legacy](https://github.com/jgoneit/seal-legacy). The current
`jgoneit/harness` URL names this Toolkit registry, not the historical product.
See [MIGRATION.md](MIGRATION.md) for the URL transition.

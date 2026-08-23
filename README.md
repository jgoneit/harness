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
| Seal | Acceptance | Experimental | <https://github.com/jgoneit/seal> | `998af7bbe865c24b523b393e0c71d8861bb4f364` | `modules/acceptance/seal` |
| Ward | Security | Experimental | <https://github.com/jgoneit/ward> | `0637b3e567dd7f856d1ae492498658a080986e9e` | `modules/security/ward` |

The pinned Seal candidate provides Task creation and reads, manifest-valid
verification, canonical Run reads, and Basic-profile completion over `.seal`
state. It also includes a skills-only Codex Plugin adapter that declares
explicit and repository-opted-in activation without bundling the CLI or taking
over Acceptance authority. Fresh-task routing has not been smoke-tested, and
repository-owned Plugin installation and removal guidance remains outstanding.
The Go repository remains experimental; Bundle, Verdict, and Reviewer behavior
are not implemented. The frozen Python behavioral reference remains
[Seal Legacy](https://github.com/jgoneit/seal-legacy).

The pinned Ward candidate installs and verifies a bounded native secret
boundary, vetoes a small set of high-confidence catastrophic actions, and
otherwise defers to the Host permission model. This pre-RC source pin is
Experimental: it does not install or activate Ward, satisfy Ward's release
gates, or claim production readiness.

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
commit, or execute any module.

## Inspect exact pins

```bash
scripts/status.sh
git submodule status --recursive
git ls-tree HEAD modules/acceptance/seal
git ls-tree HEAD modules/security/ward
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
- [Ward README at the pinned commit](https://github.com/jgoneit/ward/tree/0637b3e567dd7f856d1ae492498658a080986e9e#readme)

Harness does not copy or wrap module installers.

## What Harness does not do

Harness does not execute agents or modules, reviews, CI, deployment, retries,
or repairs. It has no common runtime, event bus, provider registry, workflow
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

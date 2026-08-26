# Jgoneit Agent Toolkit

**Registry and workspace for the modular Jgoneit Agent Toolkit.**

It provides a pinned source workspace for independent tools that improve Native
Coding Agent work.

The Native Agent remains at the center: it owns planning, implementation,
execution, tool choice, and any Agent Team topology. The user, Native Agent, or
CI chooses which modules or protocols to use, installs runtime modules when
needed, and decides how to compose them. Harness catalogs module state; it does
not run modules or own workflow transitions.

## Current modules

Only repositories that actually exist are listed.

| Module | Plane | Status | Repository | Pinned commit | Workspace path |
| --- | --- | --- | --- | --- | --- |
| Seal | Acceptance | Experimental | <https://github.com/jgoneit/seal> | `bcb0041a70f7ba02c29a0ba8c1e83bfea36c143e` | `modules/acceptance/seal` |
| Ward | Security | Experimental | <https://github.com/jgoneit/ward> | `9020346dedfa70f7c08004b2282c04f224c0f2c4` | `modules/security/ward` |
| Eval | Evaluation | Experimental | <https://github.com/jgoneit/eval> | `1337639155563fddedfeec14134de5ff7a6d5845` | `modules/evaluation/eval` |

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

The pinned Eval candidate is a provider-neutral post-task Artifact protocol.
Its manifest exposes the Charter, Protocol, Observation Schema, and Report
Template for Native Agent, user, or CI selection after a terminal task outcome.
Harness does not install, execute, activate, or self-trigger Eval. The pin is a
contract scaffold, not an Evaluation MVP or evidence that another module is
valuable.

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
git ls-tree HEAD modules/evaluation/eval
```

The superproject gitlink is the module version contract for this workspace. A
module update requires an explicit Harness commit or pull request; submodules do
not automatically follow `main`. Registry-maintenance automation may query an
upstream `main` branch and propose that exact commit in a pull request, but the
recorded pin moves only when that Harness pull request is merged.

## Maintain exact pins

The daily `Update submodule pins` workflow checks every catalog module and may
open one pull request per module. Each candidate is limited to one gitlink plus
that module's README pin references. The workflow rejects non-fast-forward
upstream movement, stale README metadata, unrelated file changes, and published
upstream checks that are pending or unsuccessful.

Pull requests remain manual by default. Optional auto-merge requires a scoped
GitHub App, the `pin-consistency` required check, repository auto-merge, and the
module id in the `SUBMODULE_PIN_AUTO_MERGE_MODULES` repository variable. See
[the pin automation runbook](docs/submodule-pin-automation.md) for setup,
validation, failure handling, and rollback.

## Search local module sources

Use the read-only wrapper around `git grep --recurse-submodules`:

```bash
scripts/search.sh 'Seal exposes state'
scripts/search.sh 'conformance'
```

Search results are not indexed, persisted, or treated as module state.

## Use modules independently

Harness is not an installer. Follow each runtime module's repository-owned
setup and removal guidance, or an Artifact protocol's repository-owned usage
boundary:

- [Seal README](https://github.com/jgoneit/seal#readme)
- [Ward README at the pinned commit](https://github.com/jgoneit/ward/tree/9020346dedfa70f7c08004b2282c04f224c0f2c4#readme)
- [Eval README at the pinned commit](https://github.com/jgoneit/eval/tree/1337639155563fddedfeec14134de5ff7a6d5845#readme)

Harness does not copy or wrap module installers. Eval declares no installed
runtime; its catalog entry provides static discovery paths only.

## What Harness does not do

Harness does not execute agents or modules or orchestrate user/module reviews,
CI, deployment, retries, or repairs. Its own bounded registry-maintenance CI may
verify catalog/gitlink consistency and propose exact-pin pull requests. It has
no common runtime, event bus, provider registry, workflow history, central state
machine, module enable flag, or shared mutable lifecycle state. It does not
choose execution order or enforce model reasoning formats.

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

# Toolkit Architecture

## Center and modules

```text
                   Native Agent / User / CI
                              |
              chooses modules and composition explicitly
                              |
            +-----------------+-----------------+
            |                                   |
   Harness catalog/workspace          Independent module repository
   - descriptions                     - own usage and lifecycle
   - repository links                 - own CLI/JSON/artifacts
   - exact Git pins                   - no Harness runtime dependency
   - local source search
                                                |
                                      Ward / Security
                                      Seal / Acceptance
                                      (both experimental)
```

Execution remains above the module layer. Harness and modules expose state,
policy, artifacts, or decisions; they do not take ownership of the Native
Agent's workflow.

## Plane map

The architecture recognizes Knowledge, Security, Execution, Acceptance, Review,
and Evaluation concerns. Execution is owned by the Native Agent and is not a
Toolkit module. A conceptual Plane does not imply that a repository exists.

The registry contains two real modules:

- Ward in the Security plane
- Seal in the Acceptance plane

Knowledge, Review, and Evaluation entries are added only after their independent
repositories and contracts exist. Harness does not create empty directories,
placeholder submodules, or planned catalog records for them.

## Catalog and gitlinks

`catalog/modules.json` describes discoverable module identity and boundary.
`.gitmodules` describes how to clone source. The Git tree's submodule gitlink is
the authoritative workspace pin.

For an Artifact protocol, catalog artifact paths are relative to the pinned
submodule root. They allow static contract discovery; they are not execution,
installation, activation, or permission to mutate a task.

For a manifest-backed Artifact protocol, the pinned manifest is authoritative
for invocation owners, terminal requirements, activation, cross-module calls,
and task mutation. Matching catalog fields exist only for static discovery and
must not weaken that manifest.

The catalog does not activate modules, and a gitlink does not request an update
to the module's latest branch. Updating a pin is an explicit Harness change that
must be reviewed like any other source change. Bounded maintenance automation
may query upstream `main` and propose a new exact pin, but clones continue to
resolve the recorded gitlink rather than a moving branch.

Registry-maintenance CI is part of the Harness repository boundary, not the
Toolkit execution plane. It may validate catalog, `.gitmodules`, gitlinks,
README pin references, and clean recursive checkouts. It may not run a module,
modify an upstream repository, decide Toolkit composition, or advance a user's
workflow.

## Independence

Every module can be cloned, used, versioned, and removed without Harness.
Runtime modules can be installed independently; Artifact protocols remain
usable without installation. Harness can be cloned without building or
executing a module. There is no shared process, daemon, SDK, event stream,
ledger, database, or lifecycle state between them.

## Composition boundary

The user, Native Agent, or CI may decide to inspect project knowledge, apply
host security policy, implement work, query Seal, request a review, or evaluate
cost. No Toolkit component encodes that order or automatically calls the next
component after success or failure.

## Recipes

A recipe under `recipes/` is a documented composition that an adopting
repository copies into its own CI. The adopter owns the order it encodes;
modules stay unaware of it and Harness does not execute it elsewhere.

```text
Human intent PR ──merge──▶ base branch (Task input, checks, acceptance tests)
                                  │
Native Agent ──implementation PR──┤  agent sees intent and failure feedback only
                                  ▼
Adopter CI: merge-base ─▶ seal task create ─▶ PR head ─▶ seal verify ─▶ seal complete
                                  │
Human merge decision ◀── accepted / rejected / error
```

[Seal PR acceptance](../recipes/seal-pr-acceptance/README.md) is the first
recipe. Harness applies it to its own pull requests through
`.github/workflows/seal-pr-acceptance.yml`. That workflow is recipe adoption;
it is separate from registry-maintenance CI, which still never runs a module.

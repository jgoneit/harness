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
   - descriptions                     - own install and release
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

The catalog does not activate modules, and a gitlink does not request an update
to the module's latest branch. Updating a pin is an explicit Harness change that
must be reviewed like any other source change.

## Independence

Every module can be cloned, installed, used, released, and removed without
Harness. Harness can be cloned without building or executing a module. There is
no shared process, daemon, SDK, event stream, ledger, database, or lifecycle
state between them.

## Composition boundary

The user, Native Agent, or CI may decide to inspect project knowledge, apply
host security policy, implement work, query Seal, request a review, or evaluate
cost. No Toolkit component encodes that order or automatically calls the next
component after success or failure.

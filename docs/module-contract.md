# Toolkit Module Contract

This contract is the admission boundary for adding a module to the catalog and
pinned workspace.

## Required

A module must have:

- an independent repository;
- an independent README;
- repository-owned installation and uninstallation guidance for a runtime, or
  an explicit no-install/no-runtime boundary for an Artifact protocol;
- one clear sentence describing its responsibility;
- exactly one primary Toolkit Plane;
- machine-readable output or a clearly defined Artifact;
- a deterministic error contract for executable behavior, or a deterministic
  validation contract for an Artifact protocol;
- no automatic invocation of another Toolkit module;
- no requirement for a Native Agent reasoning format;
- provider- or Plugin-specific behavior isolated from the core contract;
- an evaluation plan that can measure whether the module is worth its cost;
- a commit that can be pinned as a Git submodule;
- independent operation without a Harness checkout.

Experimental status must be explicit. Missing distribution or compatibility
work must be documented by the module and cannot be hidden by Harness.

## Rejected designs

A candidate is rejected if its minimum operation requires:

- a central Toolkit runtime;
- an event bus;
- global workflow state;
- another Toolkit module to be installed;
- ownership of automatic workflow transitions;
- a fixed Agent Team or topology;
- Harness to know or enforce module execution order;
- shared mutable lifecycle state in the registry;
- automatic retry or repair by the manager.

## Contract review

Review the public CLI, JSON, Artifact, and exit behavior at the exact proposed
commit. Confirm that installation, removal, and releases remain module-owned.
Record evaluation links only when results exist; do not create placeholder
claims.

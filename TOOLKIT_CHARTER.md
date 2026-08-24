# Jgoneit Agent Toolkit Charter

## Center

The center of the architecture is the **Native Agent, user, or CI**. That
external owner decides what work to perform, which independent tools to use,
and in what order. Harness is a catalog and pinned source workspace, not an
execution layer.

## Planes

The Toolkit's long-term conceptual planes are:

- **Knowledge** — author repository context artifacts and authoritative
  documentation maps.
- **Security** — author explicit sandbox, permission, secret, and network
  policy; enforcement belongs to the host, OS, container, IAM, or CI.
- **Execution** — owned by the Native Agent and therefore not a Toolkit module.
- **Seal / Acceptance** — expose evidence-backed completion state and
  deterministic decisions.
- **Review** — perform read-only, clean-context, one-shot semantic QA without
  implementing or repairing work.
- **Evaluation** — measure module value, defects, false refusals, cost, latency,
  and user friction.

These planes are an architecture map, not a list of promised repositories. The
current catalog contains Ward in Security, Seal in Acceptance, and Eval in
Evaluation.

## Invariants

- Runtime modules support independent installation; Artifact protocols remain
  independently usable without installation.
- Modules own independent releases.
- Public CLI, JSON, or Artifact contracts are stable and explicit.
- No module automatically invokes another module.
- There is no central Toolkit runtime.
- Harness owns no workflow transition.
- Modules share no mutable lifecycle state through Harness.
- No module or manager enforces a model reasoning format or Agent topology.
- Composition belongs to the Native Agent, user, or CI.
- A module remains usable without cloning Harness.

## Harness responsibilities

Harness may provide a module catalog, repository URLs, Plane and compatibility
metadata, exact Git submodule pins, clone/bootstrap documentation, local source
search, module lifecycle links, architecture guidance, and evaluation links.

Harness must not run an agent or module, decide execution order, retry or repair
failures, orchestrate PR/CI/deployment, maintain workflow history, or grow a
runtime, event bus, provider registry, or central state machine.

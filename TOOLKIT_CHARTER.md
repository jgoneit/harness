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
current catalog contains Ward in Security and Seal in Acceptance.

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

## Agent-visible footprint

The Toolkit keeps workflow state out of the Native Agent's context. The agent
receives intent (objective, Scope, acceptance criteria) and, on failure,
actionable results. It does not carry module identities, lifecycle phases, or
exit-code routing. On the normal path of work the user already authorized, a
module adds no prompt or model context.

Integrity comes from boundaries rather than from controlling the agent's
process: intent is committed before implementation and evidence is judged
after it, outside the agent loop. A module detects a violation at a boundary
instead of steering the agent away from it.

## Harness responsibilities

Harness may provide a module catalog, repository URLs, Plane and compatibility
metadata, exact Git submodule pins, clone/bootstrap documentation, local source
search, module lifecycle links, architecture guidance, evaluation links, and
bounded repository-maintenance CI that validates or proposes exact-pin changes.

Harness may also publish recipes: documented, tested compositions of
independent modules that an adopting repository copies and runs in its own CI.
A recipe is guidance, not a runtime. No module depends on it, and Harness does
not run it for another repository.

Harness must not run an agent or module, decide execution order, retry or repair
failures, orchestrate user or module PR/CI/deployment, maintain workflow history,
or grow a runtime, event bus, provider registry, or central state machine. Pin
maintenance may open and validate Harness pull requests, but it must not invoke
a module, change a module repository, or own a user workflow transition.

As an ordinary adopting repository, Harness may apply a recipe to its own pull
requests. That is the repository owner's composition under the same rules as
any adopter, separate from registry maintenance, and not Toolkit execution on
behalf of users.

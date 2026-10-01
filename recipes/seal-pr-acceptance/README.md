# Seal PR acceptance recipe

**Status: Experimental.** Evaluate a pull request against a Seal Task that was
committed before implementation, in the adopting repository's own CI, so the
Native Agent never carries Task, Run, or Completion state.

The Native Agent implements from the written intent. It does not need to know
that Seal exists. Acceptance happens at two boundaries: intent is fixed before
the work, and evidence is judged after it.

## Roles

| Owner | Responsibility |
| --- | --- |
| Human | Merges the intent, binds a pull request to it, decides the merge |
| Native Agent | Implements the change; receives only intent and failure feedback |
| Adopting repository CI | Runs this recipe on its own pull requests |
| Seal | Makes the Acceptance decision ([Seal README](https://github.com/jgoneit/seal#readme)) |
| Harness | Publishes and tests the recipe; does not run it for adopters |

## Flow

1. **Intent pull request.** Add `docs/specs/<name>/task.json`, a Seal Task Spec
   whose Scope and checks describe the intended change. Put the human-readable
   intent (for example `SPEC.md`) and any acceptance tests beside it, outside
   the Task Scope. Review and merge it before implementation starts.
2. **Implementation pull request.** The Native Agent works from the intent. A
   human binds the pull request with one body line:

   ```text
   Seal-Task: <name>
   ```

3. **CI evaluation.** The recipe computes the baseline as
   `git merge-base <base> <head>`, reads `task.json` from that baseline, and in a
   temporary worktree runs `seal task create` at the baseline, then
   `seal verify` and `seal complete` at the head. The caller's checkout is not
   modified.

The Task input and its check definitions are read from the baseline, so
editing them in the implementation pull request changes nothing that is
evaluated. Checks execute at the head; acceptance tests therefore belong
outside the Task Scope, where any change to them is a Scope violation.

## Outcomes

`seal_pr_acceptance.py accept` prints one `seal-pr-acceptance-result/v1` JSON
object and appends Markdown feedback to `--summary` (stderr otherwise).

| Outcome | Exit | Source |
| --- | ---: | --- |
| `accepted` | 0 | `seal complete` exit 0 |
| `rejected` (`scope`, `required-check`, `required-check-timeout`, `source-unstable`) | 1 | `seal complete` exit 4, 5, 6, or 9 |
| `error` | 2 | any other Seal exit, a missing or unreadable baseline Task input, or a Git failure |

Only `rejected` describes the change. The feedback lists files outside Scope
and failed required checks with a local reproduction command. `error` is an
operational failure and is not a judgment of the change. The workflow reports
`not evaluated` when the pull request is unbound or the base branch has no
recipe; that is not acceptance.

## Adopting the recipe

1. Opt the repository into Seal as described in its README: track
   `.seal/checks.json` and ignore `.seal/tasks/` and `.seal/evidence/`.
2. Copy `seal_pr_acceptance.py` to the same path and copy
   [`.github/workflows/seal-pr-acceptance.yml`](../../.github/workflows/seal-pr-acceptance.yml).
   The workflow pins one Seal release and installs it with Seal's own
   installer.
3. Merge the recipe before relying on it. The workflow loads the script from
   the base branch, so a pull request cannot change its own evaluation logic.

## Verified scenarios

[`tests/test_seal_pr_acceptance.py`](../../tests/test_seal_pr_acceptance.py)
runs these scenarios against a real Seal executable (`SEAL_BIN` or `seal` on
`PATH`, skipped otherwise). CI runs them against the pinned release.

- In-scope fix is accepted without modifying the caller's checkout.
- Out-of-scope edit is rejected as `scope`.
- Weakening `.seal/checks.json` instead of fixing is rejected as `scope`.
- Missing fix is rejected as `required-check` with a reproduction command.
- An advanced base branch still accepts, because the baseline is the merge base.
- Widening `task.json` inside the pull request has no effect.
- A Task input absent at the baseline is an `error`.
- Unsafe or conflicting `Seal-Task` bindings are refused.

## Not proven

- A pull request can edit its own workflow file. The trust root is the base
  branch workflow plus branch protection; review diffs under
  `.github/workflows/` and `recipes/` before merging.
- The binding is only as trustworthy as whoever can edit the pull request body.
  If the agent can edit it, a human must confirm the bound Task before merge.
  Do not make `seal-acceptance` a required check until that authority is
  decided, because an unbound pull request finishes the job successfully as
  `not evaluated`.
- Seal proves required checks, Scope, and source stability, not semantic
  correctness. Outcome quality depends on the intent's checks and acceptance
  tests.
- Evidence is not retained after the temporary worktree is removed. The
  feedback records only the Task and Run identities.
- Checks execute pull request code with the runner's environment; see Seal's
  trust model.
- Pull requests that move a submodule gitlink are outside the verified
  scenarios.

The recipe does not retry, repair, re-invoke the agent, infer a latest Task or
Run, comment on the pull request, or decide merges.

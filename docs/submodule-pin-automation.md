# Submodule Pin Automation

Harness keeps reproducible Git submodule pins. Automation observes upstream
`main` branches and proposes exact gitlink changes; it does not make clones
follow a moving branch and it does not run any Toolkit module.

## Workflow

`Update submodule pins` runs daily at 03:17 UTC and can also be started with
`workflow_dispatch`. A manual run accepts a catalog module id or `all`.

For each selected module, the workflow:

1. skips the module when an automation PR is already open;
2. fetches the current upstream `refs/heads/main` commit;
3. rejects a non-fast-forward move from the recorded gitlink;
4. stages exactly one gitlink and every current-pin reference for that module
   in `README.md`;
5. rejects pending or unsuccessful published upstream checks and statuses;
6. runs unit, registry consistency, recursive checkout, status, and search
   validation;
7. non-force pushes a commit-specific automation branch and opens a PR; and
8. leaves the PR for review unless optional auto-merge is explicitly enabled.

When upstream publishes no check runs or commit statuses, the workflow records
zero published checks and continues with Harness validation. This is not proof
that the upstream module ran CI.

The companion `Validate registry pins` workflow runs for pull requests and
`main` pushes. Its `pin-consistency` job repeats validation and checks a fresh
recursive clone. Automation PRs receive an additional exact-diff check: their
content must equal the selected gitlink change plus the mechanically derived
README SHA replacements.

## GitHub App setup

A GitHub App is recommended so the PR creation event can start the independent
pull-request validation workflow. Install the App only on Harness and grant:

- Contents: read and write
- Checks: read
- Pull requests: read and write

Configure these Harness repository values:

- variable `HARNESS_AUTOMATION_APP_ID`: the GitHub App id
- secret `HARNESS_AUTOMATION_APP_PRIVATE_KEY`: the App private key

The workflow requests a short-lived installation token scoped to the current
repository and only those three permissions. If neither value is configured, the
workflow falls back to `GITHUB_TOKEN`. That fallback requires the repository's
Actions setting that allows workflows to create pull requests, and it is not
eligible for this workflow's optional auto-merge path because token-created
events may not start the independent PR workflow. Configuring only one App value
is treated as an error.

## Optional auto-merge

Auto-merge is disabled by default. Before enabling it:

1. enable repository pull-request auto-merge;
2. protect `main` with pull requests and the `pin-consistency` required check;
3. configure the scoped GitHub App above; and
4. set repository variable `SUBMODULE_PIN_AUTO_MERGE_MODULES` to a comma- or
   whitespace-separated allowlist such as `ward,seal`.

Scheduled runs request auto-merge only for allowlisted modules. A manual run
must also set its `auto_merge` input, and the selected module must remain in the
allowlist. A module with no published upstream checks or commit statuses always
remains manual. Before making a permitted request, the updater waits for the
GitHub Actions `pin-consistency` check on the exact PR head to succeed; a missing,
failed, or timed-out check blocks the merge even if branch protection is
misconfigured. The workflow then uses squash auto-merge and matches the expected
head commit when enabling the request, closing the check-to-merge race at that
point. Required exact-diff CI must rerun after any later authorized push, and
automation branch write access should remain restricted. The workflow never
uses an administrator bypass.

Semantic review remains a risk boundary: the automation proves SHA and metadata
consistency, not that README behavior descriptions still characterize a newer
module commit. Keep auto-merge disabled for modules whose public behavior or
installation boundary can change on `main` without a corresponding machine
check.

## Local commands

Validate a checkout without network mutation:

```bash
python3 scripts/pin_registry.py validate
python3 -m unittest discover -s tests -p 'test_*.py'
```

After initializing the recorded pins, require matching clean submodules and
manifest-backed catalog consistency:

```bash
scripts/bootstrap.sh
python3 scripts/pin_registry.py validate --require-clean-submodules
```

Prepare one candidate locally only from a clean worktree:

```bash
python3 scripts/pin_registry.py update ward
git diff --cached -- README.md modules/security/ward
```

The update command refuses unknown modules, dirty Harness worktrees,
non-fast-forward movement, unrelated staged paths, README drift, and an
upstream `main` that advances while the candidate is being prepared.

## Failure handling and rollback

- No upstream change: the job exits without a branch or PR.
- Existing module automation PR: the module is skipped until that PR is closed
  or merged.
- Non-fast-forward upstream movement: investigate the rewritten upstream branch
  and prepare a manual reviewed pin if it is intentional.
- Existing commit-specific branch without an open PR: inspect or remove that
  stale automation branch manually before retrying.
- Failed upstream or Harness check: fix or explicitly review the failure; the
  updater does not bypass it.

Each generated PR changes one module. Reverting its squash commit restores both
the previous gitlink and the matching README pin references.

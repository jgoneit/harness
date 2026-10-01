#!/usr/bin/env python3
"""Evaluate a pull request against its pre-committed Seal Task outside the agent loop."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


RESULT_SCHEMA = "seal-pr-acceptance-result/v1"
TASK_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
TRAILER_RE = re.compile(r"^Seal-Task:[ \t]*(\S*)[ \t]*$")
TASK_INPUT_PATH = "docs/specs/{name}/task.json"

# `seal complete` exits that reflect the change itself; the Native Agent can act on them.
REJECTIONS = {
    4: ("scope", "changed files outside the Task Scope"),
    5: ("required-check", "a required check failed"),
    6: ("required-check-timeout", "a required check timed out"),
    9: ("source-unstable", "source changed during or after the checks"),
}
REJECTION_MESSAGES = dict(REJECTIONS.values())
EXIT_ACCEPTED, EXIT_REJECTED, EXIT_ERROR = 0, 1, 2


class RecipeError(RuntimeError):
    """Raised when acceptance cannot be evaluated; never an Acceptance decision."""


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def git(cwd: Path, *args: str) -> str:
    result = run(["git", *args], cwd)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RecipeError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def parse_binding(body: str) -> str | None:
    """Return the one Task name bound by `Seal-Task:` trailers, or None when unbound."""
    names = {match.group(1) for line in body.splitlines() if (match := TRAILER_RE.match(line.strip()))}
    if not names:
        return None
    if len(names) > 1:
        raise RecipeError(f"conflicting Seal-Task bindings: {', '.join(sorted(names))}")
    name = names.pop()
    if not TASK_NAME_RE.fullmatch(name):
        raise RecipeError(f"invalid Seal-Task name: {name!r}")
    return name


def seal_json(seal: str, cwd: Path, *args: str) -> tuple[int, dict[str, object] | None]:
    result = run([seal, *args], cwd)
    if result.returncode != 0:
        return result.returncode, None
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.returncode, None
    return result.returncode, document if isinstance(document, dict) else None


def evaluate(repository: Path, seal: str, base: str, head: str, task_name: str) -> dict[str, object]:
    if not TASK_NAME_RE.fullmatch(task_name):
        raise RecipeError(f"invalid Seal-Task name: {task_name!r}")
    root = Path(git(repository, "rev-parse", "--show-toplevel"))
    base_commit = git(root, "rev-parse", "--verify", f"{base}^{{commit}}")
    head_commit = git(root, "rev-parse", "--verify", f"{head}^{{commit}}")
    baseline = git(root, "merge-base", base_commit, head_commit)

    task_path = TASK_INPUT_PATH.format(name=task_name)
    task_input = run(["git", "show", f"{baseline}:{task_path}"], root)
    if task_input.returncode != 0:
        raise RecipeError(f"{task_path} does not exist at baseline {baseline}")
    try:
        task_id = json.loads(task_input.stdout)["id"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RecipeError(f"{task_path} at baseline has no readable Task id") from exc
    if not isinstance(task_id, str):
        raise RecipeError(f"{task_path} at baseline has no readable Task id")

    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "task": task_name,
        "task_input": task_path,
        "task_id": task_id,
        "baseline": baseline,
        "head": head_commit,
    }
    with tempfile.TemporaryDirectory(prefix="seal-pr-acceptance-") as scratch:
        scratch_path = Path(scratch)
        input_file = scratch_path / "task.json"
        input_file.write_text(task_input.stdout, encoding="utf-8")
        workdir = scratch_path / "worktree"
        git(root, "worktree", "add", "--quiet", "--detach", str(workdir), baseline)
        try:
            checkout(workdir, baseline)
            created = run([seal, "task", "create", "--file", str(input_file)], workdir)
            if created.returncode != 0:
                raise RecipeError(f"seal task create exited {created.returncode}: {created.stderr.strip()}")

            checkout(workdir, head_commit)
            verify_exit, verified = seal_json(seal, workdir, "verify", task_id)
            run_id = verified.get("run_id") if verified else None
            if verify_exit != 0 or not isinstance(run_id, str):
                raise RecipeError(f"seal verify exited {verify_exit} without a usable Run id")
            result["run_id"] = run_id

            complete_exit = run([seal, "complete", task_id, "--run-id", run_id], workdir).returncode
            result["seal_complete_exit"] = complete_exit
            _, summary = seal_json(seal, workdir, "run", "show", task_id, "--run-id", run_id)
            _, snapshot = seal_json(seal, workdir, "task", "show", task_id)
        finally:
            git(root, "worktree", "remove", "--force", str(workdir))

    if complete_exit == 0:
        result.update(outcome="accepted", reason="Basic Acceptance passed")
    elif complete_exit in REJECTIONS:
        result.update(outcome="rejected", reason=REJECTIONS[complete_exit][0])
    else:
        result.update(outcome="error", reason=f"seal complete exited {complete_exit}")
    result.update(diagnostics(summary, snapshot))
    return result


def checkout(workdir: Path, commit: str) -> None:
    git(workdir, "checkout", "--quiet", "--detach", commit)
    if (workdir / ".gitmodules").is_file():
        git(workdir, "submodule", "update", "--quiet", "--init", "--recursive")


def diagnostics(summary: dict[str, object] | None, snapshot: dict[str, object] | None) -> dict[str, object]:
    if summary is None:
        return {"diagnostics": "unavailable"}
    argv_by_name = {
        check.get("name"): check.get("argv")
        for check in (snapshot or {}).get("checks", [])
        if isinstance(check, dict)
    }
    failed_required, failed_optional = [], []
    for check in summary.get("checks", []):
        if not isinstance(check, dict) or check.get("passed"):
            continue
        entry = {
            "name": check.get("name"),
            "timed_out": check.get("timed_out"),
            "exit_code": check.get("exit_code"),
            "argv": argv_by_name.get(check.get("name")),
        }
        (failed_required if check.get("required") else failed_optional).append(entry)
    return {
        "failed_required_checks": failed_required,
        "failed_optional_checks": failed_optional,
        "scope_violations": [
            {"path": item.get("path"), "status": item.get("status")}
            for item in summary.get("scope_violations", [])
            if isinstance(item, dict)
        ],
    }


def render_markdown(result: dict[str, object]) -> str:
    outcome = result.get("outcome", "error")
    lines = [f"## Seal PR acceptance: {outcome}", ""]
    if outcome == "rejected":
        message = REJECTION_MESSAGES[str(result["reason"])]
        lines.append(f"The change does not satisfy its pre-committed Task: {message}.")
    elif outcome == "error":
        lines.append(f"Acceptance was not evaluated: {result.get('reason')}.")
        lines.append("This is an operational failure, not a judgment of the change.")
    else:
        lines.append("The change satisfies its pre-committed Task.")
    for violation in result.get("scope_violations", []):
        lines.append(f"- Outside Scope: `{violation['path']}` ({violation['status']})")
    for check in result.get("failed_required_checks", []):
        state = "timed out" if check["timed_out"] else f"exit {check['exit_code']}"
        lines.append(f"- Required check `{check['name']}` failed ({state})")
        if isinstance(check.get("argv"), list):
            lines.append(f"  - Reproduce: `{shlex.join(str(arg) for arg in check['argv'])}`")
    for check in result.get("failed_optional_checks", []):
        lines.append(f"- Optional check `{check['name']}` failed (non-blocking)")
    if "task_input" in result:
        lines += ["", f"Intent: `{result['task_input']}` at baseline `{str(result['baseline'])[:12]}`."]
    if "run_id" in result:
        lines.append(f"Evidence: Task `{result['task_id']}`, Run `{result['run_id']}` (not retained).")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    bind_parser = subparsers.add_parser("bind", help="read the Seal-Task trailer from --body-file")
    bind_parser.add_argument("--body-file", type=Path, required=True)

    accept_parser = subparsers.add_parser("accept", help="evaluate one bound pull request")
    accept_parser.add_argument("--base", required=True, help="base branch commit")
    accept_parser.add_argument("--head", required=True, help="pull request head commit")
    accept_parser.add_argument("--task", required=True, help="bound Task name")
    accept_parser.add_argument("--seal", default="seal", help="Seal executable")
    accept_parser.add_argument("--repository", type=Path, default=Path.cwd())
    accept_parser.add_argument("--summary", type=Path, help="append Markdown feedback here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "bind":
        try:
            name = parse_binding(args.body_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, RecipeError) as exc:
            print(f"seal-pr-acceptance error: {exc}", file=sys.stderr)
            return EXIT_ERROR
        print(f"task={name or ''}")
        return 0

    seal = shutil.which(args.seal)
    try:
        if seal is None:
            raise RecipeError(f"Seal executable not found: {args.seal}")
        result = evaluate(args.repository, seal, args.base, args.head, args.task)
    except RecipeError as exc:
        result = {"schema": RESULT_SCHEMA, "task": args.task, "outcome": "error", "reason": str(exc)}
    print(json.dumps(result, indent=2, sort_keys=True))
    markdown = render_markdown(result)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as summary:
            summary.write(markdown)
    else:
        print(markdown, file=sys.stderr, end="")
    return {"accepted": EXIT_ACCEPTED, "rejected": EXIT_REJECTED}.get(str(result["outcome"]), EXIT_ERROR)


if __name__ == "__main__":
    raise SystemExit(main())

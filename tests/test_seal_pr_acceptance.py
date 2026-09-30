from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "seal_pr_acceptance", ROOT / "recipes/seal-pr-acceptance/seal_pr_acceptance.py"
)
assert SPEC and SPEC.loader
recipe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = recipe
SPEC.loader.exec_module(recipe)

SEAL = os.environ.get("SEAL_BIN") or shutil.which("seal")
ISOLATED_GIT = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "recipe",
    "GIT_AUTHOR_EMAIL": "recipe@example.invalid",
    "GIT_COMMITTER_NAME": "recipe",
    "GIT_COMMITTER_EMAIL": "recipe@example.invalid",
}
CATALOG = {
    "schema_version": 1,
    "checks": {
        "fixed": {
            "argv": ["grep", "-q", "fixed", "src/app.txt"],
            "required": True,
            "timeout_seconds": 30,
        }
    },
}
TASK = {
    "schema_version": 1,
    "id": "fix-app",
    "type": "bugfix",
    "objective": "Fix the app.",
    "scope": ["src/"],
    "checks": ["fixed"],
    "risk": "low",
    "verifier": {"required": False},
}


class BindingTests(unittest.TestCase):
    def test_unbound_body_returns_none(self) -> None:
        self.assertIsNone(recipe.parse_binding("Fixes the app.\n\nSeal-Task is described elsewhere."))

    def test_single_trailer_binds_its_task(self) -> None:
        self.assertEqual(recipe.parse_binding("Summary\n\nSeal-Task: fix-app\n"), "fix-app")

    def test_repeated_identical_trailer_binds_once(self) -> None:
        self.assertEqual(recipe.parse_binding("Seal-Task: fix-app\r\nSeal-Task: fix-app"), "fix-app")

    def test_conflicting_trailers_are_rejected(self) -> None:
        with self.assertRaisesRegex(recipe.RecipeError, "conflicting"):
            recipe.parse_binding("Seal-Task: fix-app\nSeal-Task: other")

    def test_unsafe_name_is_rejected(self) -> None:
        for body in ("Seal-Task: ../escape", "Seal-Task:", "Seal-Task: Fix_App"):
            with self.subTest(body=body), self.assertRaisesRegex(recipe.RecipeError, "invalid"):
                recipe.parse_binding(body)


@unittest.skipUnless(SEAL, "Seal executable not available; set SEAL_BIN or put seal on PATH")
class AcceptanceScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = mock.patch.dict(os.environ, ISOLATED_GIT)
        environment.start()
        self.addCleanup(environment.stop)
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.repository = Path(scratch.name) / "repository"
        self.repository.mkdir()
        self.git("init", "--quiet", "--initial-branch=main")
        self.write("src/app.txt", "broken\n")
        self.write("docs/guide.md", "guide\n")
        self.write(".gitignore", ".seal/tasks/\n.seal/evidence/\n")
        self.write(".seal/checks.json", json.dumps(CATALOG))
        self.write("docs/specs/fix-app/task.json", json.dumps(TASK))
        self.commit("intent")
        self.git("checkout", "--quiet", "-b", "agent")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repository, check=True, text=True, stdout=subprocess.PIPE
        ).stdout.strip()

    def write(self, path: str, text: str) -> None:
        target = self.repository / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> None:
        self.git("add", "--all")
        self.git("commit", "--quiet", "-m", message)

    def accept(self, base: str = "main", task: str = "fix-app") -> tuple[int, dict[str, object], str]:
        summary = self.repository.parent / "summary.md"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = recipe.main(
                [
                    "accept",
                    "--repository", str(self.repository),
                    "--seal", str(SEAL),
                    "--base", base,
                    "--head", "HEAD",
                    "--task", task,
                    "--summary", str(summary),
                ]
            )
        return code, json.loads(stdout.getvalue()), summary.read_text(encoding="utf-8")

    def violation_paths(self, result: dict[str, object]) -> list[object]:
        return [item["path"] for item in result["scope_violations"]]

    def test_in_scope_change_is_accepted_without_touching_the_checkout(self) -> None:
        self.write("src/app.txt", "fixed\n")
        self.commit("fix")
        code, result, summary = self.accept()
        self.assertEqual((code, result["outcome"]), (0, "accepted"))
        self.assertIn("satisfies its pre-committed Task", summary)
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD"), "agent")
        self.assertEqual(len(self.git("worktree", "list", "--porcelain").split("\n\n")), 1)

    def test_out_of_scope_change_is_rejected(self) -> None:
        self.write("src/app.txt", "fixed\n")
        self.write("docs/guide.md", "edited\n")
        self.commit("fix and edit docs")
        code, result, summary = self.accept()
        self.assertEqual((code, result["outcome"], result["reason"]), (1, "rejected", "scope"))
        self.assertEqual(self.violation_paths(result), ["docs/guide.md"])
        self.assertIn("Outside Scope: `docs/guide.md`", summary)

    def test_weakened_check_catalog_is_rejected(self) -> None:
        self.write(".seal/checks.json", json.dumps({**CATALOG, "checks": {"fixed": {"argv": ["true"]}}}))
        self.commit("weaken the check")
        code, result, _ = self.accept()
        self.assertEqual((code, result["reason"]), (1, "scope"))
        self.assertIn(".seal/checks.json", self.violation_paths(result))

    def test_missing_fix_reports_a_reproducible_required_check(self) -> None:
        self.write("src/app.txt", "touched\n")
        self.commit("no fix")
        code, result, summary = self.accept()
        self.assertEqual((code, result["reason"]), (1, "required-check"))
        self.assertEqual(result["failed_required_checks"][0]["argv"], CATALOG["checks"]["fixed"]["argv"])
        self.assertIn("Reproduce: `grep -q fixed src/app.txt`", summary)

    def test_advanced_base_branch_uses_the_merge_base(self) -> None:
        intent = self.git("rev-parse", "HEAD")
        self.write("src/app.txt", "fixed\n")
        self.commit("fix")
        self.git("checkout", "--quiet", "main")
        self.write("docs/guide.md", "main moved\n")
        self.commit("main moved")
        self.git("checkout", "--quiet", "agent")
        code, result, _ = self.accept()
        self.assertEqual((code, result["outcome"], result["baseline"]), (0, "accepted", intent))

    def test_task_input_is_read_from_the_baseline(self) -> None:
        self.write("docs/specs/fix-app/task.json", json.dumps({**TASK, "scope": ["src/", "docs/"]}))
        self.write("src/app.txt", "fixed\n")
        self.write("docs/guide.md", "edited\n")
        self.commit("widen my own Task")
        code, result, _ = self.accept()
        self.assertEqual((code, result["reason"]), (1, "scope"))
        self.assertIn("docs/guide.md", self.violation_paths(result))

    def test_task_input_absent_at_baseline_is_an_error(self) -> None:
        self.write("docs/specs/late/task.json", json.dumps({**TASK, "id": "late"}))
        self.write("src/app.txt", "fixed\n")
        self.commit("intent written after the fact")
        code, result, summary = self.accept(task="late")
        self.assertEqual((code, result["outcome"]), (2, "error"))
        self.assertIn("does not exist at baseline", str(result["reason"]))
        self.assertIn("not a judgment of the change", summary)

    def test_unsafe_task_name_is_an_error(self) -> None:
        code, result, _ = self.accept(task="../escape")
        self.assertEqual((code, result["outcome"]), (2, "error"))


if __name__ == "__main__":
    unittest.main()

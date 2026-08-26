from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pin_registry", ROOT / "scripts/pin_registry.py"
)
assert SPEC and SPEC.loader
pin_registry = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pin_registry
SPEC.loader.exec_module(pin_registry)


class PinRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = pin_registry.Module(
            module_id="ward",
            name="Ward",
            plane="security",
            status="experimental",
            repository="https://github.com/jgoneit/ward",
            path="modules/security/ward",
            raw={},
        )
        self.old_sha = "1" * 40
        self.new_sha = "2" * 40

    def test_synchronize_readme_updates_only_current_module_references(self) -> None:
        other_sha = "3" * 40
        text = (
            "| Ward | Security | Experimental | <https://github.com/jgoneit/ward> | "
            f"`{self.old_sha}` | `modules/security/ward` |\n"
            "- [Ward README](https://github.com/jgoneit/ward/tree/"
            f"{self.old_sha}#readme)\n"
            f"Historical unrelated SHA: {self.old_sha}\n"
            "| Seal | Acceptance | Experimental | <https://github.com/jgoneit/seal> | "
            f"`{other_sha}` | `modules/acceptance/seal` |\n"
        )

        updated = pin_registry.synchronize_readme(
            text, self.module, self.old_sha, self.new_sha
        )

        self.assertEqual(updated.count(self.new_sha), 2)
        self.assertIn(f"Historical unrelated SHA: {self.old_sha}", updated)
        self.assertIn(other_sha, updated)

    def test_synchronize_readme_rejects_missing_recorded_pin(self) -> None:
        with self.assertRaises(pin_registry.PinError):
            pin_registry.synchronize_readme(
                "# no current pin\n", self.module, self.old_sha, self.new_sha
            )

    def test_repository_url_normalization(self) -> None:
        expected = "https://github.com/jgoneit/ward"
        self.assertEqual(pin_registry.normalize_repository(expected + ".git"), expected)
        self.assertEqual(pin_registry.normalize_repository("git@github.com:jgoneit/ward.git"), expected)
        self.assertEqual(pin_registry.expected_submodule_url(expected), "../ward.git")
        self.assertEqual(
            pin_registry.expected_submodule_url("https://github.com/other/ward"),
            "https://github.com/other/ward.git",
        )

    def test_live_registry_is_consistent(self) -> None:
        pin_registry.Registry(ROOT).validate()

    def test_update_stages_one_fast_forward_gitlink_and_readme(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            owner_root = temporary_root / "owner"
            owner_root.mkdir()
            module_worktree = temporary_root / "ward-worktree"
            harness_root = owner_root / "harness"
            module_bare = owner_root / "ward.git"
            harness_bare = owner_root / "harness.git"

            self._git(temporary_root, "init", "--bare", str(harness_bare))
            self._git(temporary_root, "init", "-b", "main", str(module_worktree))
            self._configure_identity(module_worktree)
            (module_worktree / "README.md").write_text("old\n", encoding="utf-8")
            self._git(module_worktree, "add", "README.md")
            self._git(module_worktree, "commit", "-m", "initial")
            old_sha = self._git(module_worktree, "rev-parse", "HEAD")
            self._git(temporary_root, "clone", "--bare", str(module_worktree), str(module_bare))

            (module_worktree / "README.md").write_text("new\n", encoding="utf-8")
            self._git(module_worktree, "commit", "-am", "advance")
            new_sha = self._git(module_worktree, "rev-parse", "HEAD")
            self._git(module_worktree, "remote", "add", "origin", str(module_bare))
            self._git(module_worktree, "push", "origin", "main")

            self._git(temporary_root, "init", "-b", "main", str(harness_root))
            self._configure_identity(harness_root)
            self._git(harness_root, "remote", "add", "origin", str(harness_bare))
            self._git(
                harness_root,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "../ward.git",
                "modules/security/ward",
            )
            self._git(harness_root / "modules/security/ward", "checkout", "--detach", old_sha)
            (harness_root / "catalog").mkdir()
            (harness_root / "catalog/modules.json").write_text(
                json_text(
                    {
                        "schema_version": 1,
                        "modules": [
                            {
                                "id": "ward",
                                "name": "Ward",
                                "plane": "security",
                                "status": "experimental",
                                "repository": "https://github.com/jgoneit/ward",
                                "submodule_path": "modules/security/ward",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (harness_root / "README.md").write_text(
                "| Module | Plane | Status | Repository | Pinned commit | Workspace path |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| Ward | Security | Experimental | <https://github.com/jgoneit/ward> | "
                f"`{old_sha}` | `modules/security/ward` |\n"
                f"- [Ward README](https://github.com/jgoneit/ward/tree/{old_sha}#readme)\n",
                encoding="utf-8",
            )
            self._git(harness_root, "add", ".")
            self._git(harness_root, "commit", "-m", "initial harness")
            base_sha = self._git(harness_root, "rev-parse", "HEAD")

            module_checkout = harness_root / "modules/security/ward"
            self._git(harness_root, "config", "submodule.modules/security/ward.ignore", "all")
            self._git(module_checkout, "config", "status.showUntrackedFiles", "no")
            local_file = module_checkout / "LOCAL-USER-FILE.txt"
            local_file.write_text("local user change\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"GIT_ALLOW_PROTOCOL": "file"}):
                with self.assertRaises(pin_registry.PinError):
                    pin_registry.Registry(harness_root).update("ward")
            self.assertEqual(local_file.read_text(encoding="utf-8"), "local user change\n")
            local_file.unlink()
            self._git(module_checkout, "config", "--unset", "status.showUntrackedFiles")
            self._git(harness_root, "config", "--unset", "submodule.modules/security/ward.ignore")

            with mock.patch.dict(os.environ, {"GIT_ALLOW_PROTOCOL": "file"}):
                registry = pin_registry.Registry(harness_root)
                result = registry.update("ward")

            self.assertTrue(result["changed"])
            self.assertEqual(result["old_commit"], old_sha)
            self.assertEqual(result["new_commit"], new_sha)
            self.assertEqual(
                set(self._git(harness_root, "diff", "--cached", "--name-only").splitlines()),
                {"README.md", "modules/security/ward"},
            )
            self.assertNotIn(old_sha, (harness_root / "README.md").read_text(encoding="utf-8"))
            self.assertEqual(
                self._git(harness_root / "modules/security/ward", "rev-parse", "HEAD"),
                new_sha,
            )
            self._git(harness_root, "commit", "-m", "advance ward pin")
            registry.validate_update_diff(base_sha)

    @staticmethod
    def _git(cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.strip()

    @classmethod
    def _configure_identity(cls, root: Path) -> None:
        cls._git(root, "config", "user.name", "Pin Test")
        cls._git(root, "config", "user.email", "pin-test@example.com")


def json_text(value: object) -> str:
    import json

    return json.dumps(value, indent=2) + "\n"


if __name__ == "__main__":
    unittest.main()

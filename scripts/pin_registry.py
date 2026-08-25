#!/usr/bin/env python3
"""Validate and advance Harness submodule pins without weakening exact pins."""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


SHA_RE = re.compile(r"[0-9a-f]{40}")
SAFE_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
HARNESS_GITHUB_OWNER = "jgoneit"


class PinError(RuntimeError):
    """Raised when registry or update invariants are violated."""


@dataclass(frozen=True)
class Module:
    module_id: str
    name: str
    plane: str
    status: str
    repository: str
    path: str
    raw: dict[str, object]


def run_git(
    root: Path,
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
    preserve_output: bool = False,
) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd or root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PinError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout if preserve_output else result.stdout.strip()


def normalize_repository(url: str) -> str:
    value = url.strip().rstrip("/")
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.removeprefix("git@github.com:")
    elif value.startswith("ssh://git@github.com/"):
        value = "https://github.com/" + value.removeprefix("ssh://git@github.com/")
    if value.endswith(".git"):
        value = value[:-4]
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise PinError(f"unsupported repository URL: {url}")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise PinError(f"repository URL must identify one GitHub repository: {url}")
    return f"https://github.com/{parts[0]}/{parts[1]}"


def expected_submodule_url(repository: str) -> str:
    normalized = normalize_repository(repository)
    owner, name = urlparse(normalized).path.strip("/").split("/", 1)
    if owner == HARNESS_GITHUB_OWNER:
        return f"../{name}.git"
    return normalized + ".git"


def strip_markdown(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        value = value[1:-1]
    if len(value) >= 2 and value[0] == "<" and value[-1] == ">":
        value = value[1:-1]
    return value


def write_atomic(path: Path, text: str) -> None:
    mode = path.stat().st_mode
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def synchronize_readme(text: str, module: Module, old_sha: str, new_sha: str) -> str:
    if not SHA_RE.fullmatch(old_sha) or not SHA_RE.fullmatch(new_sha):
        raise PinError("README synchronization requires full lowercase commit SHAs")

    replacements = 0
    updated_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        table_reference = line.lstrip().startswith("|") and f"`{module.path}`" in line
        repository_reference = module.repository in line
        if old_sha in line and (table_reference or repository_reference):
            replacements += line.count(old_sha)
            line = line.replace(old_sha, new_sha)
        updated_lines.append(line)

    if replacements == 0:
        raise PinError(
            f"README does not contain the recorded pin for {module.module_id}: {old_sha}"
        )
    return "".join(updated_lines)


class Registry:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.catalog_path = self.root / "catalog/modules.json"
        self.gitmodules_path = self.root / ".gitmodules"
        self.readme_path = self.root / "README.md"
        self.modules = self._load_modules()
        self.by_id = {module.module_id: module for module in self.modules}
        self.by_path = {module.path: module for module in self.modules}

    def _load_modules(self) -> list[Module]:
        try:
            catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PinError(f"cannot read catalog: {exc}") from exc

        records = catalog.get("modules") if isinstance(catalog, dict) else None
        if not isinstance(records, list) or not records:
            raise PinError("catalog.modules must be a non-empty list")

        modules: list[Module] = []
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                raise PinError("each catalog module must be an object")
            required = ("id", "name", "plane", "status", "repository", "submodule_path")
            if any(not isinstance(record.get(key), str) for key in required):
                raise PinError(f"catalog module is missing string fields: {record!r}")
            module_id = str(record["id"])
            path = str(record["submodule_path"])
            pure_path = PurePosixPath(path)
            if not SAFE_ID_RE.fullmatch(module_id):
                raise PinError(f"unsafe module id: {module_id}")
            if pure_path.is_absolute() or ".." in pure_path.parts or not path.startswith("modules/"):
                raise PinError(f"unsafe submodule path: {path}")
            if module_id in seen_ids or path in seen_paths:
                raise PinError(f"duplicate module id or path: {module_id}, {path}")
            seen_ids.add(module_id)
            seen_paths.add(path)
            modules.append(
                Module(
                    module_id=module_id,
                    name=str(record["name"]),
                    plane=str(record["plane"]),
                    status=str(record["status"]),
                    repository=normalize_repository(str(record["repository"])),
                    path=path,
                    raw=record,
                )
            )
        return modules

    def module(self, module_id: str) -> Module:
        try:
            return self.by_id[module_id]
        except KeyError as exc:
            choices = ", ".join(sorted(self.by_id))
            raise PinError(f"unknown module {module_id!r}; expected one of: {choices}") from exc

    def gitmodules(self) -> dict[str, str]:
        parser = configparser.RawConfigParser(interpolation=None, strict=True)
        try:
            with self.gitmodules_path.open(encoding="utf-8") as handle:
                parser.read_file(handle)
        except (OSError, configparser.Error) as exc:
            raise PinError(f"cannot read .gitmodules: {exc}") from exc

        entries: dict[str, str] = {}
        for section in parser.sections():
            match = re.fullmatch(r'submodule "(.+)"', section)
            if not match or not parser.has_option(section, "path") or not parser.has_option(section, "url"):
                raise PinError(f"invalid .gitmodules section: {section}")
            if set(parser.options(section)) != {"path", "url"}:
                raise PinError(
                    f".gitmodules may configure only exact-pin path and url fields: {section}"
                )
            path = parser.get(section, "path").strip()
            if match.group(1) != path:
                raise PinError(f"submodule section name must equal its path: {section}")
            if path in entries:
                raise PinError(f"duplicate .gitmodules path: {path}")
            entries[path] = parser.get(section, "url").strip()
        return entries

    def gitlinks(self, revision: str | None = None) -> dict[str, str]:
        if revision is None:
            output = run_git(self.root, "ls-files", "--stage")
        else:
            output = run_git(self.root, "ls-tree", "-r", revision)
        links: dict[str, str] = {}
        for line in output.splitlines():
            try:
                metadata, path = line.split("\t", 1)
                fields = metadata.split()
                mode = fields[0]
                sha = fields[1] if revision is None else fields[2]
            except (ValueError, IndexError) as exc:
                raise PinError(f"cannot parse git tree entry: {line}") from exc
            if mode == "160000":
                links[path] = sha
        return links

    def readme_rows(self, text: str) -> dict[str, list[str]]:
        rows: dict[str, list[str]] = {}
        for line in text.splitlines():
            if not line.startswith("|"):
                continue
            cells = [strip_markdown(cell) for cell in line.strip().strip("|").split("|")]
            if len(cells) != 6 or not SHA_RE.fullmatch(cells[4]):
                continue
            path = cells[5]
            if path in rows:
                raise PinError(f"duplicate README module row: {path}")
            rows[path] = cells
        return rows

    def validate(self, require_clean_submodules: bool = False) -> None:
        module_paths = set(self.by_path)
        gitmodules = self.gitmodules()
        gitlinks = self.gitlinks()
        if set(gitmodules) != module_paths:
            raise PinError("catalog and .gitmodules submodule paths differ")
        if set(gitlinks) != module_paths:
            raise PinError("catalog and mode-160000 gitlink paths differ")

        readme = self.readme_path.read_text(encoding="utf-8")
        rows = self.readme_rows(readme)
        if set(rows) != module_paths:
            raise PinError("catalog and README module table paths differ")

        for module in self.modules:
            expected_url = expected_submodule_url(module.repository)
            if gitmodules[module.path] != expected_url:
                raise PinError(
                    f".gitmodules URL for {module.module_id} must be {expected_url}"
                )
            name, plane, status, repository, readme_sha, path = rows[module.path]
            expected_row = (
                module.name,
                module.plane.title(),
                module.status.title(),
                module.repository,
                gitlinks[module.path],
                module.path,
            )
            if (name, plane, status, normalize_repository(repository), readme_sha, path) != expected_row:
                raise PinError(f"README table row is stale for {module.module_id}")

            pinned_link_pattern = re.compile(
                re.escape(module.repository) + r"/tree/([0-9a-f]{40})(?:[#/)])"
            )
            for linked_sha in pinned_link_pattern.findall(readme):
                if linked_sha != gitlinks[module.path]:
                    raise PinError(f"README pinned link is stale for {module.module_id}")

            if require_clean_submodules:
                self._validate_initialized_module(module, gitlinks[module.path])

    def _validate_initialized_module(self, module: Module, recorded_sha: str) -> None:
        module_root = self.root / module.path
        if not (module_root / ".git").exists():
            raise PinError(f"submodule is not initialized: {module.path}")
        checked_out = run_git(self.root, "rev-parse", "HEAD", cwd=module_root)
        if checked_out != recorded_sha:
            raise PinError(f"submodule checkout does not match gitlink: {module.path}")
        if run_git(
            self.root,
            "status",
            "--porcelain",
            "--untracked-files=all",
            cwd=module_root,
        ):
            raise PinError(f"submodule worktree is dirty: {module.path}")

        manifest_name = module.raw.get("artifacts", {})
        if not isinstance(manifest_name, dict) or "module_manifest" not in manifest_name:
            return
        manifest_path = module_root / str(manifest_name["module_manifest"])
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PinError(f"cannot read module manifest for {module.module_id}: {exc}") from exc
        shared_keys = (
            "id",
            "name",
            "description",
            "plane",
            "status",
            "kind",
            "phase",
            "invocation_owners",
            "requires_terminal_outcome",
            "self_activates",
            "auto_invokes_modules",
            "mutates_user_task",
        )
        for key in shared_keys:
            if key in module.raw and module.raw[key] != manifest.get(key):
                raise PinError(f"catalog and manifest disagree for {module.module_id}.{key}")
        catalog_artifacts = {
            key: value for key, value in manifest_name.items() if key != "module_manifest"
        }
        if catalog_artifacts != manifest.get("artifacts"):
            raise PinError(f"catalog and manifest artifacts disagree for {module.module_id}")

    def validate_update_diff(self, base: str) -> None:
        changed = set(run_git(self.root, "diff", "--name-only", f"{base}...HEAD").splitlines())
        changed_modules = changed.intersection(self.by_path)
        if len(changed_modules) != 1:
            raise PinError("automated pin PR must change exactly one module gitlink")
        path = next(iter(changed_modules))
        if changed != {"README.md", path}:
            raise PinError("automated pin PR may change only README.md and one module gitlink")

        module = self.by_path[path]
        old_links = self.gitlinks(base)
        new_links = self.gitlinks("HEAD")
        old_sha, new_sha = old_links.get(path), new_links.get(path)
        if not old_sha or not new_sha or old_sha == new_sha:
            raise PinError("automated pin PR must advance the selected gitlink")
        base_readme = run_git(
            self.root, "show", f"{base}:README.md", preserve_output=True
        )
        expected = synchronize_readme(base_readme, module, old_sha, new_sha)
        actual = self.readme_path.read_text(encoding="utf-8")
        if actual != expected:
            raise PinError("README diff contains changes other than the selected pin synchronization")

        module_root = self.root / path
        self._validate_initialized_module(module, new_sha)
        ancestry = subprocess.run(
            ["git", "merge-base", "--is-ancestor", old_sha, new_sha],
            cwd=module_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if ancestry.returncode != 0:
            raise PinError("automated pin PR does not move the gitlink fast-forward")
        remote_line = run_git(
            self.root,
            "ls-remote",
            "origin",
            "refs/heads/main",
            cwd=module_root,
        )
        remote_sha = remote_line.split()[0] if remote_line else ""
        if remote_sha != new_sha:
            raise PinError("automated pin PR does not target the current upstream main")

    def update(self, module_id: str) -> dict[str, object]:
        self.validate()
        module = self.module(module_id)
        if run_git(self.root, "status", "--porcelain", "--untracked-files=all"):
            raise PinError("refusing to update a dirty Harness worktree")

        old_sha = self.gitlinks()[module.path]
        run_git(self.root, "submodule", "sync", "--", module.path)
        run_git(self.root, "submodule", "update", "--init", "--", module.path)
        module_root = self.root / module.path
        self._validate_initialized_module(module, old_sha)
        run_git(
            self.root,
            "fetch",
            "--no-tags",
            "origin",
            "refs/heads/main",
            cwd=module_root,
        )
        new_sha = run_git(self.root, "rev-parse", "FETCH_HEAD^{commit}", cwd=module_root)
        result: dict[str, object] = {
            "changed": False,
            "module": module.module_id,
            "name": module.name,
            "repository": module.repository,
            "path": module.path,
            "old_commit": old_sha,
            "new_commit": new_sha,
        }
        if new_sha == old_sha:
            return result

        ancestry = subprocess.run(
            ["git", "merge-base", "--is-ancestor", old_sha, new_sha],
            cwd=module_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if ancestry.returncode != 0:
            raise PinError(
                f"refusing non-fast-forward pin movement for {module.module_id}: "
                f"{old_sha} -> {new_sha}"
            )

        original_readme = self.readme_path.read_text(encoding="utf-8")
        staged = False
        try:
            run_git(self.root, "checkout", "--detach", new_sha, cwd=module_root)
            updated_readme = synchronize_readme(original_readme, module, old_sha, new_sha)
            write_atomic(self.readme_path, updated_readme)
            run_git(self.root, "add", "--", module.path, "README.md")
            staged = True
            self.validate()
            changed = set(run_git(self.root, "diff", "--cached", "--name-only").splitlines())
            if changed != {module.path, "README.md"}:
                raise PinError("staged update is not limited to the gitlink and README")
            run_git(self.root, "diff", "--cached", "--check")
            remote_line = run_git(
                self.root,
                "ls-remote",
                "origin",
                "refs/heads/main",
                cwd=module_root,
            )
            remote_sha = remote_line.split()[0] if remote_line else ""
            if remote_sha != new_sha:
                raise PinError("upstream main advanced during pin preparation; rerun the update")
        except Exception:
            if staged:
                run_git(self.root, "reset", "--quiet", "--", module.path, "README.md", check=False)
            write_atomic(self.readme_path, original_readme)
            run_git(self.root, "checkout", "--detach", old_sha, cwd=module_root, check=False)
            raise

        result["changed"] = True
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list catalog module ids")
    list_parser.add_argument("--json", action="store_true", dest="as_json")
    list_parser.add_argument("--module", help="select and validate one module id")

    validate_parser = subparsers.add_parser("validate", help="validate pin consistency")
    validate_parser.add_argument("--require-clean-submodules", action="store_true")

    update_parser = subparsers.add_parser("update", help="stage one fast-forward main pin update")
    update_parser.add_argument("module")

    diff_parser = subparsers.add_parser(
        "validate-update-diff", help="validate the exact scope of an automated pin PR"
    )
    diff_parser.add_argument("--base", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry = Registry(args.root)
        if args.command == "list":
            module_ids = [registry.module(args.module).module_id] if args.module else [
                module.module_id for module in registry.modules
            ]
            print(json.dumps(module_ids) if args.as_json else "\n".join(module_ids))
        elif args.command == "validate":
            registry.validate(args.require_clean_submodules)
            print("pin registry validation passed")
        elif args.command == "update":
            print(json.dumps(registry.update(args.module), sort_keys=True))
        elif args.command == "validate-update-diff":
            registry.validate_update_diff(args.base)
            print("automated pin diff validation passed")
        else:
            raise AssertionError(f"unhandled command: {args.command}")
    except PinError as exc:
        print(f"pin registry error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

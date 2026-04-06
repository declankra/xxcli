"""Git-aware work context collection for digest scoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only used on Python < 3.11
    tomllib = None


@dataclass
class WorkContext:
    repo_name: str
    branch: str
    git_log: str
    git_diff_stat: str
    readme_excerpt: str
    deps_summary: str
    changed_files: list[str]


def build_work_context(repo_path: str) -> WorkContext:
    """Build repo context for prompt construction."""
    target = Path(repo_path).expanduser()
    repo_name = target.resolve(strict=False).name or target.name or str(target)
    if not _is_git_repo(target):
        return WorkContext(
            repo_name=repo_name,
            branch="",
            git_log="",
            git_diff_stat="",
            readme_excerpt=_read_readme_excerpt(target),
            deps_summary=_summarize_dependencies(target),
            changed_files=[],
        )

    branch = _run_git(target, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
    git_log = _run_git(target, ["git", "log", "--oneline", "-n", "20"])
    git_diff_stat = _run_git(target, ["git", "diff", "--stat", "HEAD"])
    changed_files = _collect_changed_files(target)

    return WorkContext(
        repo_name=repo_name,
        branch=branch.strip(),
        git_log=git_log.strip(),
        git_diff_stat=git_diff_stat.strip(),
        readme_excerpt=_read_readme_excerpt(target),
        deps_summary=_summarize_dependencies(target),
        changed_files=changed_files,
    )


def format_context_for_prompt(ctx: WorkContext) -> str:
    """Format work context into prompt-ready plain text."""
    changed = ", ".join(ctx.changed_files) if ctx.changed_files else "(none)"
    return (
        f"Repository: {ctx.repo_name}\n"
        f"Branch: {ctx.branch or '(not a git repo)'}\n\n"
        f"Recent commits:\n{ctx.git_log or '(none)'}\n\n"
        f"Uncommitted changes:\n{ctx.git_diff_stat or '(none)'}\n\n"
        f"Recently changed files:\n{changed}\n\n"
        f"Dependencies:\n{ctx.deps_summary or '(none found)'}\n\n"
        f"README excerpt:\n{ctx.readme_excerpt or '(none found)'}"
    )


def _is_git_repo(path: Path) -> bool:
    return _run_git(path, ["git", "rev-parse", "--show-toplevel"]).strip() != ""


def _run_git(path: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            args,
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _read_readme_excerpt(path: Path, max_lines: int = 200) -> str:
    readme_path = path / "README.md"
    if not readme_path.exists():
        return ""
    try:
        with readme_path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()[:max_lines]
    except OSError:
        return ""
    return "".join(lines).strip()


def _summarize_dependencies(path: Path) -> str:
    pyproject_path = path / "pyproject.toml"
    if pyproject_path.exists():
        parsed = _load_pyproject(pyproject_path)
        if parsed:
            dependencies = parsed.get("project", {}).get("dependencies", [])
            if dependencies:
                return "\n".join(f"- {dependency}" for dependency in dependencies)

    requirements_path = path / "requirements.txt"
    if requirements_path.exists():
        try:
            with requirements_path.open("r", encoding="utf-8") as handle:
                requirements = [
                    line.strip()
                    for line in handle
                    if line.strip() and not line.lstrip().startswith("#")
                ]
        except OSError:
            requirements = []
        if requirements:
            return "\n".join(f"- {requirement}" for requirement in requirements)

    return ""


def _load_pyproject(path: Path) -> dict:
    if tomllib is None:
        return {}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _collect_changed_files(path: Path) -> list[str]:
    current = _run_git(path, ["git", "diff", "--name-only", "HEAD"])
    files = [line.strip() for line in current.splitlines() if line.strip()]
    if files:
        return files[:20]

    recent = _run_git(path, ["git", "log", "--name-only", "--pretty=format:", "-n", "5"])
    deduped: list[str] = []
    seen = set()
    for line in recent.splitlines():
        name = line.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(name)
        if len(deduped) >= 20:
            break
    return deduped

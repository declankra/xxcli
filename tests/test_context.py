from pathlib import Path

from xxcli.context import build_work_context, format_context_for_prompt


def test_build_work_context_for_repo_root():
    ctx = build_work_context(".")
    assert ctx.repo_name == "xxcli"
    assert ctx.branch
    assert ctx.git_log
    assert ctx.deps_summary


def test_build_work_context_for_non_git_dir(tmp_path: Path):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    ctx = build_work_context(str(scratch))
    assert ctx.repo_name == "scratch"
    assert ctx.branch == ""
    assert ctx.git_log == ""
    assert ctx.changed_files == []


def test_format_context_for_prompt_non_empty():
    ctx = build_work_context(".")
    rendered = format_context_for_prompt(ctx)
    assert "Repository: xxcli" in rendered
    assert "Dependencies:" in rendered

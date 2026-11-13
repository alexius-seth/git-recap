import subprocess
from pathlib import Path

from git_recap.git_ops import get_repo_activity
from git_recap.scanner import find_git_repos
from git_recap.summarizer import append_to_log_file, filter_and_format_commits, render_markdown


def _init_temp_repo(repo_dir: Path) -> None:
    """Initialize a local git repo with user config for deterministic tests."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test Dev"], cwd=repo_dir, check=True)


def test_scanner_finds_repos_and_skips_ignored_dirs(tmp_path: Path) -> None:
    app_repo = tmp_path / "my-app"
    ignored_repo = tmp_path / "node_modules" / "hidden-pkg"

    _init_temp_repo(app_repo)
    _init_temp_repo(ignored_repo)

    repos = find_git_repos(tmp_path)
    assert repos == [app_repo.resolve()]


def test_git_ops_extracts_commits_stats_and_wip(tmp_path: Path) -> None:
    repo = tmp_path / "sample-project"
    _init_temp_repo(repo)

    sample_file = repo / "main.py"
    sample_file.write_text("print('hello')\nprint('world')\n", encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "feat: add greeting output"], cwd=repo, check=True, capture_output=True)

    # Create an uncommitted file to test WIP detection
    (repo / "notes.txt").write_text("draft", encoding="utf-8")

    activity = get_repo_activity(repo, hours=24)
    assert activity is not None
    assert activity.repo_name == "sample-project"
    assert activity.uncommitted_count == 1
    assert len(activity.commits) == 1

    commit = activity.commits[0]
    assert commit.message == "feat: add greeting output"
    assert commit.files_changed == 1
    assert commit.insertions == 2
    assert commit.deletions == 0


def test_summarizer_filters_noise_and_cleans_prefixes(tmp_path: Path) -> None:
    repo = tmp_path / "cleanup-repo"
    _init_temp_repo(repo)

    for idx, msg in enumerate(["wip", "fix: resolve login bug", "fix: resolve login bug"]):
        (repo / "a.txt").write_text(f"{idx}: {msg}", encoding="utf-8")
        subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=repo, check=True, capture_output=True)

    activity = get_repo_activity(repo, hours=24)
    assert activity is not None

    cleaned = filter_and_format_commits(activity.commits, hide_noise=True, strip_prefix=True)
    assert len(cleaned) == 1
    assert cleaned[0].message == "Resolve login bug"


def test_save_appends_markdown_journal(tmp_path: Path) -> None:
    repo = tmp_path / "journal-repo"
    _init_temp_repo(repo)

    (repo / "README.md").write_text("# Test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "docs: add readme"], cwd=repo, check=True, capture_output=True)

    activity = get_repo_activity(repo, hours=24)
    assert activity is not None

    md = render_markdown([activity], hours=24, show_stats=True)
    log_path = tmp_path / "logs" / "recap-log.md"
    saved = append_to_log_file(md, log_path=log_path)

    content = saved.read_text(encoding="utf-8")
    assert "### Git Recap (Last 24 hours)" in content
    assert "**journal-repo**" in content
    assert "(1 file, +1 / -0)" in content
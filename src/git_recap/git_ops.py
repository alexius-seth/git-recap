import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommitInfo:
    short_hash: str
    message: str
    branch_ref: str


@dataclass
class RepoActivity:
    repo_name: str
    repo_path: Path
    commits: list[CommitInfo]
    uncommitted_count: int


def _run_git(repo_path: Path, args: list[str]) -> str:
    """Execute a git command safely and return stripped stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_git_author_email(repo_path: Path) -> str:
    """Get the configured user.email for the repository."""
    return _run_git(repo_path, ["config", "user.email"])


def get_repo_activity(
    repo_path: Path,
    hours: int = 24,
    all_authors: bool = False,
) -> RepoActivity | None:
    """Collect commits within the time window and check for uncommitted changes."""
    log_args = [
        "log",
        "--all",
        f"--since={hours} hours ago",
        "--no-merges",
        "--pretty=format:%h|%s|%D",
    ]

    if not all_authors:
        email = get_git_author_email(repo_path)
        if email:
            log_args.append(f"--author={email}")

    raw_log = _run_git(repo_path, log_args)
    commits: list[CommitInfo] = []

    if raw_log:
        for line in raw_log.splitlines():
            parts = line.split("|", maxsplit=2)
            if len(parts) >= 2:
                commits.append(
                    CommitInfo(
                        short_hash=parts[0],
                        message=parts[1].strip(),
                        branch_ref=parts[2].strip() if len(parts) == 3 else "",
                    )
                )

    status_output = _run_git(repo_path, ["status", "--short"])
    uncommitted_count = len(status_output.splitlines()) if status_output else 0

    if not commits and uncommitted_count == 0:
        return None

    return RepoActivity(
        repo_name=repo_path.name,
        repo_path=repo_path,
        commits=commits,
        uncommitted_count=uncommitted_count,
    )
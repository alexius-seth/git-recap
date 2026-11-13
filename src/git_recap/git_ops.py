import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

STAT_PATTERN = re.compile(
    r"(?:(\d+)\s+files?\s+changed)?"
    r"(?:,\s*(\d+)\s+insertions?\(\+\))?"
    r"(?:,\s*(\d+)\s+deletions?\(-\))?"
)


@dataclass
class CommitInfo:
    short_hash: str
    message: str
    branch_ref: str
    date: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


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


def _parse_branch_label(raw_ref: str) -> str:
    """Extract a readable branch name from git %D decoration output."""
    if not raw_ref:
        return ""
    for part in raw_ref.split(","):
        cleaned = part.strip()
        if cleaned.startswith("HEAD -> "):
            return cleaned.replace("HEAD -> ", "", 1)
        if not cleaned.startswith("tag:") and "/" not in cleaned:
            return cleaned
    return raw_ref.split(",")[0].strip()


def _parse_shortstat(stat_line: str) -> tuple[int, int, int]:
    """Parse git --shortstat line into (files_changed, insertions, deletions)."""
    match = STAT_PATTERN.search(stat_line)
    if not match:
        return 0, 0, 0
    files = int(match.group(1) or 0)
    ins = int(match.group(2) or 0)
    dels = int(match.group(3) or 0)
    return files, ins, dels


def get_repo_activity(
    repo_path: Path,
    hours: int = 24,
    all_authors: bool = False,
) -> RepoActivity | None:
    """Collect commits, diff stats, and uncommitted changes within the time window."""
    log_args = [
        "log",
        "--all",
        f"--since={hours} hours ago",
        "--no-merges",
        "--shortstat",
        "--date=short",
        "--pretty=format:---COMMIT---|%h|%ad|%s|%D",
    ]

    if not all_authors:
        email = get_git_author_email(repo_path)
        if email:
            log_args.append(f"--author={email}")

    raw_log = _run_git(repo_path, log_args)
    commits: list[CommitInfo] = []

    if raw_log:
        blocks = raw_log.split("---COMMIT---|")
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = [line.strip() for line in block.splitlines() if line.strip()]
            header_parts = lines[0].split("|", maxsplit=3)
            if len(header_parts) < 3:
                continue

            files_changed, insertions, deletions = 0, 0, 0
            if len(lines) > 1:
                files_changed, insertions, deletions = _parse_shortstat(lines[1])

            raw_ref = header_parts[3].strip() if len(header_parts) == 4 else ""
            commits.append(
                CommitInfo(
                    short_hash=header_parts[0],
                    date=header_parts[1].strip(),
                    message=header_parts[2].strip(),
                    branch_ref=_parse_branch_label(raw_ref),
                    files_changed=files_changed,
                    insertions=insertions,
                    deletions=deletions,
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
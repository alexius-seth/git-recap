from collections import defaultdict
from datetime import datetime
from pathlib import Path
import re

from git_recap.git_ops import CommitInfo, RepoActivity

NOISE_MESSAGES = {
    "wip",
    "temp",
    "tmp",
    "test",
    "testing",
    "asdf",
    "fix",
    "update",
    "changes",
    ".",
    "-",
}

PREFIX_PATTERN = re.compile(
    r"^(feat|fix|chore|docs|style|refactor|perf|test|build|ci)(\([^)]+\))?:\s*",
    re.IGNORECASE,
)


def format_timeframe_label(hours: int) -> str:
    """Convert total hours into a readable label like '24 hours', '3 days', or '2 weeks'."""
    if hours % 168 == 0:
        weeks = hours // 168
        return f"{weeks} {'week' if weeks == 1 else 'weeks'}"
    if hours > 24 and hours % 24 == 0:
        days = hours // 24
        return f"{days} {'day' if days == 1 else 'days'}"
    return f"{hours} {'hour' if hours == 1 else 'hours'}"


def clean_commit_message(message: str, strip_prefix: bool = False) -> str:
    """Optionally strip conventional commit prefixes and capitalize the first letter."""
    text = message.strip()
    if strip_prefix:
        text = PREFIX_PATTERN.sub("", text)
    if text:
        text = text[0].upper() + text[1:]
    return text


def filter_and_format_commits(
    commits: list[CommitInfo],
    hide_noise: bool = True,
    strip_prefix: bool = False,
) -> list[CommitInfo]:
    """Filter out noise/duplicate commits and format remaining messages."""
    cleaned: list[CommitInfo] = []
    seen_messages: set[str] = set()

    for commit in commits:
        raw_lower = commit.message.strip().lower()
        if hide_noise and raw_lower in NOISE_MESSAGES:
            continue

        formatted_msg = clean_commit_message(commit.message, strip_prefix=strip_prefix)
        dedup_key = formatted_msg.lower()

        if dedup_key in seen_messages:
            continue

        seen_messages.add(dedup_key)
        cleaned.append(
            CommitInfo(
                short_hash=commit.short_hash,
                message=formatted_msg,
                branch_ref=commit.branch_ref,
                date=commit.date,
                files_changed=commit.files_changed,
                insertions=commit.insertions,
                deletions=commit.deletions,
            )
        )

    return cleaned


def group_commits_by_date(commits: list[CommitInfo]) -> dict[str, list[CommitInfo]]:
    """Group commits under YYYY-MM-DD keys in order of appearance."""
    grouped: dict[str, list[CommitInfo]] = defaultdict(list)
    for commit in commits:
        grouped[commit.date].append(commit)
    return dict(grouped)


def format_commit_extras(commit: CommitInfo, show_stats: bool) -> str:
    """Format branch label and diff stat summary if --stats is enabled."""
    if not show_stats:
        return ""
    parts: list[str] = []
    if commit.branch_ref:
        parts.append(f"[{commit.branch_ref}]")
    if commit.files_changed > 0 or commit.insertions > 0 or commit.deletions > 0:
        file_word = "file" if commit.files_changed == 1 else "files"
        parts.append(f"({commit.files_changed} {file_word}, +{commit.insertions} / -{commit.deletions})")
    return f" {' '.join(parts)}" if parts else ""


def render_markdown(activities: list[RepoActivity], hours: int, show_stats: bool = False) -> str:
    """Format active repositories and commits into clean Markdown."""
    timeframe = format_timeframe_label(hours)
    multi_day = hours > 24
    lines = [f"### Git Recap (Last {timeframe})", ""]

    for item in activities:
        lines.append(f"**{item.repo_name}**")
        if multi_day and item.commits:
            for date_str, day_commits in group_commits_by_date(item.commits).items():
                lines.append(f"- *{date_str}*")
                for commit in day_commits:
                    extras = format_commit_extras(commit, show_stats=show_stats)
                    lines.append(f"  - `{commit.short_hash}` {commit.message}{extras}")
        else:
            for commit in item.commits:
                extras = format_commit_extras(commit, show_stats=show_stats)
                lines.append(f"- `{commit.short_hash}` {commit.message}{extras}")

        if item.uncommitted_count > 0:
            lines.append(f"- *In progress: {item.uncommitted_count} uncommitted file(s)*")
        lines.append("")

    return "\n".join(lines).strip()


def append_to_log_file(markdown_text: str, log_path: Path) -> Path:
    """Append a dated recap entry to a Markdown work journal file."""
    resolved_path = log_path.expanduser().resolve()
    if resolved_path.is_dir():
        resolved_path = resolved_path / "recap-log.md"

    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"## Entry — {timestamp}\n\n{markdown_text}\n\n---\n\n"

    with resolved_path.open("a", encoding="utf-8") as f:
        f.write(entry)

    return resolved_path
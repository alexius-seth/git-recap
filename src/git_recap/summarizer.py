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
            )
        )

    return cleaned


def render_markdown(activities: list[RepoActivity], hours: int) -> str:
    """Format active repositories and commits into clean Markdown."""
    lines = [f"### Git Recap (Last {hours} hours)", ""]

    for item in activities:
        lines.append(f"**{item.repo_name}**")
        for commit in item.commits:
            lines.append(f"- `{commit.short_hash}` {commit.message}")
        if item.uncommitted_count > 0:
            lines.append(f"- *In progress: {item.uncommitted_count} uncommitted file(s)*")
        lines.append("")

    return "\n".join(lines).strip()
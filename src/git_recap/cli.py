from pathlib import Path
import pyperclip
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markup import escape


from git_recap.git_ops import CommitInfo, RepoActivity, get_repo_activity
from git_recap.scanner import find_git_repos
from git_recap.summarizer import (
    append_to_log_file,
    filter_and_format_commits,
    format_timeframe_label,
    group_commits_by_date,
    render_markdown,
)

app = typer.Typer(help="Scan local Git repositories and summarize recent activity.")
console = Console(highlight=False)


def _print_commit_line(commit: CommitInfo, indent: str, show_stats: bool) -> None:
    """Render a single commit line in the terminal with optional branch and diff stats."""
    safe_message = escape(commit.message)
    line = f"{indent}[dim]{commit.short_hash}[/dim] {safe_message}"
    if show_stats:
        if commit.branch_ref:
            line += f" [magenta]\\[{escape(commit.branch_ref)}][/magenta]"
        if commit.files_changed > 0 or commit.insertions > 0 or commit.deletions > 0:
            line += (
                f" [dim]({commit.files_changed}f, "
                f"[green]+{commit.insertions}[/green] / [red]-{commit.deletions}[/red])[/dim]"
            )
    console.print(line)


@app.command()
def main(
    paths: list[Path] = typer.Argument(
        None,
        help="One or more directories to scan (defaults to current folder).",
    ),
    hours: int | None = typer.Option(
        None,
        "--hours",
        "-h",
        help="Look back this many hours for commits.",
    ),
    days: int | None = typer.Option(
        None,
        "--days",
        "-d",
        help="Look back this many days for commits (e.g., --days 3).",
    ),
    weeks: int | None = typer.Option(
        None,
        "--weeks",
        "-w",
        help="Look back this many weeks for commits (e.g., --weeks 2).",
    ),
    all_authors: bool = typer.Option(
        False,
        "--all-authors",
        "-a",
        help="Include commits from all authors instead of just your git user.email.",
    ),
    include_wip: bool = typer.Option(
        True,
        "--wip/--no-wip",
        help="Show repositories with uncommitted changes even without new commits.",
    ),
    clean: bool = typer.Option(
        False,
        "--clean",
        help="Strip prefixes like 'feat:' or 'fix:' and capitalize commit messages.",
    ),
    show_all_commits: bool = typer.Option(
        False,
        "--raw",
        help="Disable noise filtering and show every commit verbatim.",
    ),
    stats: bool = typer.Option(
        False,
        "--stats",
        "-s",
        help="Show branch labels and diff stats (+insertions / -deletions) per commit.",
    ),
    copy: bool = typer.Option(
        False,
        "--copy",
        "-c",
        help="Copy the formatted Markdown summary to your clipboard.",
    ),
    save: bool = typer.Option(
        False,
        "--save",
        help="Append the Markdown summary to ./recap-log.md.",
    ),
    log_file: Path | None = typer.Option(
        None,
        "--log-file",
        help="Save summary to a custom Markdown file path (implies --save).",
    ),
) -> None:
    """Summarize your local Git activity."""
    if weeks is not None:
        total_hours = weeks * 168
    elif days is not None:
        total_hours = days * 24
    elif hours is not None:
        total_hours = hours
    else:
        total_hours = 24

    timeframe = format_timeframe_label(total_hours)
    multi_day = total_hours > 24
    target_paths = paths if paths else [Path.cwd()]

    discovered_repos: list[Path] = []
    seen_paths: set[Path] = set()

    for target in target_paths:
        for repo in find_git_repos(target):
            if repo not in seen_paths:
                seen_paths.add(repo)
                discovered_repos.append(repo)

    if not discovered_repos:
        console.print("[yellow]No Git repositories found in the specified path(s).[/yellow]")
        raise typer.Exit(code=0)

    activities: list[RepoActivity] = []
    for repo in discovered_repos:
        activity = get_repo_activity(repo, hours=total_hours, all_authors=all_authors)
        if not activity:
            continue

        activity.commits = filter_and_format_commits(
            activity.commits,
            hide_noise=not show_all_commits,
            strip_prefix=clean,
        )

        if not activity.commits and (not include_wip or activity.uncommitted_count == 0):
            continue

        activities.append(activity)

    if not activities:
        console.print(
            f"[dim]No Git activity found in the last {timeframe} across {len(discovered_repos)} repo(s).[/dim]"
        )
        raise typer.Exit(code=0)

    repo_label = "repo" if len(activities) == 1 else "repos"
    console.print(
        Panel.fit(
            f"[bold cyan]Git Recap[/bold cyan] — Last {timeframe} ({len(activities)} active {repo_label})",
            border_style="cyan",
        )
    )

    for item in activities:
        console.print(f"\n[bold green]● {item.repo_name}[/bold green] [dim]({item.repo_path})[/dim]")

        if multi_day and item.commits:
            for date_str, day_commits in group_commits_by_date(item.commits).items():
                console.print(f"  [bold cyan]{date_str}[/bold cyan]")
                for commit in day_commits:
                    _print_commit_line(commit, indent="    ", show_stats=stats)
        else:
            for commit in item.commits:
                _print_commit_line(commit, indent="  ", show_stats=stats)

        if item.uncommitted_count > 0:
            console.print(
                f"  [yellow]↳ {item.uncommitted_count} uncommitted file(s) in working tree[/yellow]"
            )

    should_save = save or (log_file is not None)
    markdown_text = render_markdown(activities, hours=total_hours, show_stats=stats) if (copy or should_save) else ""

    if copy:
        pyperclip.copy(markdown_text)
        console.print("\n[bold green]✓ Copied Markdown summary to clipboard.[/bold green]")

    if should_save:
        destination = log_file if log_file is not None else Path("recap-log.md")
        saved_path = append_to_log_file(markdown_text, log_path=destination)
        console.print(f"[bold green]✓ Saved recap entry to {saved_path}[/bold green]")

    if not copy and not should_save:
        console.print()


if __name__ == "__main__":
    app()
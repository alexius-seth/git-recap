from pathlib import Path
import pyperclip
import typer
from rich.console import Console
from rich.panel import Panel

from git_recap.git_ops import RepoActivity, get_repo_activity
from git_recap.scanner import find_git_repos
from git_recap.summarizer import filter_and_format_commits, render_markdown

app = typer.Typer(help="Scan local Git repositories and summarize recent activity.")
console = Console()


@app.command()
def main(
    paths: list[Path] = typer.Argument(
        None,
        help="One or more directories to scan (defaults to current folder).",
    ),
    hours: int = typer.Option(
        24,
        "--hours",
        "-h",
        help="Look back this many hours for commits.",
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
    copy: bool = typer.Option(
        False,
        "--copy",
        "-c",
        help="Copy the formatted Markdown summary to your clipboard.",
    ),
) -> None:
    """Summarize your local Git activity."""
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
        activity = get_repo_activity(repo, hours=hours, all_authors=all_authors)
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
            f"[dim]No Git activity found in the last {hours} hours across {len(discovered_repos)} repo(s).[/dim]"
        )
        raise typer.Exit(code=0)

    repo_label = "repo" if len(activities) == 1 else "repos"
    console.print(
        Panel.fit(
            f"[bold cyan]Git Recap[/bold cyan] — Last {hours} hours ({len(activities)} active {repo_label})",
            border_style="cyan",
        )
    )

    for item in activities:
        console.print(f"\n[bold green]● {item.repo_name}[/bold green] [dim]({item.repo_path})[/dim]")

        for commit in item.commits:
            console.print(f"  [dim]{commit.short_hash}[/dim] {commit.message}")

        if item.uncommitted_count > 0:
            console.print(
                f"  [yellow]↳ {item.uncommitted_count} uncommitted file(s) in working tree[/yellow]"
            )

    if copy:
        markdown_text = render_markdown(activities, hours=hours)
        pyperclip.copy(markdown_text)
        console.print("\n[bold green]✓ Copied Markdown summary to clipboard.[/bold green]")
    else:
        console.print()


if __name__ == "__main__":
    app()
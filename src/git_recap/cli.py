from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel

from git_recap.git_ops import get_repo_activity
from git_recap.scanner import find_git_repos

app = typer.Typer(help="Scan local Git repositories and summarize recent activity.")
console = Console()


@app.command()
def main(
    path: Path = typer.Argument(
        Path.cwd(),
        help="Root directory containing your Git repositories (defaults to current folder).",
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
        help="Show repositories with uncommitted changes even if there are no new commits.",
    ),
) -> None:
    """Summarize your local Git activity."""
    repos = find_git_repos(path)

    if not repos:
        console.print(f"[yellow]No Git repositories found inside:[/yellow] {path.resolve()}")
        raise typer.Exit(code=0)

    activities = []
    for repo in repos:
        activity = get_repo_activity(repo, hours=hours, all_authors=all_authors)
        if not activity:
            continue
        if not activity.commits and not include_wip:
            continue
        activities.append(activity)

    if not activities:
        console.print(f"[dim]No Git activity found in the last {hours} hours across {len(repos)} repos.[/dim]")
        raise typer.Exit(code=0)

    console.print(
        Panel.fit(
            f"[bold cyan]Git Recap[/bold cyan] — Last {hours} hours ({len(activities)} active repos)",
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

    console.print()


if __name__ == "__main__":
    app()
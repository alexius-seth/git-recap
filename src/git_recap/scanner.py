import os
from pathlib import Path

IGNORED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".next",
    ".cache",
}


def find_git_repos(root_path: Path) -> list[Path]:
    """Recursively find all directories containing a .git folder."""
    repos: list[Path] = []
    root_path = root_path.expanduser().resolve()

    if not root_path.exists():
        return repos

    for current_root, dirs, _ in os.walk(root_path):
        # Prune heavy/irrelevant folders in-place so os.walk skips them
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        if ".git" in dirs:
            repos.append(Path(current_root))
            # Stop descending inside an already-found Git repo
            dirs.clear()

    return sorted(repos, key=lambda p: p.name.lower())
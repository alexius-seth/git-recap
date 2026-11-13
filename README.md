# git-recap

A fast, offline-first CLI tool that scans local Git repositories on your machine and formats a clean summary of your recent commits and work-in-progress files.

![git-recap terminal preview](assets/screenshot.png)

## Features

- **Multi-Repo & Multi-Path Scanning:** Scan a single project, a parent workspace folder, or multiple directories across drives while skipping heavy folders like `node_modules` and `.venv`.
- **Flexible Time Windows:** Look back by `--hours`, `--days`, or `--weeks`, automatically grouping multi-day summaries by date.
- **Noise Filtering & Cleanup (`--clean`):** Hides low-value commits (`wip`, `temp`, `.`) and strips conventional prefixes (`feat:`, `fix:`) for readable standup bullets.
- **Branch Labels & Diff Stats (`--stats`):** Displays branch names and line/file change counts (`+42 / -10`) so major changes stand out.
- **Clipboard & Journal Export (`--copy`, `--save`):** Copy formatted Markdown straight to your clipboard or append dated entries to `recap-log.md`.

## Requirements

- Python 3.10 or higher
- Git installed and available in your system `PATH`

## Installation

Clone the repository and install it locally using `pip`:

```bash
git clone https://github.com/alexius-seth/git-recap.git
cd git-recap
pip install -e .
```

Once installed, you can run it using any of these aliases:

```bash
git recap
git-recap
recap
```

## Usage Examples

```bash
# Summarize the current folder (or all repos inside it) for the last 24 hours
recap

# Look back 10 hours, clean up commit prefixes, and copy Markdown to clipboard
recap --hours 10 --clean --copy

# Summarize the last 3 days with branch names and diff stats
recap --days 3 --clean --stats

# Generate a weekly recap across multiple folders and save it to recap-log.md
recap C:\git-recap D:\Projects --weeks 1 --clean --save

# Save a summary to a specific folder or Markdown file
recap --log-file C:\git-recap\journal.md
```

### Example Markdown Output (`--copy` / `--save`)

```markdown
### Git Recap (Last 24 hours)

**git-recap**
- `a87fed7` Add multi-day recaps, diff stats, journal export, tests, and docs [main] (4 files, +310 / -28)
- `e2bae32` Add commit cleanup, Markdown clipboard export, and multi-path CLI support [main] (3 files, +185 / -12)
- *In progress: 1 uncommitted file(s)*
```

## CLI Options

| Flag | Short | Description |
| :--- | :--- | :--- |
| `--hours <int>` | `-h` | Look back this many hours (default: `24`). |
| `--days <int>` | `-d` | Look back this many days (groups output by date when `> 1`). |
| `--weeks <int>` | `-w` | Look back this many weeks. |
| `--clean` | | Strip prefixes like `feat:` or `fix:` and capitalize messages. |
| `--stats` | `-s` | Show branch labels and `(+insertions / -deletions)` per commit. |
| `--copy` | `-c` | Copy formatted Markdown output to the system clipboard. |
| `--save` | | Append the Markdown summary to `./recap-log.md`. |
| `--log-file <path>` | | Save summary to a custom file or folder path (implies `--save`). |
| `--raw` | | Show all commits verbatim without noise filtering. |
| `--all-authors` | `-a` | Include commits from all authors instead of only your `git user.email`. |
| `--no-wip` | | Hide repositories that only have uncommitted changes. |

## Running Tests

Install the development dependencies and run `pytest`:

```bash
pip install -e ".[dev]"
pytest
```

## Author

**Alexius Seth** — [@alexius-seth](https://github.com/alexius-seth)

## License

This project is licensed under the [MIT](LICENSE) License.


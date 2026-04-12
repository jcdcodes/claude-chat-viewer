# Claude Chat Viewer

A read-only web interface for browsing Claude Code conversation transcripts stored in `~/.claude/projects/`.

The whole project (except this sentence) was mostly written in Claude Code with Superpowers, and I've only scanned most of the source code.

## Features

- **Grouped and flat views** of sessions, sorted reverse-chronologically
- **Session metadata**: file size, approximate interaction time, git branch
- **Collapsible thinking blocks and tool calls** with persistent expand/collapse preferences
- **Inline subagent transcripts** with lazy loading
- **Markdown / raw text toggle** for message content (raw mode uses Menlo monospace)
- **Full-text search** across all message content including subagents
- **Multi-directory overlay**: merges a backup directory with live `~/.claude/projects/` data

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run python main.py
```

Then open http://127.0.0.1:5000 in your browser.

## Options

```
uv run python main.py --port 8080          # use a different port
uv run python main.py --data-dir /path/to  # use a different backup directory
```

By default, the app overlays live data from `~/.claude/projects/` on top of backup data from `~/Sync/air-claude-history-backup/`. Use `--data-dir` to point at a different backup directory.

## Tests

```
uv run pytest
```

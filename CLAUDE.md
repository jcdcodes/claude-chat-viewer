# Claude Chat Viewer - Project Context

## Project Overview

This is a **read-only web interface** for browsing Claude Code conversation transcripts. It parses JSONL files from `~/.claude/projects/` (and optional backup directories) and displays them with features like collapsible blocks, search, and lazy-loaded subagents.

## Architecture

### Data Flow
```
JSONL files (Claude transcripts)
    ↓ (parser.py)
Model objects (Session, Message, etc.)
    ↓ (main.py routes)
Flask templates (HTML)
    ↓
Browser with htmx + JS for interactivity
```

### Core Files

| File | Purpose |
|------|---------|
| `main.py` | Flask app with routes: `/`, `/api/sessions`, `/session/<id>`, `/api/subagent/<id>/<subid>`, `/search` |
| `models.py` | Dataclasses: `Message`, `Session`, `Project`, `SubagentSession`, `ContentBlock` variants |
| `parser.py` | Loads and parses JSONL transcript files into model objects |
| `search.py` | Full-text search across all messages with highlighting |
| `static/app.js` | Frontend JS for collapse toggles, content mode switching, htmx handling |
| `static/style.css` | CSS styling with light theme and high-contrast text |
| `templates/` | Jinja2 templates for rendering |

### Key Models

- **Message**: `uuid`, `parent_uuid`, `type` ("user"/"assistant"/"tool_result"), `timestamp`, `content` (list of ContentBlock), `model`
- **ContentBlock**: `TextBlock`, `ThinkingBlock`, `ToolUseBlock`, `ToolResultBlock`
- **Session**: `id`, `project`, `timestamp`, `title`, `git_branch`, `cwd`, `version`, `file_size`, `messages`, `subagents`
- **Project**: `name`, `path`, `sessions`

## Important Patterns & Conventions

1. **Assistant Message Merging**: Multiple assistant streaming chunks are merged into single `Message` objects using `requestId`
2. **Tool Result Attachment**: Tool results are attached to the associated assistant message (not standalone)
3. **Interaction Time**: Computed based on message gaps - gaps > 15 minutes are considered breaks
4. **Project Name Display**: Strips user prefix (`-Users-<user>-` → `-`)
5. **Multi-directory Overlay**: Live `~/.claude/projects/` overlays backup directory (live wins on duplicates)
6. **Subagent Loading**: Lazy-loaded from `<session_dir>/<session_id>/subagents/` with `.meta.json` and `.jsonl` files

## Frontend Features

- **Collapse Toggles**: Thinking blocks, tool calls, insights with persistent `localStorage` state
- **Content Mode**: Markdown vs RAW text toggle (raw uses Menlo monospace font)
- **View Switching**: Grouped (by project) vs Flat (all sessions) views via htmx
- **Search**: Full-text search across all messages including subagents with highlighting
- **Hash Navigation**: Scroll to message on page load if URL has hash fragment

## Setup & Development

```bash
# Install dependencies
uv sync

# Run the app
uv run python main.py

# Options
uv run python main.py --port 8080          # use a different port
uv run python main.py --data-dir /path/to  # use a different backup directory

# Run tests
uv run pytest
```

## Testing

Tests are in `tests/`:
- `test_models.py` - Model dataclass tests
- `test_parser.py` - JSONL parsing tests
- `test_search.py` - Search functionality tests
- `test_routes.py` - Flask route tests
- `conftest.py` - Pytest fixtures (e.g., `projects_dir` mock data)

## Theme Notes

- Uses high-contrast text colors (never gray-on-gray)
- Primary accent color: `#4a4ae0`
- Max-width: 1200px and light mode for readability
- Responsive layout

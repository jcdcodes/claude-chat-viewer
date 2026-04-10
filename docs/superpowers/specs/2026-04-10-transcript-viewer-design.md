# Claude Transcript Viewer — Design Spec

## Overview

A single-user, read-only web app for browsing Claude Code conversation transcripts stored in `~/.claude/projects/`. Runs on localhost only (127.0.0.1). Written in Python with Flask, server-rendered Jinja templates, and htmx for partial-page interactivity. No database — data is loaded from JSONL files on disk and cached in memory at startup.

## Data Source

Claude Code stores conversation transcripts in `~/.claude/projects/`. Each subdirectory represents a project, named by path-encoding (e.g., `-Users-jdaghlian-arboretum-greenhouse`). Within each project directory:

- `*.jsonl` files — one per session, named by UUID. Each line is a JSON object representing a message or event.
- `<uuid>/subagents/` directories — contain subagent transcripts as `agent-<id>.jsonl` files with corresponding `agent-<id>.meta.json` metadata files.
- `memory/` directory — project memory files (not displayed by this app).

### JSONL Message Types

Each line has a `type` field:

| Type | Meaning | Display? |
|---|---|---|
| `user` | User message | Yes |
| `assistant` | Assistant message (may contain text, thinking, tool_use blocks) | Yes |
| `system` | System metadata (e.g., `turn_duration`) | No (annotate turn duration on preceding assistant message) |
| `progress` | Hook progress events | No |
| `file-history-snapshot` | File state snapshots | No |
| `last-prompt` | Last prompt marker | No |

### Key Message Fields

- `uuid`, `parentUuid` — message identity and threading
- `type` — message type (see above)
- `timestamp` — ISO 8601
- `message.role` — `user` or `assistant`
- `message.content` — array of content blocks (text, thinking, tool_use, tool_result)
- `model` or `message.model` — model used (e.g., `claude-sonnet-4-6`)
- `sessionId` — session UUID
- `gitBranch` — git branch at time of message
- `cwd` — working directory
- `isSidechain` — whether message is on a sidechain (branched conversation)

### Subagent Metadata

`agent-<id>.meta.json` contains:
```json
{
  "agentType": "Explore",
  "description": "Explore EMR bundle fhir_to_omop job"
}
```

The subagent JSONL has the same format as main session transcripts.

## Data Model

```
Project
  name: str              # display name, e.g. "-arboretum-greenhouse"
  path: str              # full filesystem path
  sessions: list[Session]

Session
  id: str                # UUID
  project: str           # parent project name
  timestamp: datetime    # from first message
  title: str             # first user message text, truncated
  git_branch: str | None
  cwd: str
  version: str
  file_size: int         # JSONL file size in bytes
  interaction_time: int  # estimated active time in seconds
  messages: list[Message]
  subagents: dict[str, SubagentSession]

Message
  uuid: str
  parent_uuid: str | None
  type: "user" | "assistant" | "tool_result"
  timestamp: datetime
  content: list[ContentBlock]
  model: str | None

ContentBlock — one of:
  TextBlock(text: str)
  ThinkingBlock(thinking: str)
  ToolUseBlock(tool_name: str, tool_id: str, input: dict)
  ToolResultBlock(tool_use_id: str, content: str, is_error: bool)

SubagentSession
  id: str
  agent_type: str        # e.g., "Explore"
  description: str
  messages: list[Message]
  message_count: int
  interaction_time: int
```

### Parsing Rules

- Filter out `progress`, `file-history-snapshot`, and `last-prompt` messages entirely.
- `system` messages with subtype `turn_duration`: attach `durationMs` as annotation on the preceding assistant turn (do not display as standalone messages).
- Assistant messages may arrive as multiple JSONL lines with the same `requestId` as content streams in. Merge these into a single Message by combining their content block arrays.
- User messages with `tool_result` content (tool call responses) are displayed as part of the preceding assistant message's tool call, not as standalone user messages.
- `isSidechain: true` messages are excluded from the main conversation view.

### Interaction Time Algorithm

Walk timestamps in order. If the gap between consecutive messages is ≤15 minutes, add that gap to the running total. Gaps >15 minutes are treated as breaks. Display as `~N min` or `~N hr N min`.

## Application Structure

```
claude-chat-viewer/
  main.py              — Flask app, routes, startup
  parser.py            — JSONL parsing, data model dataclasses
  search.py            — full-text search across raw JSONL
  templates/
    base.html          — layout shell, nav
    index.html         — project/session listing (both views)
    session.html       — single session conversation view
    search_results.html — search results page
    partials/
      message.html     — single message block (user/assistant)
      tool_call.html   — collapsed tool call with summary
      thinking.html    — collapsed thinking block
      subagent.html    — subagent header + htmx lazy-load target
      subagent_detail.html — full subagent transcript (loaded on expand)
      session_list.html    — session list partial (for htmx view switching)
  static/
    style.css          — all styling
    htmx.min.js        — htmx (~14KB, vendored)
```

## Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Landing page — project/session listing |
| `/session/<id>` | GET | Full session conversation view |
| `/api/subagent/<session_id>/<subagent_id>` | GET | htmx partial — loads subagent transcript on demand |
| `/search` | GET | Search results page (`?q=...`) |
| `/api/sessions` | GET | htmx partial — swap session list view (`?view=flat\|grouped`) |

## Views

### Index Page (Landing)

Two switchable views, toggled via htmx without full page reload:

**Grouped by project (default):**
- Projects listed in reverse chronological order by their most recent session date
- Sessions within each group sorted newest-first
- Project name displayed as heading in accent color (e.g., `-arboretum-greenhouse` — the `-Users-jdaghlian-` prefix stripped)

**Flat chronological:**
- All sessions across all projects in a single list, newest-first
- Project name shown inline per row, in the same accent color as the grouped view headings

**Each session row shows:**
- Title (first user message, truncated)
- Git branch
- Project name (flat view only)
- Total size (JSONL file size, human-readable: KB/MB)
- Approximate interaction time
- Date

**Search bar** at top of both views — submits to `/search`.

### Session View (Conversation Reader)

**Header:**
- Back link to index
- Session title (first user message)
- Metadata: project name (accent color), git branch, date, file size, interaction time
- Global collapse toggles: "Thinking: collapsed/expanded" and "Tool calls: collapsed/expanded" dropdowns

**Messages:**
- **User messages:** black text on light blue background (`#e8f0fe`), with "You" label and timestamp
- **Assistant messages:** black text on light purple background (`#f5f5ff`), with "Claude" label in accent color, model name, and timestamp
- **Thinking blocks:** collapsed by default (respects global toggle). Shows italic "Thinking..." when collapsed. Expandable to show full thinking text.
- **Tool calls:** collapsed by default (respects global toggle). Collapsed state shows: tool name (bold), abbreviated args (e.g., the command for Bash, the path for Read), and a brief output summary on the right. Expanded state shows full input and output.
- **Subagent blocks:** visually distinct with indigo left border. Collapsed state shows: agent type, description, message count, interaction time. Expanded state (loaded via htmx on demand) shows the full nested conversation:
  - **Prompt** — the dispatch message sent to the subagent
  - **Agent conversation** — the subagent's messages with its own tool calls (same collapse behavior)
  - **Result** — the value returned to the parent agent, visually distinct with accent left border

**Collapse preferences** (thinking default, tool call default) persist in localStorage across page loads.

### Search Results

- Search bar at top (same as index)
- Server-side full-text search across all raw JSONL content (user messages, assistant prose, tool call args/output, subagent transcripts)
- Results grouped by session: session title, project name, date
- Each result shows a snippet with surrounding context and highlighted matching terms
- Clicking a result navigates to the session view, scrolled to the matching message with the match highlighted

## Visual Design

- Light theme: white background, fully saturated text colors throughout
- All text is high-contrast: black for body text, dark colors for metadata/timestamps — never gray-on-gray
- Accent color: `#4a4ae0` (indigo) for project names, assistant labels, subagent borders
- User message background: `#e8f0fe` (light blue)
- Assistant message background: `#f5f5ff` (light purple)
- Collapsed blocks background: `#f5f5f5` with `#ccc` border
- Code snippets: `#e4e4e4` background, black text
- No custom fonts — system font stack (`system-ui, sans-serif`; monospace for code)

## Technical Decisions

- **Flask** — minimal framework, smallest footprint
- **Jinja2 templates** — server-rendered HTML, readable Python
- **htmx** — single vendored JS file (~14KB) for: lazy-loading subagent transcripts, swapping session list views, search. No build step, no npm.
- **In-memory data** — all JSONL parsed at startup, cached in memory. ~18MB currently, trivially fits. Provides fast search and rendering.
- **Localhost only** — Flask bound to `127.0.0.1`. Single-user, no auth needed.
- **Search** — server-side substring/regex search over parsed message content. Searches the data model, not the rendered HTML, so lazy-loaded subagent content is always searchable.
- **No database** — reads directly from `~/.claude/projects/` on disk. Data refreshed on server restart.

## Out of Scope

- Editing or deleting transcripts
- Real-time updates / file watching
- Multi-user access or authentication
- Export functionality
- Syntax highlighting in code blocks (could be added later with a CSS-only library)

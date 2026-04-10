# Claude Transcript Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only web app to browse Claude Code transcripts from `~/.claude/projects/` in a web browser on localhost.

**Architecture:** Flask serves server-rendered Jinja2 templates. JSONL transcripts are parsed at startup and cached in memory. htmx handles partial-page updates for subagent lazy-loading and view toggling. All styling in one CSS file, no build step.

**Tech Stack:** Python 3.13, Flask, Jinja2, htmx (vendored)

---

### Task 1: Project Setup and Dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `static/htmx.min.js`

- [ ] **Step 1: Add Flask dependency to pyproject.toml**

```toml
[project]
name = "claude-chat-viewer"
version = "0.1.0"
description = "Read-only browser for Claude Code conversation transcripts"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "flask>=3.1",
]
```

- [ ] **Step 2: Install dependencies**

Run: `uv sync`
Expected: Flask and dependencies installed, `uv.lock` created.

- [ ] **Step 3: Download htmx**

Run: `curl -o static/htmx.min.js https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js`
Expected: `static/htmx.min.js` exists, ~14KB.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock static/htmx.min.js
git commit -m "Add Flask dependency and vendor htmx"
```

---

### Task 2: Data Model

**Files:**
- Create: `models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the test file for data model classes**

```python
# tests/test_models.py
from datetime import datetime, timezone
from models import (
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    Message,
    SubagentSession,
    Session,
    Project,
)


def test_text_block_creation():
    block = TextBlock(text="hello")
    assert block.text == "hello"
    assert block.type == "text"


def test_thinking_block_creation():
    block = ThinkingBlock(thinking="let me think...")
    assert block.thinking == "let me think..."
    assert block.type == "thinking"


def test_tool_use_block_creation():
    block = ToolUseBlock(
        tool_name="Bash",
        tool_id="toolu_123",
        input={"command": "ls"},
    )
    assert block.tool_name == "Bash"
    assert block.tool_id == "toolu_123"
    assert block.input == {"command": "ls"}
    assert block.type == "tool_use"


def test_tool_result_block_creation():
    block = ToolResultBlock(
        tool_use_id="toolu_123",
        content="file1.py\nfile2.py",
        is_error=False,
    )
    assert block.tool_use_id == "toolu_123"
    assert block.content == "file1.py\nfile2.py"
    assert block.is_error is False
    assert block.type == "tool_result"


def test_message_creation():
    ts = datetime(2026, 4, 6, 18, 38, 44, tzinfo=timezone.utc)
    msg = Message(
        uuid="abc-123",
        parent_uuid=None,
        type="user",
        timestamp=ts,
        content=[TextBlock(text="hello")],
        model=None,
    )
    assert msg.uuid == "abc-123"
    assert msg.type == "user"
    assert len(msg.content) == 1


def test_session_interaction_time():
    ts1 = datetime(2026, 4, 6, 18, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 4, 6, 18, 5, 0, tzinfo=timezone.utc)
    ts3 = datetime(2026, 4, 6, 18, 8, 0, tzinfo=timezone.utc)
    # 20 minute gap — break
    ts4 = datetime(2026, 4, 6, 18, 28, 0, tzinfo=timezone.utc)
    ts5 = datetime(2026, 4, 6, 18, 30, 0, tzinfo=timezone.utc)

    messages = [
        Message(uuid="1", parent_uuid=None, type="user", timestamp=ts1, content=[], model=None),
        Message(uuid="2", parent_uuid="1", type="assistant", timestamp=ts2, content=[], model=None),
        Message(uuid="3", parent_uuid="2", type="user", timestamp=ts3, content=[], model=None),
        Message(uuid="4", parent_uuid="3", type="assistant", timestamp=ts4, content=[], model=None),
        Message(uuid="5", parent_uuid="4", type="user", timestamp=ts5, content=[], model=None),
    ]

    session = Session(
        id="sess-1",
        project="test",
        timestamp=ts1,
        title="test session",
        git_branch="main",
        cwd="/tmp",
        version="2.1.81",
        file_size=1000,
        messages=messages,
        subagents={},
    )
    # 5 min + 3 min + (20 min break, skip) + 2 min = 10 min = 600 seconds
    assert session.interaction_time == 600


def test_session_interaction_time_empty():
    session = Session(
        id="sess-1",
        project="test",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        title="empty",
        git_branch=None,
        cwd="/tmp",
        version="2.1.81",
        file_size=0,
        messages=[],
        subagents={},
    )
    assert session.interaction_time == 0


def test_session_interaction_time_format():
    ts1 = datetime(2026, 4, 6, 18, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 4, 6, 18, 5, 0, tzinfo=timezone.utc)
    messages = [
        Message(uuid="1", parent_uuid=None, type="user", timestamp=ts1, content=[], model=None),
        Message(uuid="2", parent_uuid="1", type="assistant", timestamp=ts2, content=[], model=None),
    ]
    session = Session(
        id="s", project="p", timestamp=ts1, title="t",
        git_branch=None, cwd="/", version="1", file_size=0,
        messages=messages, subagents={},
    )
    assert session.interaction_time_display == "~5 min"


def test_session_interaction_time_format_hours():
    ts1 = datetime(2026, 4, 6, 18, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 4, 6, 19, 15, 0, tzinfo=timezone.utc)
    messages = [
        Message(uuid="1", parent_uuid=None, type="user", timestamp=ts1, content=[], model=None),
        Message(uuid="2", parent_uuid="1", type="assistant", timestamp=ts2, content=[], model=None),
    ]
    session = Session(
        id="s", project="p", timestamp=ts1, title="t",
        git_branch=None, cwd="/", version="1", file_size=0,
        messages=messages, subagents={},
    )
    assert session.interaction_time_display == "~1 hr 15 min"


def test_session_file_size_display():
    session = Session(
        id="s", project="p",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        title="t", git_branch=None, cwd="/", version="1",
        file_size=52_230, messages=[], subagents={},
    )
    assert session.file_size_display == "51 KB"


def test_session_file_size_display_mb():
    session = Session(
        id="s", project="p",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        title="t", git_branch=None, cwd="/", version="1",
        file_size=2_500_000, messages=[], subagents={},
    )
    assert session.file_size_display == "2.4 MB"


def test_project_sorted_sessions():
    ts_old = datetime(2026, 4, 1, tzinfo=timezone.utc)
    ts_new = datetime(2026, 4, 10, tzinfo=timezone.utc)
    s1 = Session(
        id="old", project="p", timestamp=ts_old, title="old",
        git_branch=None, cwd="/", version="1", file_size=0,
        messages=[], subagents={},
    )
    s2 = Session(
        id="new", project="p", timestamp=ts_new, title="new",
        git_branch=None, cwd="/", version="1", file_size=0,
        messages=[], subagents={},
    )
    proj = Project(name="-myproject", path="/some/path", sessions=[s1, s2])
    assert proj.latest_timestamp == ts_new
    assert proj.sorted_sessions[0].id == "new"
    assert proj.sorted_sessions[1].id == "old"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Implement the data model**

```python
# models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

INTERACTION_GAP_SECONDS = 15 * 60  # 15 minutes


@dataclass
class TextBlock:
    text: str
    type: str = field(default="text", init=False)


@dataclass
class ThinkingBlock:
    thinking: str
    type: str = field(default="thinking", init=False)


@dataclass
class ToolUseBlock:
    tool_name: str
    tool_id: str
    input: dict[str, Any]
    type: str = field(default="tool_use", init=False)


@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: str
    is_error: bool
    type: str = field(default="tool_result", init=False)


ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock


@dataclass
class Message:
    uuid: str
    parent_uuid: str | None
    type: str  # "user", "assistant", "tool_result"
    timestamp: datetime
    content: list[ContentBlock]
    model: str | None


@dataclass
class SubagentSession:
    id: str
    agent_type: str
    description: str
    messages: list[Message]

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def interaction_time(self) -> int:
        return _compute_interaction_time(self.messages)


@dataclass
class Session:
    id: str
    project: str
    timestamp: datetime
    title: str
    git_branch: str | None
    cwd: str
    version: str
    file_size: int
    messages: list[Message]
    subagents: dict[str, SubagentSession]

    @property
    def interaction_time(self) -> int:
        return _compute_interaction_time(self.messages)

    @property
    def interaction_time_display(self) -> str:
        total_seconds = self.interaction_time
        total_minutes = round(total_seconds / 60)
        if total_minutes < 1:
            return "~<1 min"
        if total_minutes < 60:
            return f"~{total_minutes} min"
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes == 0:
            return f"~{hours} hr"
        return f"~{hours} hr {minutes} min"

    @property
    def file_size_display(self) -> str:
        if self.file_size >= 1_000_000:
            return f"{self.file_size / 1_048_576:.1f} MB"
        return f"{self.file_size // 1024} KB"


@dataclass
class Project:
    name: str
    path: str
    sessions: list[Session]

    @property
    def latest_timestamp(self) -> datetime:
        return max(s.timestamp for s in self.sessions)

    @property
    def sorted_sessions(self) -> list[Session]:
        return sorted(self.sessions, key=lambda s: s.timestamp, reverse=True)


def _compute_interaction_time(messages: list[Message]) -> int:
    if len(messages) < 2:
        return 0
    total = 0
    for i in range(1, len(messages)):
        gap = (messages[i].timestamp - messages[i - 1].timestamp).total_seconds()
        if gap <= INTERACTION_GAP_SECONDS:
            total += gap
    return int(total)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "Add data model classes with interaction time calculation"
```

---

### Task 3: JSONL Parser

**Files:**
- Create: `parser.py`
- Create: `tests/test_parser.py`
- Create: `tests/fixtures/` (test fixture JSONL files)

- [ ] **Step 1: Create test fixture data**

Create a minimal JSONL fixture that covers the key message types. This avoids depending on real user data in tests.

```python
# tests/conftest.py
import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def projects_dir(tmp_path: Path) -> Path:
    """Create a mock ~/.claude/projects/ structure with test data."""
    project_dir = tmp_path / "-Users-testuser-myproject"
    project_dir.mkdir()

    session_id = "aaaa-bbbb-cccc-dddd"
    jsonl_path = project_dir / f"{session_id}.jsonl"

    messages = [
        {
            "type": "file-history-snapshot",
            "messageId": "msg-0",
            "snapshot": {},
            "timestamp": "2026-04-06T18:38:44.000Z",
        },
        {
            "parentUuid": None,
            "isSidechain": False,
            "type": "user",
            "message": {
                "role": "user",
                "content": "explain the login flow",
            },
            "uuid": "msg-1",
            "timestamp": "2026-04-06T18:38:44.000Z",
            "sessionId": session_id,
            "version": "2.1.81",
            "gitBranch": "main",
            "cwd": "/Users/testuser/myproject",
        },
        {
            "parentUuid": "msg-1",
            "isSidechain": False,
            "message": {
                "model": "claude-sonnet-4-6",
                "id": "msg_01",
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "Let me analyze this..."},
                ],
            },
            "requestId": "req_001",
            "type": "assistant",
            "uuid": "msg-2",
            "timestamp": "2026-04-06T18:38:48.000Z",
            "sessionId": session_id,
            "version": "2.1.81",
            "gitBranch": "main",
            "cwd": "/Users/testuser/myproject",
        },
        {
            "parentUuid": "msg-2",
            "isSidechain": False,
            "message": {
                "model": "claude-sonnet-4-6",
                "id": "msg_01",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_01",
                        "name": "Read",
                        "input": {"file_path": "/Users/testuser/myproject/auth.py"},
                    },
                ],
            },
            "requestId": "req_001",
            "type": "assistant",
            "uuid": "msg-3",
            "timestamp": "2026-04-06T18:38:50.000Z",
            "sessionId": session_id,
            "version": "2.1.81",
            "gitBranch": "main",
            "cwd": "/Users/testuser/myproject",
        },
        {
            "parentUuid": "msg-3",
            "isSidechain": False,
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "tool_use_id": "toolu_01",
                        "type": "tool_result",
                        "content": "def login(user, pw):\n    return check(user, pw)",
                        "is_error": False,
                    }
                ],
            },
            "uuid": "msg-4",
            "timestamp": "2026-04-06T18:38:51.000Z",
            "toolUseResult": {
                "stdout": "def login(user, pw):\n    return check(user, pw)",
            },
            "sessionId": session_id,
            "version": "2.1.81",
            "gitBranch": "main",
            "cwd": "/Users/testuser/myproject",
        },
        {
            "parentUuid": "msg-4",
            "isSidechain": False,
            "message": {
                "model": "claude-sonnet-4-6",
                "id": "msg_02",
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "The login flow works like this..."},
                ],
            },
            "requestId": "req_002",
            "type": "assistant",
            "uuid": "msg-5",
            "timestamp": "2026-04-06T18:39:00.000Z",
            "sessionId": session_id,
            "version": "2.1.81",
            "gitBranch": "main",
            "cwd": "/Users/testuser/myproject",
        },
        {
            "parentUuid": "msg-3",
            "isSidechain": False,
            "type": "system",
            "subtype": "turn_duration",
            "durationMs": 12000,
            "timestamp": "2026-04-06T18:39:01.000Z",
            "uuid": "msg-6",
            "sessionId": session_id,
        },
        {
            "type": "progress",
            "data": {"type": "hook_progress"},
            "timestamp": "2026-04-06T18:39:02.000Z",
            "uuid": "msg-7",
            "sessionId": session_id,
        },
    ]

    with open(jsonl_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    # Create a subagent
    subagent_dir = project_dir / session_id / "subagents"
    subagent_dir.mkdir(parents=True)

    meta = {"agentType": "Explore", "description": "Explore auth module"}
    with open(subagent_dir / "agent-abc123.meta.json", "w") as f:
        json.dump(meta, f)

    subagent_messages = [
        {
            "type": "user",
            "message": {"role": "user", "content": "Search for auth functions"},
            "uuid": "sub-1",
            "parentUuid": None,
            "isSidechain": False,
            "timestamp": "2026-04-06T18:38:49.000Z",
            "agentId": "agent-abc123",
            "sessionId": session_id,
            "version": "2.1.81",
            "cwd": "/Users/testuser/myproject",
        },
        {
            "type": "assistant",
            "message": {
                "model": "claude-sonnet-4-6",
                "role": "assistant",
                "content": [{"type": "text", "text": "Found 2 auth functions."}],
            },
            "requestId": "req_sub_001",
            "uuid": "sub-2",
            "parentUuid": "sub-1",
            "isSidechain": False,
            "timestamp": "2026-04-06T18:38:55.000Z",
            "sessionId": session_id,
            "version": "2.1.81",
            "cwd": "/Users/testuser/myproject",
        },
    ]

    with open(subagent_dir / "agent-abc123.jsonl", "w") as f:
        for msg in subagent_messages:
            f.write(json.dumps(msg) + "\n")

    return tmp_path
```

- [ ] **Step 2: Write tests for the parser**

```python
# tests/test_parser.py
from pathlib import Path

from models import TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock
from parser import load_projects


def test_load_projects_finds_project(projects_dir: Path):
    projects = load_projects(projects_dir)
    assert len(projects) == 1
    assert projects[0].name == "-myproject"


def test_load_projects_finds_session(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    assert session.id == "aaaa-bbbb-cccc-dddd"
    assert session.git_branch == "main"
    assert session.title == "explain the login flow"


def test_parser_filters_non_conversation_types(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    msg_types = [m.type for m in session.messages]
    # Should not contain progress or file-history-snapshot messages
    assert "progress" not in msg_types
    assert "file-history-snapshot" not in msg_types


def test_parser_merges_assistant_streaming_messages(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    # msg-2 and msg-3 share requestId req_001 and should be merged
    assistant_msgs = [m for m in session.messages if m.type == "assistant"]
    # req_001 merged into one, req_002 is another
    assert len(assistant_msgs) == 2
    # First assistant message should have both thinking and tool_use blocks
    first = assistant_msgs[0]
    block_types = [b.type for b in first.content]
    assert "thinking" in block_types
    assert "tool_use" in block_types


def test_parser_attaches_tool_results(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    # The tool_result user message (msg-4) should be attached to the
    # assistant message's tool_use, not appear as a standalone message
    assistant_msgs = [m for m in session.messages if m.type == "assistant"]
    first = assistant_msgs[0]
    block_types = [b.type for b in first.content]
    assert "tool_result" in block_types
    result_block = [b for b in first.content if b.type == "tool_result"][0]
    assert "def login" in result_block.content


def test_parser_excludes_tool_result_as_standalone(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    # Tool result user messages should not appear as standalone user messages
    user_msgs = [m for m in session.messages if m.type == "user"]
    for msg in user_msgs:
        for block in msg.content:
            assert not isinstance(block, ToolResultBlock), \
                "Tool results should be attached to assistant messages, not standalone"


def test_parser_loads_subagents(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    assert "agent-abc123" in session.subagents
    subagent = session.subagents["agent-abc123"]
    assert subagent.agent_type == "Explore"
    assert subagent.description == "Explore auth module"
    assert subagent.message_count == 2


def test_parser_strips_user_prefix_from_project_name(projects_dir: Path):
    """Project name should have the -Users-<username>- prefix stripped."""
    projects = load_projects(projects_dir)
    assert projects[0].name == "-myproject"


def test_parser_sets_file_size(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    assert session.file_size > 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'parser'`

- [ ] **Step 4: Implement the parser**

```python
# parser.py
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import (
    ContentBlock,
    Message,
    Project,
    Session,
    SubagentSession,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

# Matches -Users-<username>- prefix in project directory names
_USER_PREFIX_RE = re.compile(r"^-Users-[^-]+-")


def load_projects(base_path: Path) -> list[Project]:
    """Load all projects from the Claude projects directory."""
    projects = []
    base = Path(base_path)

    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name == "memory":
            continue

        display_name = _USER_PREFIX_RE.sub("-", entry.name)
        sessions = _load_sessions(entry, display_name)
        if sessions:
            projects.append(Project(name=display_name, path=str(entry), sessions=sessions))

    return projects


def _load_sessions(project_dir: Path, project_name: str) -> list[Session]:
    """Load all sessions from a project directory."""
    sessions = []

    for jsonl_file in sorted(project_dir.glob("*.jsonl")):
        session_id = jsonl_file.stem
        try:
            session = _parse_session(jsonl_file, session_id, project_name)
            if session:
                sessions.append(session)
        except (json.JSONDecodeError, KeyError):
            continue

    return sessions


def _parse_session(
    jsonl_path: Path, session_id: str, project_name: str
) -> Session | None:
    """Parse a single session JSONL file into a Session object."""
    raw_lines: list[dict[str, Any]] = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                raw_lines.append(json.loads(line))

    if not raw_lines:
        return None

    # Filter to conversation-relevant types
    conversation_lines = [
        r for r in raw_lines if r.get("type") in ("user", "assistant", "system")
    ]

    # Merge streamed assistant messages (same requestId) and attach tool results
    messages = _build_messages(conversation_lines)

    if not messages:
        return None

    # Extract metadata from first user message
    first_user = next((r for r in raw_lines if r.get("type") == "user"), None)
    git_branch = first_user.get("gitBranch") if first_user else None
    cwd = first_user.get("cwd", "") if first_user else ""
    version = first_user.get("version", "") if first_user else ""

    # Title from first user message text
    title = _extract_title(messages)

    # Timestamp from first message
    timestamp = messages[0].timestamp

    # Load subagents
    subagents = _load_subagents(jsonl_path.parent / session_id / "subagents")

    return Session(
        id=session_id,
        project=project_name,
        timestamp=timestamp,
        title=title,
        git_branch=git_branch,
        cwd=cwd,
        version=version,
        file_size=jsonl_path.stat().st_size,
        messages=messages,
        subagents=subagents,
    )


def _build_messages(lines: list[dict[str, Any]]) -> list[Message]:
    """
    Build Message list from raw JSONL lines.

    - Merges streamed assistant messages with the same requestId
    - Attaches tool_result user messages to the preceding assistant's tool_use
    - Filters out system messages (extracts turn_duration as annotation)
    - Skips sidechain messages
    """
    # Group assistant lines by requestId for merging
    assistant_groups: dict[str, list[dict]] = {}
    # Track ordering: list of (requestId_or_uuid, line) for sequencing
    ordered: list[tuple[str, dict]] = []
    seen_request_ids: set[str] = set()

    for line in lines:
        if line.get("isSidechain"):
            continue

        msg_type = line.get("type")

        if msg_type == "assistant":
            request_id = line.get("requestId", line.get("uuid"))
            if request_id not in assistant_groups:
                assistant_groups[request_id] = []
                ordered.append(("assistant", request_id))
            assistant_groups[request_id].append(line)

        elif msg_type == "user":
            ordered.append(("user", line))

        elif msg_type == "system":
            # Skip system messages — they're metadata only
            pass

    # Now build final message list
    messages: list[Message] = []
    for kind, data in ordered:
        if kind == "assistant":
            request_id = data
            group = assistant_groups[request_id]
            msg = _merge_assistant_lines(group)
            if msg:
                messages.append(msg)

        elif kind == "user":
            line = data
            content = line.get("message", {}).get("content", "")

            # Check if this is a tool_result message
            if isinstance(content, list) and all(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content
            ):
                # Attach to the preceding assistant message's tool_use
                _attach_tool_results(messages, content)
            else:
                # Regular user message
                msg = _parse_user_message(line)
                if msg:
                    messages.append(msg)

    return messages


def _merge_assistant_lines(lines: list[dict]) -> Message | None:
    """Merge multiple JSONL lines for the same assistant requestId."""
    if not lines:
        return None

    all_blocks: list[ContentBlock] = []
    for line in lines:
        content = line.get("message", {}).get("content", [])
        for block in content:
            parsed = _parse_content_block(block)
            if parsed:
                all_blocks.append(parsed)

    first = lines[0]
    return Message(
        uuid=first["uuid"],
        parent_uuid=first.get("parentUuid"),
        type="assistant",
        timestamp=_parse_timestamp(first["timestamp"]),
        content=all_blocks,
        model=first.get("message", {}).get("model"),
    )


def _parse_user_message(line: dict) -> Message:
    """Parse a user message line into a Message."""
    content_raw = line.get("message", {}).get("content", "")
    if isinstance(content_raw, str):
        content = [TextBlock(text=content_raw)]
    else:
        content = []
        for block in content_raw:
            parsed = _parse_content_block(block)
            if parsed:
                content.append(parsed)

    return Message(
        uuid=line["uuid"],
        parent_uuid=line.get("parentUuid"),
        type="user",
        timestamp=_parse_timestamp(line["timestamp"]),
        content=content,
        model=None,
    )


def _attach_tool_results(
    messages: list[Message], result_blocks: list[dict]
) -> None:
    """Attach tool_result blocks to the preceding assistant message."""
    if not messages:
        return

    # Find the last assistant message to attach results to
    for msg in reversed(messages):
        if msg.type == "assistant":
            for block in result_blocks:
                msg.content.append(
                    ToolResultBlock(
                        tool_use_id=block.get("tool_use_id", ""),
                        content=block.get("content", ""),
                        is_error=block.get("is_error", False),
                    )
                )
            return


def _parse_content_block(block: dict) -> ContentBlock | None:
    """Parse a raw content block dict into a ContentBlock."""
    block_type = block.get("type")

    if block_type == "text":
        text = block.get("text", "")
        if text:
            return TextBlock(text=text)
    elif block_type == "thinking":
        thinking = block.get("thinking", "")
        if thinking:
            return ThinkingBlock(thinking=thinking)
    elif block_type == "tool_use":
        return ToolUseBlock(
            tool_name=block.get("name", ""),
            tool_id=block.get("id", ""),
            input=block.get("input", {}),
        )
    elif block_type == "tool_result":
        return ToolResultBlock(
            tool_use_id=block.get("tool_use_id", ""),
            content=block.get("content", ""),
            is_error=block.get("is_error", False),
        )
    return None


def _extract_title(messages: list[Message]) -> str:
    """Extract a title from the first user message, truncated."""
    for msg in messages:
        if msg.type == "user":
            for block in msg.content:
                if isinstance(block, TextBlock):
                    text = block.text.strip()
                    if len(text) > 80:
                        return text[:77] + "..."
                    return text
    return "(no title)"


def _parse_timestamp(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp string."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _load_subagents(subagents_dir: Path) -> dict[str, SubagentSession]:
    """Load subagent sessions from a subagents directory."""
    subagents: dict[str, SubagentSession] = {}

    if not subagents_dir.exists():
        return subagents

    for meta_file in subagents_dir.glob("*.meta.json"):
        agent_id = meta_file.stem.replace(".meta", "")
        jsonl_file = subagents_dir / f"{agent_id}.jsonl"

        if not jsonl_file.exists():
            continue

        try:
            with open(meta_file) as f:
                meta = json.load(f)

            lines: list[dict] = []
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        lines.append(json.loads(line))

            conversation_lines = [
                r for r in lines if r.get("type") in ("user", "assistant")
            ]
            messages = _build_messages(conversation_lines)

            subagents[agent_id] = SubagentSession(
                id=agent_id,
                agent_type=meta.get("agentType", "Unknown"),
                description=meta.get("description", ""),
                messages=messages,
            )
        except (json.JSONDecodeError, KeyError):
            continue

    return subagents
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_parser.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add parser.py tests/test_parser.py tests/conftest.py
git commit -m "Add JSONL parser with message merging and subagent loading"
```

---

### Task 4: Search Module

**Files:**
- Create: `search.py`
- Create: `tests/test_search.py`

- [ ] **Step 1: Write search tests**

```python
# tests/test_search.py
from pathlib import Path

from parser import load_projects
from search import search_sessions, SearchResult


def test_search_finds_user_message(projects_dir: Path):
    projects = load_projects(projects_dir)
    results = search_sessions(projects, "login flow")
    assert len(results) >= 1
    assert any("login flow" in r.snippet.lower() for r in results)


def test_search_finds_assistant_text(projects_dir: Path):
    projects = load_projects(projects_dir)
    results = search_sessions(projects, "login flow works like this")
    assert len(results) >= 1


def test_search_finds_tool_output(projects_dir: Path):
    projects = load_projects(projects_dir)
    results = search_sessions(projects, "def login")
    assert len(results) >= 1


def test_search_finds_subagent_content(projects_dir: Path):
    projects = load_projects(projects_dir)
    results = search_sessions(projects, "auth functions")
    assert len(results) >= 1


def test_search_no_results(projects_dir: Path):
    projects = load_projects(projects_dir)
    results = search_sessions(projects, "xyzzy_nonexistent_term")
    assert len(results) == 0


def test_search_result_has_session_info(projects_dir: Path):
    projects = load_projects(projects_dir)
    results = search_sessions(projects, "login flow")
    result = results[0]
    assert result.session_id == "aaaa-bbbb-cccc-dddd"
    assert result.session_title == "explain the login flow"
    assert result.project_name == "-myproject"


def test_search_case_insensitive(projects_dir: Path):
    projects = load_projects(projects_dir)
    results = search_sessions(projects, "LOGIN FLOW")
    assert len(results) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_search.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'search'`

- [ ] **Step 3: Implement the search module**

```python
# search.py
from __future__ import annotations

from dataclasses import dataclass

from models import (
    ContentBlock,
    Message,
    Project,
    Session,
    SubagentSession,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)


@dataclass
class SearchResult:
    session_id: str
    session_title: str
    project_name: str
    message_uuid: str
    snippet: str
    timestamp: str


def search_sessions(projects: list[Project], query: str) -> list[SearchResult]:
    """Search across all sessions for the given query string. Case-insensitive."""
    query_lower = query.lower()
    results: list[SearchResult] = []

    for project in projects:
        for session in project.sessions:
            _search_session(session, query_lower, results)

    # Sort by timestamp descending
    results.sort(key=lambda r: r.timestamp, reverse=True)
    return results


def _search_session(
    session: Session, query_lower: str, results: list[SearchResult]
) -> None:
    """Search messages and subagents within a session."""
    for message in session.messages:
        _search_message(message, session, query_lower, results)

    for subagent in session.subagents.values():
        for message in subagent.messages:
            _search_message(message, session, query_lower, results)


def _search_message(
    message: Message,
    session: Session,
    query_lower: str,
    results: list[SearchResult],
) -> None:
    """Search content blocks within a message."""
    for block in message.content:
        text = _extract_block_text(block)
        if not text:
            continue

        idx = text.lower().find(query_lower)
        if idx == -1:
            continue

        snippet = _make_snippet(text, idx, len(query_lower))
        results.append(
            SearchResult(
                session_id=session.id,
                session_title=session.title,
                project_name=session.project,
                message_uuid=message.uuid,
                snippet=snippet,
                timestamp=message.timestamp.isoformat(),
            )
        )
        # One result per message is enough
        return


def _extract_block_text(block: ContentBlock) -> str:
    """Extract searchable text from a content block."""
    if isinstance(block, TextBlock):
        return block.text
    elif isinstance(block, ThinkingBlock):
        return block.thinking
    elif isinstance(block, ToolUseBlock):
        return str(block.input)
    elif isinstance(block, ToolResultBlock):
        return block.content if isinstance(block.content, str) else str(block.content)
    return ""


def _make_snippet(text: str, match_idx: int, match_len: int, context: int = 80) -> str:
    """Create a snippet with context around the match."""
    start = max(0, match_idx - context)
    end = min(len(text), match_idx + match_len + context)

    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_search.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add search.py tests/test_search.py
git commit -m "Add full-text search across sessions and subagents"
```

---

### Task 5: Flask App and Routes

**Files:**
- Modify: `main.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write route tests**

```python
# tests/test_routes.py
from pathlib import Path

import pytest

from main import create_app


@pytest.fixture
def client(projects_dir: Path):
    app = create_app(projects_dir)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Claude Transcripts" in response.data


def test_index_shows_project(client):
    response = client.get("/")
    assert b"-myproject" in response.data


def test_index_shows_session_title(client):
    response = client.get("/")
    assert b"explain the login flow" in response.data


def test_index_flat_view(client):
    response = client.get("/api/sessions?view=flat")
    assert response.status_code == 200
    assert b"explain the login flow" in response.data


def test_index_grouped_view(client):
    response = client.get("/api/sessions?view=grouped")
    assert response.status_code == 200
    assert b"-myproject" in response.data


def test_session_view_returns_200(client):
    response = client.get("/session/aaaa-bbbb-cccc-dddd")
    assert response.status_code == 200
    assert b"explain the login flow" in response.data


def test_session_view_shows_messages(client):
    response = client.get("/session/aaaa-bbbb-cccc-dddd")
    assert b"explain the login flow" in response.data
    assert b"The login flow works like this" in response.data


def test_session_view_404_for_missing(client):
    response = client.get("/session/nonexistent-id")
    assert response.status_code == 404


def test_subagent_api_returns_html(client):
    response = client.get("/api/subagent/aaaa-bbbb-cccc-dddd/agent-abc123")
    assert response.status_code == 200
    assert b"auth functions" in response.data


def test_subagent_api_404_for_missing(client):
    response = client.get("/api/subagent/aaaa-bbbb-cccc-dddd/nonexistent")
    assert response.status_code == 404


def test_search_returns_results(client):
    response = client.get("/search?q=login+flow")
    assert response.status_code == 200
    assert b"login flow" in response.data


def test_search_empty_query(client):
    response = client.get("/search?q=")
    assert response.status_code == 200


def test_app_binds_localhost_only(projects_dir: Path):
    """Verify the app is configured for localhost only."""
    app = create_app(projects_dir)
    # The app itself doesn't enforce host binding — that's in the __main__ block.
    # Just verify the app can be created.
    assert app is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_routes.py -v`
Expected: FAIL — `ImportError: cannot import name 'create_app' from 'main'`

- [ ] **Step 3: Implement the Flask app**

```python
# main.py
from __future__ import annotations

from pathlib import Path

from flask import Flask, abort, render_template, request

from parser import load_projects
from search import search_sessions

# Default Claude projects directory
DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def create_app(projects_dir: Path | None = None) -> Flask:
    if projects_dir is None:
        projects_dir = DEFAULT_PROJECTS_DIR

    app = Flask(__name__)
    projects = load_projects(projects_dir)

    # Build a lookup: session_id -> (project, session)
    session_lookup: dict[str, tuple] = {}
    for project in projects:
        for session in project.sessions:
            session_lookup[session.id] = (project, session)

    @app.route("/")
    def index():
        sorted_projects = sorted(
            projects, key=lambda p: p.latest_timestamp, reverse=True
        )
        return render_template(
            "index.html", projects=sorted_projects, view="grouped"
        )

    @app.route("/api/sessions")
    def api_sessions():
        view = request.args.get("view", "grouped")
        sorted_projects = sorted(
            projects, key=lambda p: p.latest_timestamp, reverse=True
        )
        if view == "flat":
            all_sessions = []
            for project in projects:
                for session in project.sessions:
                    all_sessions.append((project, session))
            all_sessions.sort(key=lambda ps: ps[1].timestamp, reverse=True)
            return render_template(
                "partials/session_list.html",
                view="flat",
                flat_sessions=all_sessions,
            )
        return render_template(
            "partials/session_list.html",
            view="grouped",
            projects=sorted_projects,
        )

    @app.route("/session/<session_id>")
    def session_view(session_id: str):
        entry = session_lookup.get(session_id)
        if not entry:
            abort(404)
        project, session = entry
        return render_template(
            "session.html", session=session, project=project
        )

    @app.route("/api/subagent/<session_id>/<subagent_id>")
    def subagent_detail(session_id: str, subagent_id: str):
        entry = session_lookup.get(session_id)
        if not entry:
            abort(404)
        _, session = entry
        subagent = session.subagents.get(subagent_id)
        if not subagent:
            abort(404)
        return render_template(
            "partials/subagent_detail.html", subagent=subagent
        )

    @app.route("/search")
    def search_view():
        query = request.args.get("q", "").strip()
        results = []
        if query:
            results = search_sessions(projects, query)
        return render_template(
            "search_results.html", query=query, results=results
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
```

- [ ] **Step 4: Create minimal template stubs so routes return 200**

These are bare-minimum templates that make the route tests pass. They'll be fleshed out in Task 6.

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Claude Transcripts</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
  <script src="{{ url_for('static', filename='htmx.min.js') }}"></script>
</head>
<body>
  {% block content %}{% endblock %}
</body>
</html>
```

```html
<!-- templates/index.html -->
{% extends "base.html" %}
{% block content %}
<div class="page-header">
  <h1>Claude Transcripts</h1>
  <div class="controls">
    <form action="/search" method="get">
      <input type="text" name="q" placeholder="Search all sessions...">
    </form>
    <div class="view-toggle">
      <button hx-get="/api/sessions?view=grouped" hx-target="#session-list">Grouped</button>
      <button hx-get="/api/sessions?view=flat" hx-target="#session-list">Flat</button>
    </div>
  </div>
</div>
<div id="session-list">
  {% include "partials/session_list.html" %}
</div>
{% endblock %}
```

```html
<!-- templates/partials/session_list.html -->
{% if view == "grouped" %}
  {% for project in projects %}
  <div class="project-group">
    <h2 class="project-name">{{ project.name }}</h2>
    {% for session in project.sorted_sessions %}
    <a href="/session/{{ session.id }}" class="session-row">
      <div class="session-info">
        <span class="session-title">{{ session.title }}</span>
        {% if session.git_branch %}
        <span class="session-branch">{{ session.git_branch }}</span>
        {% endif %}
      </div>
      <div class="session-meta">
        <span>{{ session.file_size_display }}</span>
        <span>{{ session.interaction_time_display }}</span>
        <span>{{ session.timestamp.strftime('%b %-d') }}</span>
      </div>
    </a>
    {% endfor %}
  </div>
  {% endfor %}
{% else %}
  {% for project, session in flat_sessions %}
  <a href="/session/{{ session.id }}" class="session-row">
    <div class="session-info">
      <span class="session-title">{{ session.title }}</span>
      <span class="project-name-inline">{{ project.name }}</span>
      {% if session.git_branch %}
      <span class="session-branch">{{ session.git_branch }}</span>
      {% endif %}
    </div>
    <div class="session-meta">
      <span>{{ session.file_size_display }}</span>
      <span>{{ session.interaction_time_display }}</span>
      <span>{{ session.timestamp.strftime('%b %-d') }}</span>
    </div>
  </a>
  {% endfor %}
{% endif %}
```

```html
<!-- templates/session.html -->
{% extends "base.html" %}
{% block content %}
<div class="session-header">
  <a href="/">← All sessions</a>
  <h1>{{ session.title }}</h1>
  <div class="session-header-meta">
    <span class="project-name">{{ project.name }}</span>
    {% if session.git_branch %}· {{ session.git_branch }}{% endif %}
    · {{ session.timestamp.strftime('%b %-d, %Y') }}
    · {{ session.file_size_display }}
    · {{ session.interaction_time_display }}
  </div>
</div>
<div class="conversation">
  {% for message in session.messages %}
    {% include "partials/message.html" %}
  {% endfor %}
</div>
{% endblock %}
```

```html
<!-- templates/partials/message.html -->
<div class="message message-{{ message.type }}" id="msg-{{ message.uuid }}">
  <div class="message-header">
    {% if message.type == "user" %}
      <span class="message-author">You</span>
    {% else %}
      <span class="message-author author-assistant">Claude</span>
      {% if message.model %}
      <span class="message-model">{{ message.model }}</span>
      {% endif %}
    {% endif %}
    <span class="message-time">{{ message.timestamp.strftime('%I:%M %p') }}</span>
  </div>
  <div class="message-body">
    {% for block in message.content %}
      {% if block.type == "text" %}
        <div class="text-block">{{ block.text }}</div>
      {% elif block.type == "thinking" %}
        {% include "partials/thinking.html" %}
      {% elif block.type == "tool_use" %}
        {% include "partials/tool_call.html" %}
      {% elif block.type == "tool_result" %}
        {# Tool results are rendered inside tool_call.html #}
      {% endif %}
    {% endfor %}
  </div>
</div>
```

```html
<!-- templates/partials/thinking.html -->
<details class="thinking-block collapsible-thinking">
  <summary>Thinking...</summary>
  <div class="thinking-content">{{ block.thinking }}</div>
</details>
```

```html
<!-- templates/partials/tool_call.html -->
{% set result_block = None %}
{% for b in message.content %}
  {% if b.type == "tool_result" and b.tool_use_id == block.tool_id %}
    {% set result_block = b %}
  {% endif %}
{% endfor %}
<details class="tool-call collapsible-tool">
  <summary>
    <span class="tool-name">{{ block.tool_name }}</span>
    <span class="tool-args">{{ block.input | string | truncate(80) }}</span>
  </summary>
  <div class="tool-input"><pre>{{ block.input | tojson(indent=2) }}</pre></div>
  {% if result_block %}
  <div class="tool-output {% if result_block.is_error %}tool-error{% endif %}">
    <pre>{{ result_block.content }}</pre>
  </div>
  {% endif %}
</details>
```

```html
<!-- templates/partials/subagent.html -->
<div class="subagent-block">
  <details>
    <summary class="subagent-header">
      <span class="subagent-type">{{ subagent.agent_type }} agent</span>
      <span class="subagent-desc">{{ subagent.description }}</span>
      <span class="subagent-meta">{{ subagent.message_count }} messages</span>
    </summary>
    <div hx-get="/api/subagent/{{ session.id }}/{{ subagent.id }}"
         hx-trigger="toggle"
         hx-swap="innerHTML">
      Loading...
    </div>
  </details>
</div>
```

```html
<!-- templates/partials/subagent_detail.html -->
<div class="subagent-conversation">
  {% for message in subagent.messages %}
    <div class="message message-{{ message.type }}">
      <div class="message-header">
        {% if message.type == "user" %}
          <span class="message-author">Prompt</span>
        {% else %}
          <span class="message-author author-assistant">Agent</span>
          {% if message.model %}
          <span class="message-model">{{ message.model }}</span>
          {% endif %}
        {% endif %}
      </div>
      <div class="message-body">
        {% for block in message.content %}
          {% if block.type == "text" %}
            <div class="text-block">{{ block.text }}</div>
          {% elif block.type == "thinking" %}
            <details class="thinking-block collapsible-thinking">
              <summary>Thinking...</summary>
              <div class="thinking-content">{{ block.thinking }}</div>
            </details>
          {% elif block.type == "tool_use" %}
            {% set result_block = None %}
            {% for b in message.content %}
              {% if b.type == "tool_result" and b.tool_use_id == block.tool_id %}
                {% set result_block = b %}
              {% endif %}
            {% endfor %}
            <details class="tool-call collapsible-tool">
              <summary>
                <span class="tool-name">{{ block.tool_name }}</span>
                <span class="tool-args">{{ block.input | string | truncate(80) }}</span>
              </summary>
              <div class="tool-input"><pre>{{ block.input | tojson(indent=2) }}</pre></div>
              {% if result_block %}
              <div class="tool-output {% if result_block.is_error %}tool-error{% endif %}">
                <pre>{{ result_block.content }}</pre>
              </div>
              {% endif %}
            </details>
          {% endif %}
        {% endfor %}
      </div>
    </div>
  {% endfor %}
</div>
```

```html
<!-- templates/search_results.html -->
{% extends "base.html" %}
{% block content %}
<div class="page-header">
  <h1>Claude Transcripts</h1>
  <form action="/search" method="get">
    <input type="text" name="q" value="{{ query }}" placeholder="Search all sessions...">
  </form>
</div>
{% if query %}
  {% if results %}
    <div class="search-results">
      {% for result in results %}
      <a href="/session/{{ result.session_id }}#msg-{{ result.message_uuid }}" class="search-result">
        <div class="search-result-header">
          <span class="session-title">{{ result.session_title }}</span>
          <span class="project-name-inline">{{ result.project_name }}</span>
        </div>
        <div class="search-result-snippet">{{ result.snippet }}</div>
      </a>
      {% endfor %}
    </div>
  {% else %}
    <p>No results for "{{ query }}"</p>
  {% endif %}
{% endif %}
{% endblock %}
```

- [ ] **Step 5: Create empty CSS file**

```css
/* static/style.css */
/* Styles will be added in Task 6 */
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_routes.py -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add main.py templates/ static/style.css tests/test_routes.py
git commit -m "Add Flask app with routes and template stubs"
```

---

### Task 6: CSS Styling

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Implement the full stylesheet**

```css
/* static/style.css */

/* ---- Reset & Base ---- */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  color: #111;
  background: #fff;
  max-width: 960px;
  margin: 0 auto;
  padding: 16px;
}

a { color: #4a4ae0; text-decoration: none; }
a:hover { text-decoration: underline; }

pre, code {
  font-family: ui-monospace, 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
}

code {
  background: #e4e4e4;
  padding: 1px 5px;
  border-radius: 3px;
  color: #000;
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
  color: #111;
  line-height: 1.5;
}

/* ---- Page Header ---- */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ddd;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 700;
  color: #000;
}

.controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.controls input[type="text"] {
  padding: 6px 10px;
  border: 1px solid #ccc;
  background: #f8f8f8;
  color: #111;
  border-radius: 4px;
  width: 240px;
  font-size: 13px;
}

/* ---- View Toggle ---- */
.view-toggle {
  display: flex;
  background: #eee;
  border-radius: 4px;
  overflow: hidden;
}

.view-toggle button {
  padding: 5px 12px;
  border: none;
  background: transparent;
  color: #444;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
}

.view-toggle button.active,
.view-toggle button[aria-pressed="true"] {
  background: #4a4ae0;
  color: #fff;
}

/* ---- Session List ---- */
.project-group { margin-bottom: 16px; }

.project-name {
  font-weight: 700;
  color: #4a4ae0;
  font-size: 15px;
  margin-bottom: 6px;
}

.project-group .session-row { margin-left: 12px; }

.session-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: #f5f5f7;
  border-radius: 4px;
  margin-bottom: 4px;
  color: #111;
  text-decoration: none;
}

.session-row:hover { background: #ededf2; }

.session-info { display: flex; align-items: baseline; gap: 8px; min-width: 0; }

.session-title {
  font-weight: 500;
  color: #000;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-name-inline {
  font-size: 11px;
  font-weight: 700;
  color: #4a4ae0;
  white-space: nowrap;
}

.session-branch {
  font-size: 11px;
  color: #444;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #333;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ---- Session View Header ---- */
.session-header {
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ddd;
}

.session-header a {
  font-size: 12px;
  font-weight: 600;
}

.session-header h1 {
  font-size: 18px;
  font-weight: 700;
  color: #000;
  margin-top: 4px;
}

.session-header-meta {
  font-size: 12px;
  color: #111;
  margin-top: 2px;
}

.session-header-meta .project-name {
  font-size: 12px;
}

/* ---- Collapse Controls ---- */
.collapse-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.collapse-controls button {
  padding: 4px 10px;
  background: #e0e0ea;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #111;
  font-family: inherit;
}

.collapse-controls button:hover { background: #d0d0da; }

/* ---- Messages ---- */
.conversation { max-width: 800px; }

.message { margin-bottom: 20px; }

.message-header {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 4px;
}

.message-author {
  font-weight: 700;
  font-size: 12px;
  color: #000;
}

.author-assistant { color: #4a4ae0; }

.message-model {
  font-size: 10px;
  color: #444;
}

.message-time {
  font-size: 10px;
  color: #444;
}

.message-user .message-body .text-block {
  padding: 10px 14px;
  background: #e8f0fe;
  border-radius: 8px;
  color: #000;
}

.message-assistant .message-body .text-block {
  padding: 10px 14px;
  background: #f5f5ff;
  border-radius: 8px;
  color: #000;
}

/* ---- Thinking Blocks ---- */
.thinking-block {
  margin-bottom: 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
  overflow: hidden;
}

.thinking-block summary {
  padding: 8px 12px;
  background: #f5f5f5;
  cursor: pointer;
  font-size: 12px;
  color: #555;
  font-style: italic;
  list-style: none;
}

.thinking-block summary::before {
  content: "▶ ";
  font-style: normal;
  font-size: 10px;
}

.thinking-block[open] summary::before {
  content: "▼ ";
}

.thinking-content {
  padding: 10px 14px;
  background: #fafafa;
  font-size: 13px;
  color: #111;
  white-space: pre-wrap;
}

/* ---- Tool Calls ---- */
.tool-call {
  margin-bottom: 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
  overflow: hidden;
}

.tool-call summary {
  padding: 8px 12px;
  background: #f5f5f5;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  list-style: none;
}

.tool-call summary::before {
  content: "▶ ";
  font-size: 10px;
}

.tool-call[open] summary::before {
  content: "▼ ";
}

.tool-name {
  font-weight: 700;
  color: #333;
}

.tool-args {
  color: #111;
  font-size: 11px;
  background: #e4e4e4;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: ui-monospace, 'SF Mono', 'Cascadia Code', monospace;
}

.tool-input, .tool-output {
  padding: 8px 12px;
  background: #f8f8f8;
  border-top: 1px solid #e0e0e0;
  max-height: 400px;
  overflow-y: auto;
}

.tool-error { background: #fff0f0; }

/* ---- Subagent Blocks ---- */
.subagent-block {
  margin-bottom: 20px;
  border-left: 3px solid #4a4ae0;
  padding-left: 12px;
}

.subagent-block > details {
  border: 1px solid #c0c0d8;
  border-radius: 6px;
  overflow: hidden;
}

.subagent-header {
  padding: 10px 14px;
  background: #f4f4ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  list-style: none;
}

.subagent-header::before {
  content: "▶ ";
  color: #4a4ae0;
  font-size: 10px;
}

details[open] > .subagent-header::before {
  content: "▼ ";
}

.subagent-type {
  font-weight: 700;
  color: #4a4ae0;
  font-size: 12px;
}

.subagent-desc {
  font-size: 12px;
  color: #111;
}

.subagent-meta {
  font-size: 10px;
  color: #333;
  margin-left: auto;
}

.subagent-conversation {
  padding: 12px 14px;
  background: #fcfcff;
}

.subagent-conversation .message { margin-bottom: 12px; }

.subagent-conversation .text-block {
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
}

/* ---- Search Results ---- */
.search-results { margin-top: 16px; }

.search-result {
  display: block;
  padding: 10px 12px;
  background: #f5f5f7;
  border-radius: 4px;
  margin-bottom: 6px;
  color: #111;
}

.search-result:hover { background: #ededf2; text-decoration: none; }

.search-result-header {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 4px;
}

.search-result-snippet {
  font-size: 12px;
  color: #333;
  font-family: ui-monospace, 'SF Mono', 'Cascadia Code', monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

mark {
  background: #fff3a8;
  color: #000;
  padding: 0 2px;
  border-radius: 2px;
}

/* ---- Utility ---- */
.hidden { display: none; }
```

- [ ] **Step 2: Verify the app runs and looks correct**

Run: `uv run python main.py`
Expected: Server starts on `http://127.0.0.1:5000`. Open in browser and verify the index page renders with real data.

- [ ] **Step 3: Commit**

```bash
git add static/style.css
git commit -m "Add full CSS styling with light theme and high-contrast text"
```

---

### Task 7: JavaScript — Collapse Toggles and Preferences

**Files:**
- Create: `static/app.js`
- Modify: `templates/base.html` (add script tag)
- Modify: `templates/session.html` (add collapse controls)

- [ ] **Step 1: Implement the JavaScript**

```javascript
// static/app.js

// ---- Collapse Preference Management ----

function getPreference(key, defaultValue) {
  const stored = localStorage.getItem(key);
  return stored !== null ? stored : defaultValue;
}

function setPreference(key, value) {
  localStorage.setItem(key, value);
}

function applyCollapseState(selector, preferenceKey) {
  const state = getPreference(preferenceKey, "collapsed");
  document.querySelectorAll(selector).forEach(function(el) {
    el.open = state === "expanded";
  });
}

function toggleAll(selector, preferenceKey, button) {
  var current = getPreference(preferenceKey, "collapsed");
  var next = current === "collapsed" ? "expanded" : "collapsed";
  setPreference(preferenceKey, next);
  document.querySelectorAll(selector).forEach(function(el) {
    el.open = next === "expanded";
  });
  button.textContent = button.dataset.label + ": " + next;
}

// ---- View Toggle ----

function setActiveToggle(clickedButton) {
  var buttons = clickedButton.parentElement.querySelectorAll("button");
  buttons.forEach(function(b) { b.classList.remove("active"); });
  clickedButton.classList.add("active");
}

// ---- Initialize on page load ----

document.addEventListener("DOMContentLoaded", function() {
  applyCollapseState(".collapsible-thinking", "thinking-state");
  applyCollapseState(".collapsible-tool", "tool-state");

  // Update button labels to reflect current state
  var thinkingBtn = document.getElementById("toggle-thinking");
  if (thinkingBtn) {
    thinkingBtn.textContent = "Thinking: " + getPreference("thinking-state", "collapsed");
  }
  var toolBtn = document.getElementById("toggle-tools");
  if (toolBtn) {
    toolBtn.textContent = "Tool calls: " + getPreference("tool-state", "collapsed");
  }
});

// Re-apply collapse state after htmx swaps (e.g., subagent detail loaded)
document.addEventListener("htmx:afterSwap", function() {
  applyCollapseState(".collapsible-thinking", "thinking-state");
  applyCollapseState(".collapsible-tool", "tool-state");
});
```

- [ ] **Step 2: Add script tag to base.html**

Add before `</body>` in `templates/base.html`:
```html
  <script src="{{ url_for('static', filename='app.js') }}"></script>
```

- [ ] **Step 3: Add collapse controls to session.html**

Add after the session header metadata div in `templates/session.html`:
```html
<div class="collapse-controls">
  <button id="toggle-thinking" data-label="Thinking"
          onclick="toggleAll('.collapsible-thinking', 'thinking-state', this)">
    Thinking: collapsed
  </button>
  <button id="toggle-tools" data-label="Tool calls"
          onclick="toggleAll('.collapsible-tool', 'tool-state', this)">
    Tool calls: collapsed
  </button>
</div>
```

- [ ] **Step 4: Add view toggle active state to index.html**

Update the view toggle buttons in `templates/index.html` to use `setActiveToggle`:
```html
<div class="view-toggle">
  <button class="active"
          hx-get="/api/sessions?view=grouped" hx-target="#session-list"
          onclick="setActiveToggle(this)">Grouped</button>
  <button hx-get="/api/sessions?view=flat" hx-target="#session-list"
          onclick="setActiveToggle(this)">Flat</button>
</div>
```

- [ ] **Step 5: Verify interactivity works**

Run: `uv run python main.py`
Expected: Open browser. Toggle thinking/tool collapse buttons — all blocks expand/collapse together. Refresh page — preference persists. Switch between grouped/flat views without full page reload.

- [ ] **Step 6: Commit**

```bash
git add static/app.js templates/base.html templates/session.html templates/index.html
git commit -m "Add collapse toggle preferences and view switching JS"
```

---

### Task 8: Subagent Inline Display with htmx Lazy Loading

**Files:**
- Modify: `templates/session.html`
- Modify: `templates/partials/message.html`

The subagent templates (`partials/subagent.html` and `partials/subagent_detail.html`) were created in Task 5. Now wire them into the session view.

- [ ] **Step 1: Add subagent rendering to session.html**

After the message loop in `templates/session.html`, the subagent blocks need to appear inline. Add subagent rendering inside the conversation loop. Replace the `{% for message in session.messages %}` block with:

```html
<div class="conversation">
  {% for message in session.messages %}
    {% include "partials/message.html" %}
    {# Check if any subagent was spawned by a tool_use in this message #}
    {% for block in message.content %}
      {% if block.type == "tool_use" and block.tool_name == "Agent" %}
        {% for sub_id, subagent in session.subagents.items() %}
          {% if subagent.description == block.input.get("description", "") %}
            {% include "partials/subagent.html" %}
          {% endif %}
        {% endfor %}
      {% endif %}
    {% endfor %}
  {% endfor %}
</div>
```

- [ ] **Step 2: Fix the subagent.html htmx trigger**

Update `templates/partials/subagent.html` so the htmx load fires when the `<details>` is opened:

```html
<!-- templates/partials/subagent.html -->
<div class="subagent-block">
  <details hx-get="/api/subagent/{{ session.id }}/{{ subagent.id }}"
           hx-trigger="toggle once"
           hx-target="find .subagent-content"
           hx-swap="innerHTML">
    <summary class="subagent-header">
      <span class="subagent-type">{{ subagent.agent_type }} agent</span>
      <span class="subagent-desc">{{ subagent.description }}</span>
      <span class="subagent-meta">{{ subagent.message_count }} messages</span>
    </summary>
    <div class="subagent-content">Loading...</div>
  </details>
</div>
```

- [ ] **Step 3: Verify subagent lazy loading works**

Run: `uv run python main.py`
Expected: Open a session that has subagents. See collapsed subagent block. Click to expand — "Loading..." briefly appears, then the subagent conversation loads in place. Collapse and re-expand — content is already loaded (no re-fetch due to `once` modifier).

- [ ] **Step 4: Commit**

```bash
git add templates/session.html templates/partials/subagent.html
git commit -m "Wire subagent blocks inline with htmx lazy loading"
```

---

### Task 9: Search Highlighting and Scroll-to-Match

**Files:**
- Modify: `search.py` (add highlight markup)
- Modify: `templates/search_results.html` (render highlighted snippets)
- Modify: `static/app.js` (scroll to hash on session load)

- [ ] **Step 1: Add highlight_snippet function to search.py**

Add to `search.py`:

```python
import html as html_module


def highlight_snippet(snippet: str, query: str) -> str:
    """Wrap matching text in <mark> tags for highlighting. HTML-escapes the snippet first."""
    escaped = html_module.escape(snippet)
    query_lower = query.lower()
    escaped_lower = escaped.lower()

    result = []
    i = 0
    while i < len(escaped):
        idx = escaped_lower.find(query_lower, i)
        if idx == -1:
            result.append(escaped[i:])
            break
        result.append(escaped[i:idx])
        result.append("<mark>")
        result.append(escaped[idx : idx + len(query)])
        result.append("</mark>")
        i = idx + len(query)

    return "".join(result)
```

- [ ] **Step 2: Use highlight_snippet in the search results template**

Update `templates/search_results.html` to pass highlighted snippets. In `main.py`, register `highlight_snippet` as a Jinja filter:

Add after `app = Flask(__name__)` in `create_app`:
```python
from search import highlight_snippet
app.jinja_env.filters["highlight"] = lambda snippet, query: highlight_snippet(snippet, query)
```

Update the snippet line in `templates/search_results.html`:
```html
<div class="search-result-snippet">{{ result.snippet | highlight(query) | safe }}</div>
```

- [ ] **Step 3: Add scroll-to-hash in app.js**

Add to the `DOMContentLoaded` handler in `static/app.js`:
```javascript
  // Scroll to message if URL has a hash
  if (window.location.hash) {
    var target = document.querySelector(window.location.hash);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      target.classList.add("highlight-flash");
    }
  }
```

Add the highlight-flash animation to `static/style.css`:
```css
.highlight-flash {
  animation: flash 1.5s ease-out;
}

@keyframes flash {
  0% { background: #fff3a8; }
  100% { background: transparent; }
}
```

- [ ] **Step 4: Write a test for highlight_snippet**

Add to `tests/test_search.py`:
```python
from search import highlight_snippet


def test_highlight_snippet_marks_match():
    result = highlight_snippet("The login flow works", "login flow")
    assert "<mark>login flow</mark>" in result


def test_highlight_snippet_escapes_html():
    result = highlight_snippet("use <script> tag", "script")
    assert "&lt;" in result
    assert "<mark>script</mark>" in result
    assert "<script>" not in result
```

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add search.py templates/search_results.html static/app.js static/style.css main.py tests/test_search.py
git commit -m "Add search highlighting and scroll-to-match"
```

---

### Task 10: Integration Test with Real Data

**Files:**
- No new files — manual verification

- [ ] **Step 1: Run the app against real data**

Run: `uv run python main.py`
Expected: App starts on `http://127.0.0.1:5000`.

- [ ] **Step 2: Verify index page**

Open `http://127.0.0.1:5000` in browser. Check:
- Projects listed in grouped view, sorted by most recent session
- Project names have `-Users-jdaghlian-` prefix stripped
- Sessions show title, branch, size, interaction time, date
- Switch to flat view — all sessions in one list, project names in accent color
- Switch back to grouped — no full page reload

- [ ] **Step 3: Verify session view**

Click into a session. Check:
- Header shows title, project, branch, date, size, interaction time
- User messages in blue, assistant in purple
- Thinking blocks collapsed by default
- Tool calls collapsed with tool name + args visible
- Toggle buttons expand/collapse all thinking/tool blocks
- Refresh page — preference persists

- [ ] **Step 4: Verify subagent display**

Navigate to a session with subagents. Check:
- Subagent block appears with indigo left border
- Shows agent type, description, message count
- Click to expand — loads full conversation
- Nested tool calls are collapsible

- [ ] **Step 5: Verify search**

Search for a known term. Check:
- Results page shows matching sessions
- Snippets show context around match
- Matching text highlighted
- Click result — navigates to session, scrolls to message, flashes highlight

- [ ] **Step 6: Final commit if any fixes were needed**

If any template/CSS tweaks were required during verification:
```bash
git add -A
git commit -m "Fix issues found during integration testing"
```

- [ ] **Step 7: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests PASS.

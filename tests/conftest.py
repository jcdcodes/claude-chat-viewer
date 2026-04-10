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

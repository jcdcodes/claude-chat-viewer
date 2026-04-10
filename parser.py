# parser.py
from __future__ import annotations

import json
import re
from datetime import datetime
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

_USER_PREFIX_RE = re.compile(r"^-Users-[^-]+-")


def load_projects(base_path: Path) -> list[Project]:
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


def _parse_session(jsonl_path: Path, session_id: str, project_name: str) -> Session | None:
    raw_lines: list[dict[str, Any]] = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                raw_lines.append(json.loads(line))
    if not raw_lines:
        return None

    conversation_lines = [r for r in raw_lines if r.get("type") in ("user", "assistant", "system")]
    messages = _build_messages(conversation_lines)
    if not messages:
        return None

    first_user = next((r for r in raw_lines if r.get("type") == "user"), None)
    git_branch = first_user.get("gitBranch") if first_user else None
    cwd = first_user.get("cwd", "") if first_user else ""
    version = first_user.get("version", "") if first_user else ""
    title = _extract_title(messages)
    timestamp = messages[0].timestamp
    subagents = _load_subagents(jsonl_path.parent / session_id / "subagents")

    return Session(
        id=session_id, project=project_name, timestamp=timestamp,
        title=title, git_branch=git_branch, cwd=cwd, version=version,
        file_size=jsonl_path.stat().st_size, messages=messages, subagents=subagents,
    )


def _build_messages(lines: list[dict[str, Any]]) -> list[Message]:
    assistant_groups: dict[str, list[dict]] = {}
    ordered: list[tuple[str, Any]] = []

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

    messages: list[Message] = []
    for kind, data in ordered:
        if kind == "assistant":
            group = assistant_groups[data]
            msg = _merge_assistant_lines(group)
            if msg:
                messages.append(msg)
        elif kind == "user":
            content = data.get("message", {}).get("content", "")
            if isinstance(content, list) and all(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in content
            ):
                _attach_tool_results(messages, content)
            else:
                msg = _parse_user_message(data)
                if msg:
                    messages.append(msg)
    return messages


def _merge_assistant_lines(lines: list[dict]) -> Message | None:
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
        uuid=first["uuid"], parent_uuid=first.get("parentUuid"),
        type="assistant", timestamp=_parse_timestamp(first["timestamp"]),
        content=all_blocks, model=first.get("message", {}).get("model"),
    )


def _parse_user_message(line: dict) -> Message:
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
        uuid=line["uuid"], parent_uuid=line.get("parentUuid"),
        type="user", timestamp=_parse_timestamp(line["timestamp"]),
        content=content, model=None,
    )


def _attach_tool_results(messages: list[Message], result_blocks: list[dict]) -> None:
    if not messages:
        return
    for msg in reversed(messages):
        if msg.type == "assistant":
            for block in result_blocks:
                msg.content.append(ToolResultBlock(
                    tool_use_id=block.get("tool_use_id", ""),
                    content=block.get("content", ""),
                    is_error=block.get("is_error", False),
                ))
            return


def _parse_content_block(block: dict) -> ContentBlock | None:
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
            tool_name=block.get("name", ""), tool_id=block.get("id", ""),
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
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _load_subagents(subagents_dir: Path) -> dict[str, SubagentSession]:
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
            conversation_lines = [r for r in lines if r.get("type") in ("user", "assistant")]
            messages = _build_messages(conversation_lines)
            subagents[agent_id] = SubagentSession(
                id=agent_id, agent_type=meta.get("agentType", "Unknown"),
                description=meta.get("description", ""), messages=messages,
            )
        except (json.JSONDecodeError, KeyError):
            continue
    return subagents

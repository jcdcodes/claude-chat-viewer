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

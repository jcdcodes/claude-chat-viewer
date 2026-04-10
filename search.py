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
    query_lower = query.lower()
    results: list[SearchResult] = []
    for project in projects:
        for session in project.sessions:
            _search_session(session, query_lower, results)
    results.sort(key=lambda r: r.timestamp, reverse=True)
    return results


def _search_session(session: Session, query_lower: str, results: list[SearchResult]) -> None:
    for message in session.messages:
        _search_message(message, session, query_lower, results)
    for subagent in session.subagents.values():
        for message in subagent.messages:
            _search_message(message, session, query_lower, results)


def _search_message(message: Message, session: Session, query_lower: str, results: list[SearchResult]) -> None:
    for block in message.content:
        text = _extract_block_text(block)
        if not text:
            continue
        idx = text.lower().find(query_lower)
        if idx == -1:
            continue
        snippet = _make_snippet(text, idx, len(query_lower))
        results.append(SearchResult(
            session_id=session.id, session_title=session.title,
            project_name=session.project, message_uuid=message.uuid,
            snippet=snippet, timestamp=message.timestamp.isoformat(),
        ))
        return  # One result per message


def _extract_block_text(block: ContentBlock) -> str:
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
    start = max(0, match_idx - context)
    end = min(len(text), match_idx + match_len + context)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet

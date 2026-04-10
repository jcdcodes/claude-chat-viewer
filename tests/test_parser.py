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
    assert "progress" not in msg_types
    assert "file-history-snapshot" not in msg_types


def test_parser_merges_assistant_streaming_messages(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    assistant_msgs = [m for m in session.messages if m.type == "assistant"]
    assert len(assistant_msgs) == 2
    first = assistant_msgs[0]
    block_types = [b.type for b in first.content]
    assert "thinking" in block_types
    assert "tool_use" in block_types


def test_parser_attaches_tool_results(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    assistant_msgs = [m for m in session.messages if m.type == "assistant"]
    first = assistant_msgs[0]
    block_types = [b.type for b in first.content]
    assert "tool_result" in block_types
    result_block = [b for b in first.content if b.type == "tool_result"][0]
    assert "def login" in result_block.content


def test_parser_excludes_tool_result_as_standalone(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
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
    projects = load_projects(projects_dir)
    assert projects[0].name == "-myproject"


def test_parser_sets_file_size(projects_dir: Path):
    projects = load_projects(projects_dir)
    session = projects[0].sessions[0]
    assert session.file_size > 0

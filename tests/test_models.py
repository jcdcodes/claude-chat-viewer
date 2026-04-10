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
    from datetime import timedelta
    # 8 messages, each 10 min apart (all within 15-min threshold)
    # Total active time: 7 * 10 = 70 min = ~1 hr 10 min
    base = datetime(2026, 4, 6, 18, 0, 0, tzinfo=timezone.utc)
    messages = []
    for i in range(8):
        ts = base + timedelta(minutes=i * 10)
        messages.append(
            Message(uuid=str(i), parent_uuid=str(i-1) if i else None,
                    type="user" if i % 2 == 0 else "assistant",
                    timestamp=ts, content=[], model=None)
        )
    session = Session(
        id="s", project="p", timestamp=messages[0].timestamp, title="t",
        git_branch=None, cwd="/", version="1", file_size=0,
        messages=messages, subagents={},
    )
    assert session.interaction_time_display == "~1 hr 10 min"


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

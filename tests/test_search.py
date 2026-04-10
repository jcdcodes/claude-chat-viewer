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

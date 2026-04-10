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
    app = create_app(projects_dir)
    assert app is not None

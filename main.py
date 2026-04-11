# main.py
from __future__ import annotations
from pathlib import Path
import markdown as md
from markupsafe import Markup
from flask import Flask, abort, render_template, request
from parser import load_projects, load_projects_merged
from search import search_sessions

LIVE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
DEFAULT_BACKUP_DIR = Path.home() / "Sync" / "air-claude-history-backup"


def create_app(projects_dir: Path | None = None) -> Flask:
    app = Flask(__name__)
    from search import highlight_snippet
    app.jinja_env.filters["highlight"] = lambda snippet, query: highlight_snippet(snippet, query)

    _md = md.Markdown(extensions=["fenced_code", "tables", "nl2br"])

    def render_markdown(text: str) -> Markup:
        _md.reset()
        return Markup(_md.convert(text))

    app.jinja_env.filters["markdown"] = render_markdown

    backup_dir = projects_dir if projects_dir is not None else DEFAULT_BACKUP_DIR
    # Load backup first, then overlay live data (live wins on duplicates)
    projects = load_projects_merged([backup_dir, LIVE_PROJECTS_DIR])

    session_lookup: dict[str, tuple] = {}
    for project in projects:
        for session in project.sessions:
            session_lookup[session.id] = (project, session)

    @app.route("/")
    def index():
        sorted_projects = sorted(projects, key=lambda p: p.latest_timestamp, reverse=True)
        return render_template("index.html", projects=sorted_projects, view="grouped")

    @app.route("/api/sessions")
    def api_sessions():
        view = request.args.get("view", "grouped")
        sorted_projects = sorted(projects, key=lambda p: p.latest_timestamp, reverse=True)
        if view == "flat":
            all_sessions = []
            for project in projects:
                for session in project.sessions:
                    all_sessions.append((project, session))
            all_sessions.sort(key=lambda ps: ps[1].timestamp, reverse=True)
            return render_template("partials/session_list.html", view="flat", flat_sessions=all_sessions)
        return render_template("partials/session_list.html", view="grouped", projects=sorted_projects)

    @app.route("/session/<session_id>")
    def session_view(session_id: str):
        entry = session_lookup.get(session_id)
        if not entry:
            abort(404)
        project, session = entry
        return render_template("session.html", session=session, project=project)

    @app.route("/api/subagent/<session_id>/<subagent_id>")
    def subagent_detail(session_id: str, subagent_id: str):
        entry = session_lookup.get(session_id)
        if not entry:
            abort(404)
        _, session = entry
        subagent = session.subagents.get(subagent_id)
        if not subagent:
            abort(404)
        return render_template("partials/subagent_detail.html", subagent=subagent)

    @app.route("/search")
    def search_view():
        query = request.args.get("q", "").strip()
        results = []
        if query:
            results = search_sessions(projects, query)
        return render_template("search_results.html", query=query, results=results)

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Claude transcript viewer")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Backup directory to overlay with live ~/.claude/projects/ data (default: ~/Sync/air-claude-history-backup/)",
    )
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    app = create_app(args.data_dir)
    app.run(host="127.0.0.1", port=args.port, debug=True)

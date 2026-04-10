# main.py
from __future__ import annotations
from pathlib import Path
from flask import Flask, abort, render_template, request
from parser import load_projects
from search import search_sessions

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def create_app(projects_dir: Path | None = None) -> Flask:
    if projects_dir is None:
        projects_dir = DEFAULT_PROJECTS_DIR

    app = Flask(__name__)
    projects = load_projects(projects_dir)

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
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)

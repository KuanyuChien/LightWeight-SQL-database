"""Lightweight HTTP server that serves the dashboard and executes SQL queries."""

from __future__ import annotations

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Add the project root to sys.path so we can import sql_db
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from sql_db.executor import DatabaseEngine


class DashboardHandler(SimpleHTTPRequestHandler):
    engine: DatabaseEngine = DatabaseEngine()

    def do_POST(self):
        if self.path == "/api/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.requestline and self.rfile.read(content_length)
            try:
                payload = json.loads(body)
                statements = payload.get("sql", "")
            except (json.JSONDecodeError, AttributeError):
                self._json_response(400, {"success": False, "error": "invalid JSON"})
                return

            if payload.get("reset"):
                DashboardHandler.engine = DatabaseEngine()

            # Execute each statement separated by semicolons
            rows: list[list[object]] = []
            columns: list[str] = []
            for raw_stmt in statements.split(";"):
                stmt = raw_stmt.strip()
                if not stmt:
                    continue
                result = DashboardHandler.engine.execute(stmt)
                if not result.success:
                    self._json_response(200, {"success": False, "error": result.error})
                    return
                if result.rows:
                    rows = [list(r) for r in result.rows]
                    columns = result.columns

            self._json_response(200, {"success": True, "rows": rows, "columns": columns})
        else:
            self._json_response(404, {"error": "not found"})

    def _json_response(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(dashboard_dir)
    server = HTTPServer(("", port), DashboardHandler)
    print(f"Dashboard running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()

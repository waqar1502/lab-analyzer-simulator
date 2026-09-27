from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..simulation.engine import SimulationEngine


class SimulatorHttpServer(ThreadingHTTPServer):
    daemon_threads = True


def create_server(engine: SimulationEngine, host: str, port: int) -> SimulatorHttpServer:
    static_root = Path(__file__).parent / "static"

    class Handler(BaseHTTPRequestHandler):
        server_version = "LabAnalyzerSimulator/0.1"

        def _json(self, status: int, payload: Any) -> None:
            data = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ValueError("request body is too large")
            raw = self.rfile.read(length) if length else b"{}"
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("JSON body must be an object")
            return value

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/healthz":
                self._json(200, {"status": "healthy"})
            elif path == "/readyz":
                self._json(200, {"status": "ready", "mode": engine.settings.mode})
            elif path == "/api/status":
                self._json(200, engine.status())
            elif path == "/api/messages":
                self._json(200, {"items": engine.messages_snapshot()})
            elif path == "/api/runs":
                self._json(200, {"items": engine.runs_snapshot()})
            elif path.startswith("/api/runs/"):
                run_id = path.removeprefix("/api/runs/")
                run = engine.run_snapshot(run_id)
                self._json(200 if run else 404, {"run": run} if run else {"error": "run_not_found"})
            elif path in {"/", "/index.html"}:
                self._static("index.html", "text/html; charset=utf-8")
            else:
                self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                body = self._body()
                if path == "/api/query":
                    worklist = engine.query(str(body.get("sample_identifier", "")), body.get("scenario_id"))
                    self._json(200, {"worklist": engine._worklist_dict(worklist), "status": engine.status()})
                elif path == "/api/run":
                    run = engine.start_run(
                        profile_id=str(body.get("profile_id", "cbc-normal")),
                        sample_identifier=body.get("sample_identifier"),
                        scenario_id=body.get("scenario_id"),
                    )
                    self._json(202, {"run": self._run_dict(run), "status": engine.status()})
                elif path == "/api/scenario":
                    scenario_id = engine.set_scenario(str(body.get("scenario_id", "normal")))
                    self._json(200, {"scenario_id": scenario_id, "status": engine.status()})
                elif path == "/api/protocol":
                    protocol_id = str(body.get("protocol", "hl7"))
                    engine.set_protocol(protocol_id)
                    self._json(200, engine.status())
                elif path == "/api/reset":
                    engine.reset()
                    self._json(200, engine.status())
                else:
                    self._json(404, {"error": "not_found"})
            except (ValueError, KeyError) as error:
                self._json(422, {"error": str(error), "status": engine.status()})
            except Exception as error:  # boundary protection for the UI/API
                self._json(500, {"error": str(error), "status": engine.status()})

        @staticmethod
        def _run_dict(run: Any) -> dict[str, Any]:
            return {field: getattr(run, field) for field in run.__slots__}

        def _static(self, name: str, content_type: str) -> None:
            path = static_root / name
            if not path.is_file():
                self._json(404, {"error": "not_found"})
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return SimulatorHttpServer((host, port), Handler)


def serve(engine: SimulationEngine, host: str, port: int) -> None:
    server = create_server(engine, host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

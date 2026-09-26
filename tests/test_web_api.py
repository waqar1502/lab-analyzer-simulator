import json
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lab_analyzer_simulator.domain import Settings
from lab_analyzer_simulator.simulation.engine import SimulationEngine
from lab_analyzer_simulator.web.server import create_server


ROOT = Path(__file__).parents[1]


class WebApiTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = SimulationEngine(ROOT, Settings(mode="fixture", random_seed=42))
        self.server = create_server(engine, "127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(1)

    def get(self, path: str) -> dict:
        with urlopen(self.base + path, timeout=2) as response:
            return json.loads(response.read())

    def post(self, path: str, body: dict) -> dict:
        request = Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=3) as response:
            return json.loads(response.read())

    def test_health_status_and_run(self) -> None:
        self.assertEqual("healthy", self.get("/healthz")["status"])
        self.assertEqual("fixture", self.get("/api/status")["mode"])
        result = self.post("/api/run", {"sample_identifier": "SAMPLE-CBC-001", "profile_id": "cbc-normal"})
        self.assertEqual("COMPLETED", result["run"]["state"])
        self.assertEqual(5, result["run"]["result_count"])


if __name__ == "__main__":
    unittest.main()

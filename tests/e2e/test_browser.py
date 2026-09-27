import threading
import unittest
from pathlib import Path

from lab_analyzer_simulator.domain import Settings
from lab_analyzer_simulator.simulation.engine import SimulationEngine
from lab_analyzer_simulator.web.server import create_server

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # The base test suite remains dependency-free.
    sync_playwright = None


ROOT = Path(__file__).parents[2]


@unittest.skipUnless(sync_playwright is not None, "install the e2e extra and Chromium to run browser tests")
class BrowserE2ETests(unittest.TestCase):
    def run_browser_flow(self, protocol: str, expected_wire_text: str) -> None:
        engine = SimulationEngine(ROOT, Settings(mode="fixture", protocol=protocol, random_seed=42))
        server = create_server(engine, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}")
                page.select_option("#sample", "SAMPLE-CBC-001")
                page.select_option("#profile", "cbc-normal")
                page.click("text=Scan and query worklist")
                page.wait_for_function("document.querySelector('#worklist').textContent.includes('ORDER-SYNTH-001')")
                page.click("text=Run selected profile")
                page.wait_for_function("document.querySelector('#worklist').textContent.includes('State: COMPLETED')", timeout=10000)
                self.assertIn(expected_wire_text, page.locator("#console").text_content() or "")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(1)

    def test_hl7_browser_flow(self) -> None:
        self.run_browser_flow("hl7", "ORU^R01")

    def test_astm_browser_flow(self) -> None:
        self.run_browser_flow("astm", "R|")

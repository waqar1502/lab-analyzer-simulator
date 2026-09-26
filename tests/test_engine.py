import unittest
from pathlib import Path

from lab_analyzer_simulator.domain import AnalyzerState, FailureState, Settings
from lab_analyzer_simulator.protocols.hl7 import Hl7ProtocolError
from lab_analyzer_simulator.simulation.engine import SimulationEngine


ROOT = Path(__file__).parents[1]


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SimulationEngine(ROOT, Settings(mode="fixture", random_seed=42))

    def test_fixture_run_completes_without_host(self) -> None:
        run = self.engine.run("cbc-normal", "SAMPLE-CBC-001")
        self.assertEqual(AnalyzerState.COMPLETED, run.state)
        self.assertEqual(5, run.result_count)
        self.assertEqual(AnalyzerState.COMPLETED, self.engine.state)
        self.assertIn("ORU^R01", self.engine.messages[-2]["message"])

    def test_unknown_sample_has_explicit_failure(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.query("NOT-IN-CATALOG")
        self.assertEqual(AnalyzerState.FAILED, self.engine.state)
        self.assertEqual(FailureState.UNKNOWN_SAMPLE, self.engine.failure)

    def test_duplicate_is_explicit_and_reuses_previous_control_id(self) -> None:
        first = self.engine.run("cbc-normal", "SAMPLE-CBC-001")
        second = self.engine.run("cbc-normal", "SAMPLE-CBC-001", "duplicate")
        self.assertEqual(first.message_control_id, second.message_control_id)

    def test_rejected_ack_is_an_explicit_result_failure(self) -> None:
        with self.assertRaises(Hl7ProtocolError):
            self.engine.run("cbc-normal", "SAMPLE-CBC-001", "nak")
        self.assertEqual(FailureState.RESULT_REJECTED, self.engine.failure)


if __name__ == "__main__":
    unittest.main()

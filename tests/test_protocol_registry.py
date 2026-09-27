import unittest
from pathlib import Path

from lab_analyzer_simulator.domain import Settings
from lab_analyzer_simulator.protocols import ProtocolFactory, ProtocolRegistry
from lab_analyzer_simulator.simulation.engine import SimulationEngine
from tests.support.astm_fake_host import AstmFakeHost


ROOT = Path(__file__).parents[1]


class ProtocolRegistryTests(unittest.TestCase):
    def test_registry_creates_both_protocols(self) -> None:
        registry = ProtocolRegistry()
        self.assertEqual({"astm", "hl7"}, set(registry.ids()))
        self.assertEqual("hl7", registry.create("hl7", Settings()).protocol_id)
        self.assertEqual("astm", ProtocolFactory(registry).create("astm", Settings(protocol="astm")).protocol_id)

    def test_engine_can_run_cbc_critical_with_astm_fixture_mode(self) -> None:
        engine = SimulationEngine(ROOT, Settings(protocol="astm", mode="fixture", random_seed=42))
        run = engine.run("cbc-critical", "SAMPLE-CBC-001")
        self.assertEqual("COMPLETED", run.state)
        self.assertEqual("astm", run.protocol)
        self.assertIn("R|", engine.messages[-2]["message"])

    def test_engine_astm_live_flow_uses_fake_host_over_tcp(self) -> None:
        worklist = "\r".join([
            "H|\\^&|HOST|LIS|2.0",
            "P|1|PATIENT-1|||Synthetic Patient",
            "O|1|ACCESSION-1|ORDER-1||WBC^White Blood Cell|R",
            "L|1|N", "",
        ])
        host = AstmFakeHost(worklist, expected_sessions=2)
        host.start()
        try:
            settings = Settings(protocol="astm", mode="live", gateway_host=host.host, gateway_port=host.port, connect_timeout_seconds=1, astm_receive_timeout_seconds=1, random_seed=42)
            engine = SimulationEngine(ROOT, settings)
            run = engine.run("cbc-normal", "SAMPLE-001")
        finally:
            host.close()
        self.assertIsNone(host.error)
        self.assertEqual("COMPLETED", run.state)
        self.assertEqual(1, len(host.received_queries))
        self.assertEqual(1, len(host.received_results))


if __name__ == "__main__":
    unittest.main()

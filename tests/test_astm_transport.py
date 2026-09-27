import unittest

from lab_analyzer_simulator.domain import Settings
from lab_analyzer_simulator.protocols.astm.protocol import AstmProtocol
from lab_analyzer_simulator.transports.astm.tcp import AstmTcpTransport
from tests.support.astm_fake_host import AstmFakeHost


class AstmTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(protocol="astm", astm_frame_size=24, astm_retry_count=2, astm_receive_timeout_seconds=1)
        self.protocol = AstmProtocol(self.settings)
        self.worklist = "\r".join([
            "H|\\^&|HOST|LIS|2.0",
            "P|1|PATIENT-1|||Synthetic Patient",
            "O|1|ACCESSION-1|ORDER-1||WBC^White Blood Cell\\HGB^Hemoglobin|R",
            "L|1|N", "",
        ])

    def transport_for(self, host: AstmFakeHost) -> AstmTcpTransport:
        return AstmTcpTransport(host.host, host.port, 1, 1, 24, 2, True)

    def test_query_and_result_use_real_astm_tcp_controls_and_frames(self) -> None:
        host = AstmFakeHost(self.worklist, expected_sessions=2)
        host.start()
        try:
            query = self.protocol.build_query("SAMPLE-001")
            response = self.transport_for(host).exchange(query, expect_response=True)
            self.assertIn("O|1|ACCESSION-1", response)
            worklist = self.protocol.parse_worklist(response, "SAMPLE-001")
            result, _ = self.protocol.build_result(worklist, [])
            self.transport_for(host).exchange(result, expect_response=False)
        finally:
            host.close()
        self.assertIsNone(host.error)
        self.assertEqual(1, len(host.received_queries))
        self.assertEqual(1, len(host.received_results))
        self.assertIn("RX ENQ", host.events)
        self.assertIn("RX EOT", host.events)

    def test_host_nak_causes_client_retry(self) -> None:
        host = AstmFakeHost(self.worklist, nak_first_frame=True)
        host.start()
        try:
            response = self.transport_for(host).exchange(self.protocol.build_query("SAMPLE-001"), expect_response=True)
        finally:
            host.close()
        self.assertIn("H|", response)
        self.assertIsNone(host.error)


if __name__ == "__main__":
    unittest.main()

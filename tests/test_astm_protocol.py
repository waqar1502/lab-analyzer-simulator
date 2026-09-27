import unittest

from lab_analyzer_simulator.domain import ResultValue, Settings, Worklist
from lab_analyzer_simulator.protocols.astm.protocol import AstmProtocol
from lab_analyzer_simulator.protocols.astm.records import parse_records


class AstmProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = AstmProtocol(Settings(protocol="astm"))

    def test_query_builds_h_q_l_records(self) -> None:
        message = self.protocol.build_query("SAMPLE-001")
        self.assertEqual(["H", "Q", "L"], [record.record_type for record in parse_records(message)])
        self.assertIn("SAMPLE-001", message)

    def test_worklist_parser_reads_h_p_o_l(self) -> None:
        message = "\r".join([
            "H|\\^&|HOST|LIS|2.0",
            "P|1|PATIENT-1|||Synthetic Patient",
            "O|1|ACCESSION-1|ORDER-1||WBC^White Blood Cell\\HGB^Hemoglobin|R",
            "L|1|N",
            "",
        ])
        worklist = self.protocol.parse_worklist(message, "SAMPLE-001")
        self.assertEqual("PATIENT-1", worklist.patient_id)
        self.assertEqual("ORDER-1", worklist.order_number)
        self.assertEqual(["WBC", "HGB"], [test.code for test in worklist.ordered_tests])

    def test_result_builds_h_p_o_multiple_r_l_records(self) -> None:
        worklist = Worklist.from_dict({"sample_identifier": "SAMPLE-001", "order_number": "ORDER-1", "accession_number": "ACC-1", "ordered_tests": [{"code": "WBC", "name": "WBC"}, {"code": "HGB", "name": "HGB"}]})
        message, control_id = self.protocol.build_result(worklist, [ResultValue("WBC", "WBC", "7.1"), ResultValue("HGB", "HGB", "14.2")])
        records = parse_records(message)
        self.assertEqual(["H", "P", "O", "R", "R", "L"], [record.record_type for record in records])
        self.assertTrue(control_id.startswith("ASTM-"))

    def test_acknowledgement_is_session_level(self) -> None:
        self.assertEqual(("AA", "ASTM-FRAME-ACK"), self.protocol.parse_acknowledgement(""))


if __name__ == "__main__":
    unittest.main()

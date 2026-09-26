import unittest
from pathlib import Path

from lab_analyzer_simulator.domain import ResultValue, Settings, Worklist
from lab_analyzer_simulator.protocols.hl7 import Hl7Protocol, Hl7ProtocolError


class Hl7ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = Hl7Protocol(Settings())

    def test_query_contains_sample_and_mllp_compatible_segments(self) -> None:
        message = self.protocol.query_message("SAMPLE-CBC-001", "QRY-TEST-001")
        self.assertTrue(message.startswith("MSH|"))
        self.assertIn("QRY^R02", message)
        self.assertIn("SAMPLE-CBC-001", message)
        self.assertTrue(message.endswith("\r"))

    def test_result_contains_one_obx_per_result_and_unique_default_id(self) -> None:
        worklist = Worklist.from_dict(
            {
                "sample_identifier": "SAMPLE-1",
                "ordered_tests": [{"code": "HGB", "name": "Hemoglobin"}],
            }
        )
        result, control_id = self.protocol.result_message(
            worklist, [ResultValue("HGB", "Hemoglobin", "14.2", "g/dL", "12-17")]
        )
        self.assertIn("ORU^R01", result)
        self.assertIn("OBX|1|NM|HGB^Hemoglobin", result)
        self.assertTrue(control_id.startswith("RES-"))

    def test_ack_parser_accepts_aa_and_rejects_missing_msa(self) -> None:
        ack = self.protocol.acknowledgement("RES-1")
        self.assertEqual(("AA", "RES-1"), self.protocol.parse_ack(ack))
        with self.assertRaises(Hl7ProtocolError):
            self.protocol.parse_ack("MSH|^~\\&|A|B|C|D|20260101000000||ACK^R01|1|P|2.5\r")

    def test_oru_worklist_parser_reads_patient_and_tests(self) -> None:
        response = "\r".join(
            [
                "MSH|^~\\&|HOST|LAB|SIM|SIM|20260101000000||DSR^Q03|1|P|2.5",
                "MSA|AA|QRY-1|Accepted",
                "PID|1||PAT-1||Synthetic^Patient",
                "ORC|RE|ORDER-1|ACCESSION-1||CM",
                "OBR|1|ORDER-1|ACCESSION-1|HGB^Hemoglobin|||20260101000000||||||||WHOLE_BLOOD_EDTA",
                "",
            ]
        )
        worklist = self.protocol.parse_worklist(response)
        self.assertEqual("PAT-1", worklist.patient_id)
        self.assertEqual("Synthetic Patient", worklist.patient_name)
        self.assertEqual("HGB", worklist.ordered_tests[0].code)

    def test_dsp_worklist_parser_reads_the_common_query_response_shape(self) -> None:
        response = "\r".join(
            [
                "MSH|^~\\&|HOST|LAB|SIM|SIM|20260101000000||DSR^Q03|1|P|2.5",
                "MSA|AA|QRY-1|Accepted",
                "DSP|1||ORDER-2",
                "DSP|2||SAMPLE-CBC-001",
                "DSP|3||ACCESSION-2",
                "DSP|4||Synthetic Patient",
                "DSP|5||PATIENT-2",
                "DSP|7||PANEL^CBC^WBC^White Blood Cell~PANEL^CBC^HGB^Hemoglobin",
                "",
            ]
        )
        worklist = self.protocol.parse_worklist(response)
        self.assertEqual("ORDER-2", worklist.order_number)
        self.assertEqual("SAMPLE-CBC-001", worklist.sample_identifier)
        self.assertEqual(["WBC", "HGB"], [test.code for test in worklist.ordered_tests])


if __name__ == "__main__":
    unittest.main()

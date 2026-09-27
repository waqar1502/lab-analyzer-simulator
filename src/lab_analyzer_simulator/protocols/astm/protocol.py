from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone

from ...domain import ResultValue, Worklist
from ..base import AnalyzerProtocol
from .records import AstmProtocolError, AstmRecord, parse_records, serialize_records


class AstmProtocol(AnalyzerProtocol):
    """Generic ASTM E1381/E1394-style record adapter for analyzer testing."""

    protocol_id = "astm"

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    @staticmethod
    def control_id(prefix: str = "ASTM") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    def build_query(self, sample_identifier: str, control_id: str | None = None) -> str:
        if not sample_identifier.strip():
            raise AstmProtocolError("sample_identifier is required")
        records = [
            AstmRecord("H", ("\\^&", "LAB_ANALYZER_SIMULATOR", "SIMULATOR", "2.0")),
            AstmRecord("Q", ("1", sample_identifier, "ALL", "")),
            AstmRecord("L", ("1", "N")),
        ]
        return serialize_records(records)

    def parse_worklist(self, message: str, requested_sample: str | None = None) -> Worklist:
        records = parse_records(message)
        if not any(record.record_type == "H" for record in records):
            raise AstmProtocolError("ASTM worklist has no H record")
        patient = next((record for record in records if record.record_type == "P"), None)
        order = next((record for record in records if record.record_type == "O"), None)
        if order is None:
            raise AstmProtocolError("ASTM worklist has no O record")
        order_fields = order.fields
        accession = order_fields[1] if len(order_fields) > 1 and order_fields[1] else "ASTM-ACCESSION"
        sample = requested_sample or accession
        patient_id = patient.fields[1] if patient and len(patient.fields) > 1 and patient.fields[1] else "SYNTHETIC-PATIENT"
        patient_name = patient.fields[4] if patient and len(patient.fields) > 4 and patient.fields[4] else "Synthetic Patient"
        test_field = order_fields[4] if len(order_fields) > 4 else "GENERIC^Generic analyzer test"
        tests = []
        for item in test_field.split("\\"):
            parts = item.split("^")
            code = parts[0] or (parts[1] if len(parts) > 1 else "GENERIC")
            name = parts[1] if len(parts) > 1 and parts[1] else code
            tests.append({"code": code, "name": name, "specimen": "SERUM"})
        return Worklist.from_dict(
            {
                "sample_identifier": sample,
                "order_number": order_fields[2] if len(order_fields) > 2 and order_fields[2] else accession,
                "accession_number": accession,
                "patient_id": patient_id,
                "patient_name": patient_name,
                "specimen": "SERUM",
                "ordered_tests": tests,
            }
        )

    def build_result(
        self,
        worklist: Worklist,
        results: Iterable[ResultValue],
        control_id: str | None = None,
    ) -> tuple[str, str]:
        control_id = control_id or self.control_id("ASTM")
        records = [
            AstmRecord("H", ("\\^&", "LAB_ANALYZER_SIMULATOR", "SIMULATOR", "2.0")),
            AstmRecord("P", ("1", worklist.patient_id, "", "", worklist.patient_name)),
            AstmRecord("O", ("1", worklist.accession_number, worklist.order_number, "", "\\".join(f"{test.code}^{test.name}" for test in worklist.ordered_tests), "R")),
        ]
        for index, result in enumerate(results, start=1):
            records.append(
                AstmRecord(
                    "R",
                    (
                        str(index),
                        f"{result.code}^{result.name}",
                        result.value,
                        result.units,
                        result.reference_range,
                        result.abnormal_flag,
                        result.result_status,
                    ),
                )
            )
        records.append(AstmRecord("L", ("1", "N")))
        return serialize_records(records), control_id

    def parse_acknowledgement(self, message: str) -> tuple[str, str]:
        if not message:
            return "AA", "ASTM-FRAME-ACK"
        records = parse_records(message)
        if not any(record.record_type == "L" for record in records):
            raise AstmProtocolError("ASTM acknowledgement response has no L record")
        return "AA", "ASTM-SESSION-ACK"

    def validate_message(self, message: str) -> None:
        records = parse_records(message)
        if records[0].record_type != "H" or records[-1].record_type != "L":
            raise AstmProtocolError("ASTM payload must start with H and end with L")

    def expects_response(self, operation: str) -> bool:
        return operation == "query"

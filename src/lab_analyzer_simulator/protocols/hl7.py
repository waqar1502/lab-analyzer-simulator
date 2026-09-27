from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone

from ..domain import ResultValue, Settings, Worklist
from .base import AnalyzerProtocol, AnalyzerProtocolError


class Hl7ProtocolError(AnalyzerProtocolError):
    pass


class Hl7Protocol(AnalyzerProtocol):
    """Minimal HL7 v2.5 implementation for analyzer query/result flows."""

    protocol_id = "hl7"

    start_block = "\x0b"
    end_block = "\x1c\x0d"

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    @staticmethod
    def control_id(prefix: str = "SIM") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:16]}"

    @staticmethod
    def _clean(value: object) -> str:
        return str(value).replace("|", " ").replace("\r", " ").replace("\n", " ")

    def _msh(self, message_type: str, control_id: str, profile: str | None = None) -> str:
        return "|".join(
            [
                "MSH",
                "^~\\&",
                self.settings.sender_application,
                self.settings.sender_facility,
                self.settings.receiver_application,
                self.settings.receiver_facility,
                self.timestamp(),
                "",
                message_type,
                control_id,
                "P",
                self.settings.hl7_version,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                profile or self.settings.protocol_profile,
            ]
        )

    def query_message(self, sample_identifier: str, control_id: str | None = None) -> str:
        control_id = control_id or self.control_id("QRY")
        if not sample_identifier.strip():
            raise Hl7ProtocolError("sample_identifier is required")
        qrd = "|".join(
            ["QRD", self.timestamp(), "R", "I", control_id, "", "RD", self._clean(sample_identifier), "", "", "RES"]
        )
        qrf = "QRF|SIMULATOR||||||"
        return "\r".join([self._msh("QRY^R02", control_id), qrd, qrf]) + "\r"

    def build_query(self, sample_identifier: str, control_id: str | None = None) -> str:
        return self.query_message(sample_identifier, control_id)

    def parse_segments(self, message: str) -> list[list[str]]:
        text = message.strip("\x0b\x1c\r\n")
        segments = []
        for line in re.split(r"\r\n|\r|\n", text):
            if line:
                fields = line.split("|")
                if fields[0] == "MSH":
                    fields.insert(1, "|")
                segments.append(fields)
        if not segments or segments[0][0] != "MSH":
            raise Hl7ProtocolError("message does not start with MSH")
        return segments

    def validate_message(self, message: str) -> None:
        self.parse_segments(message)

    @staticmethod
    def _field(segment: list[str], number: int, default: str = "") -> str:
        return segment[number] if number < len(segment) else default

    def parse_ack(self, message: str) -> tuple[str, str]:
        segments = self.parse_segments(message)
        msa = next((item for item in segments if item[0] == "MSA"), None)
        if not msa:
            raise Hl7ProtocolError("ACK does not contain MSA")
        return self._field(msa, 1), self._field(msa, 2)

    def parse_worklist(self, message: str, requested_sample: str | None = None) -> Worklist:
        segments = self.parse_segments(message)
        msa = next((item for item in segments if item[0] == "MSA"), None)
        if msa and self._field(msa, 1) not in {"AA", "CA"}:
            raise Hl7ProtocolError(f"host rejected query: {self._field(msa, 1)} {self._field(msa, 3)}")

        pid = next((item for item in segments if item[0] == "PID"), None)
        orc = next((item for item in segments if item[0] == "ORC"), None)
        obr_items = [item for item in segments if item[0] == "OBR"]
        sample = requested_sample or "UNKNOWN-SAMPLE"
        order = "SIMULATED-ORDER"
        accession = sample
        patient_id = "SYNTHETIC-PATIENT"
        patient_name = "Synthetic Patient"
        if pid:
            patient_id = self._field(pid, 3) or patient_id
            patient_name = self._field(pid, 5).replace("^", " ") or patient_name
        if orc:
            order = self._field(orc, 3) or order
        if obr_items:
            accession = self._field(obr_items[0], 3) or accession
            if not requested_sample:
                sample = accession
        tests = []
        for obr in obr_items:
            code_name = self._field(obr, 4)
            parts = code_name.split("^")
            tests.append(
                {
                    "code": parts[0] or "UNSPECIFIED",
                    "name": parts[1] if len(parts) > 1 else parts[0] or "Unspecified test",
                    "specimen": self._field(obr, 15) or "SERUM",
                }
            )
        dsp_values: dict[str, str] = {}
        for dsp in (item for item in segments if item[0] == "DSP"):
            key = self._field(dsp, 1)
            value = self._field(dsp, 3)
            if key:
                dsp_values[key] = value
        if dsp_values.get("1"):
            order = dsp_values["1"]
            sample = requested_sample or dsp_values.get("2") or sample
            accession = dsp_values.get("3") or sample
            patient_name = dsp_values.get("4") or patient_name
            patient_id = dsp_values.get("5") or patient_id
            encoded_tests = dsp_values.get("7", "")
            for encoded_test in encoded_tests.split("~"):
                parts = encoded_test.split("^")
                code = parts[2].strip() if len(parts) > 2 and parts[2].strip() else parts[0].strip()
                if code:
                    tests.append({"code": code, "name": parts[3].strip() if len(parts) > 3 and parts[3].strip() else code, "specimen": "SERUM"})
        if not tests:
            for dsp in (item for item in segments if item[0] == "DSP"):
                text = self._field(dsp, 3)
                match = re.search(r"([A-Z][A-Z0-9_-]{1,20})\^([^|]+)", text)
                if match:
                    tests.append({"code": match.group(1), "name": match.group(2), "specimen": "SERUM"})
        if not tests:
            tests = [{"code": "GENERIC", "name": "Generic analyzer test", "specimen": "SERUM"}]
        return Worklist.from_dict(
            {
                "sample_identifier": sample,
                "order_number": order,
                "accession_number": accession,
                "patient_id": patient_id,
                "patient_name": patient_name,
                "specimen": tests[0].get("specimen", "SERUM"),
                "ordered_tests": tests,
            }
        )

    def result_message(
        self,
        worklist: Worklist,
        results: Iterable[ResultValue],
        control_id: str | None = None,
    ) -> tuple[str, str]:
        control_id = control_id or self.control_id("RES")
        results = list(results)
        lines = [self._msh("ORU^R01", control_id, "lab.analyzer.result.v1")]
        lines.append(f"PID|1||{self._clean(worklist.patient_id)}||{self._clean(worklist.patient_name)}")
        lines.append(f"ORC|RE|{self._clean(worklist.order_number)}|{self._clean(worklist.accession_number)}||CM")
        lines.append(
            f"OBR|1|{self._clean(worklist.order_number)}|{self._clean(worklist.accession_number)}|"
            f"PANEL^{self._clean(worklist.specimen)}|||{self.timestamp()}||||||||{self._clean(worklist.specimen)}"
        )
        for index, result in enumerate(results, start=1):
            lines.append(
                "|".join(
                    [
                        "OBX",
                        str(index),
                        "NM",
                        f"{self._clean(result.code)}^{self._clean(result.name)}",
                        "",
                        self._clean(result.value),
                        self._clean(result.units),
                        self._clean(result.reference_range),
                        self._clean(result.abnormal_flag),
                        "",
                        "F",
                    ]
                )
            )
        return "\r".join(lines) + "\r", control_id

    def build_result(
        self,
        worklist: Worklist,
        results: Iterable[ResultValue],
        control_id: str | None = None,
    ) -> tuple[str, str]:
        return self.result_message(worklist, results, control_id)

    @staticmethod
    def acknowledgement(control_id: str, code: str = "AA", text: str = "Accepted") -> str:
        response_id = Hl7Protocol.control_id("ACK")
        return "\r".join(
            [
                f"MSH|^~\\&|LAB_HOST|SIMULATOR|LAB_ANALYZER_SIMULATOR|SIMULATOR|{Hl7Protocol.timestamp()}||ACK^R01|{response_id}|P|2.5",
                f"MSA|{code}|{control_id}|{text}",
            ]
        ) + "\r"

    def parse_acknowledgement(self, message: str) -> tuple[str, str]:
        return self.parse_ack(message)

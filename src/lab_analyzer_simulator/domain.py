from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AnalyzerState(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    IDLE = "IDLE"
    BARCODE_SCANNED = "BARCODE_SCANNED"
    QUERYING_HOST = "QUERYING_HOST"
    ORDER_RECEIVED = "ORDER_RECEIVED"
    READY = "READY"
    PROCESSING = "PROCESSING"
    RESULT_GENERATED = "RESULT_GENERATED"
    SENDING_RESULT = "SENDING_RESULT"
    WAITING_ACK = "WAITING_ACK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FailureState(StrEnum):
    HOST_UNAVAILABLE = "HOST_UNAVAILABLE"
    UNKNOWN_SAMPLE = "UNKNOWN_SAMPLE"
    QUERY_REJECTED = "QUERY_REJECTED"
    INVALID_ORDER = "INVALID_ORDER"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    TRANSMISSION_FAILED = "TRANSMISSION_FAILED"
    RESULT_REJECTED = "RESULT_REJECTED"
    TIMEOUT = "TIMEOUT"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"


@dataclass(slots=True, frozen=True)
class OrderedTest:
    code: str
    name: str
    specimen: str = "SERUM"
    unit: str = ""
    reference_range: str = ""
    value_type: str = "NM"


@dataclass(slots=True, frozen=True)
class Worklist:
    sample_identifier: str
    order_number: str
    accession_number: str
    patient_id: str
    patient_name: str
    specimen: str
    ordered_tests: tuple[OrderedTest, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Worklist:
        tests = tuple(
            OrderedTest(
                code=str(item["code"]),
                name=str(item.get("name", item["code"])),
                specimen=str(item.get("specimen", value.get("specimen", "SERUM"))),
                unit=str(item.get("unit", "")),
                reference_range=str(item.get("reference_range", "")),
                value_type=str(item.get("value_type", "NM")),
            )
            for item in value.get("ordered_tests", [])
        )
        return cls(
            sample_identifier=str(value["sample_identifier"]),
            order_number=str(value.get("order_number", value["sample_identifier"])),
            accession_number=str(value.get("accession_number", value["sample_identifier"])),
            patient_id=str(value.get("patient_id", "SYNTHETIC-PATIENT")),
            patient_name=str(value.get("patient_name", "Synthetic Patient")),
            specimen=str(value.get("specimen", "SERUM")),
            ordered_tests=tests,
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(slots=True, frozen=True)
class ResultValue:
    code: str
    name: str
    value: str
    units: str = ""
    reference_range: str = ""
    abnormal_flag: str = "N"
    result_status: str = "F"


@dataclass(slots=True)
class SimulationRun:
    run_id: str
    sample_identifier: str
    profile_id: str
    scenario_id: str
    state: str
    failure: str | None = None
    message_control_id: str | None = None
    result_count: int = 0
    progress: int = 0
    error: str | None = None
    created_at: str = ""
    completed_at: str | None = None


@dataclass(slots=True, frozen=True)
class ResultProfile:
    profile_id: str
    name: str
    analyzer_type: str
    tests: dict[str, dict[str, Any]]
    processing_seconds: float = 0.0
    processing_jitter_seconds: float = 0.0


@dataclass(slots=True, frozen=True)
class Settings:
    mode: str = "fixture"
    bind_host: str = "127.0.0.1"
    web_port: int = 8000
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 2575
    sender_application: str = "LAB_ANALYZER_SIMULATOR"
    sender_facility: str = "SIMULATOR"
    receiver_application: str = "LAB_HOST"
    receiver_facility: str = "LAB"
    hl7_version: str = "2.5"
    protocol_profile: str = "lab.analyzer.simulator.v1"
    connect_timeout_seconds: float = 3.0
    read_timeout_seconds: float = 5.0
    max_message_bytes: int = 1_000_000
    random_seed: int | None = 42


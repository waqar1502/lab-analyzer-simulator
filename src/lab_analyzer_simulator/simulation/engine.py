from __future__ import annotations

import threading
import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..catalog import Catalog
from ..domain import AnalyzerState, FailureState, Settings, SimulationRun, Worklist
from ..protocols import AnalyzerProtocol, AnalyzerProtocolError, ProtocolRegistry
from ..protocols.hl7 import Hl7ProtocolError
from ..transports import AnalyzerTransport, TransportError, TransportFault
from ..transports.astm.tcp import AstmTcpTransport
from ..transports.mllp import MllpTransport
from .generators import ResultGenerator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SimulationEngine:
    SCENARIOS = (
        "normal", "unknown-sample", "duplicate", "timeout", "delayed-ack", "malformed-mllp",
        "malformed-hl7", "no-ack", "nak", "reject-ack", "reset", "unavailable", "bad-id",
        "oversized", "unexpected-response", "invalid-encoding", "disconnect", "invalid-checksum",
        "wrong-frame-number", "missing-ack", "duplicate-frame", "corrupted-frame", "oversized-frame",
        "connection-reset-mid-frame", "connection-reset-between-frames", "missing-eot", "unexpected-eot",
        "enq-collision", "invalid-record-sequence",
    )

    def __init__(self, root: Path, settings: Settings):
        self.root = root
        self.settings = settings
        self.catalog = Catalog(root)
        self.registry = ProtocolRegistry()
        self.protocol: AnalyzerProtocol = self.registry.create(settings.protocol, settings)
        self.transport: AnalyzerTransport = self._create_transport(settings)
        self.generator = ResultGenerator(settings.random_seed)
        self.state = AnalyzerState.DISCONNECTED
        self.failure: FailureState | None = None
        self.progress = 0
        self.current_worklist: Worklist | None = None
        self.last_response = ""
        self.messages: list[dict[str, Any]] = []
        self.runs: list[SimulationRun] = []
        self.events: list[dict[str, Any]] = []
        self.active_scenario = "normal"
        self.active_result_profile: str | None = None
        self._lock = threading.RLock()

    def _create_transport(self, settings: Settings) -> AnalyzerTransport:
        if settings.protocol == "astm":
            return AstmTcpTransport(
                settings.gateway_host,
                settings.gateway_port,
                settings.connect_timeout_seconds,
                settings.astm_receive_timeout_seconds,
                settings.astm_frame_size,
                settings.astm_retry_count,
                settings.astm_checksum,
            )
        return MllpTransport(
            settings.gateway_host,
            settings.gateway_port,
            settings.connect_timeout_seconds,
            settings.read_timeout_seconds,
            settings.max_message_bytes,
        )

    def set_protocol(self, protocol_id: str) -> None:
        with self._lock:
            settings = replace(self.settings, protocol=protocol_id)
            self.protocol = self.registry.create(protocol_id, settings)
            self.settings = settings
            self.transport = self._create_transport(settings)
            self._transition(AnalyzerState.DISCONNECTED, detail=f"protocol selected: {protocol_id}")

    def set_scenario(self, scenario_id: str) -> str:
        if scenario_id not in self.SCENARIOS:
            raise ValueError(f"unknown scenario: {scenario_id}")
        with self._lock:
            self.active_scenario = scenario_id
        return scenario_id

    def _transition(self, state: AnalyzerState, failure: FailureState | None = None, detail: str = "") -> None:
        self.state = state
        self.failure = failure
        self.events.append({"timestamp": _now(), "state": state, "failure": failure, "detail": detail})

    def status(self) -> dict[str, Any]:
        with self._lock:
            active = self.runs[0] if self.runs else None
            return {
                "mode": self.settings.mode,
                "protocol": self.protocol.protocol_id,
                "activeProtocol": self.protocol.protocol_id,
                "activeAnalyzer": self.settings.analyzer_name,
                "activeScenario": self.active_scenario,
                "activeResultProfile": self.active_result_profile,
                "state": self.state,
                "analyzerState": self.state,
                "connectionState": "FIXTURE" if self.settings.mode == "fixture" else self.state,
                "failure": self.failure,
                "progress": self.progress,
                "sample_identifier": self.current_worklist.sample_identifier if self.current_worklist else None,
                "worklist": self._worklist_dict(self.current_worklist),
                "activeRun": self._run_dict(active),
                "events": self.events[-50:],
                "available_protocols": list(self.registry.ids()),
                "available_profiles": [
                    {"id": item.profile_id, "name": item.name, "analyzer_type": item.analyzer_type}
                    for item in self.catalog.profiles.values()
                ],
                "available_samples": list(self.catalog.worklists),
            }

    @staticmethod
    def _worklist_dict(worklist: Worklist | None) -> dict[str, Any] | None:
        if not worklist:
            return None
        return {
            "sample_identifier": worklist.sample_identifier,
            "order_number": worklist.order_number,
            "accession_number": worklist.accession_number,
            "patient_id": worklist.patient_id,
            "patient_name": worklist.patient_name,
            "specimen": worklist.specimen,
            "ordered_tests": [
                {"code": test.code, "name": test.name, "specimen": test.specimen, "unit": test.unit,
                 "reference_range": test.reference_range, "value_type": test.value_type}
                for test in worklist.ordered_tests
            ],
        }

    @staticmethod
    def _run_dict(run: SimulationRun | None) -> dict[str, Any] | None:
        return {field: getattr(run, field) for field in run.__slots__} if run else None

    def reset(self) -> None:
        with self._lock:
            self.state = AnalyzerState.IDLE
            self.failure = None
            self.progress = 0
            self.current_worklist = None
            self.last_response = ""
            self.events.clear()
            self._transition(AnalyzerState.IDLE, detail="simulator reset")

    def query(self, sample_identifier: str, scenario_id: str | None = None) -> Worklist:
        scenario_id = scenario_id or self.active_scenario
        self.set_scenario(scenario_id)
        with self._lock:
            if self.state == AnalyzerState.DISCONNECTED:
                self._transition(AnalyzerState.CONNECTED)
            if self.state in {AnalyzerState.CONNECTED, AnalyzerState.COMPLETED, AnalyzerState.FAILED}:
                self._transition(AnalyzerState.IDLE)
            self._transition(AnalyzerState.BARCODE_SCANNED, detail=sample_identifier)
            if scenario_id == "unknown-sample":
                self._transition(AnalyzerState.FAILED, FailureState.UNKNOWN_SAMPLE, "scenario requested unknown sample")
                raise ValueError("unknown sample")
            if self.settings.mode == "fixture":
                worklist = self.catalog.get_worklist(sample_identifier)
                if not worklist:
                    self._transition(AnalyzerState.FAILED, FailureState.UNKNOWN_SAMPLE, "sample is not in fixture catalog")
                    raise ValueError(f"unknown sample: {sample_identifier}")
                self.current_worklist = worklist
                self._transition(AnalyzerState.ORDER_RECEIVED, detail="fixture worklist loaded")
                self._transition(AnalyzerState.READY)
                return worklist
            self._transition(AnalyzerState.QUERYING_HOST)
            message = self.protocol.build_query(sample_identifier, self.protocol.control_id("QRY"))
            self.protocol.validate_message(message)
            self.messages.append({"protocol": self.protocol.protocol_id, "direction": "outbound", "kind": "query", "message": message, "timestamp": _now()})
        try:
            response = self.transport.exchange(message, self._fault(scenario_id), self.protocol.expects_response("query"))
            with self._lock:
                self.last_response = response
                self.messages.append({"protocol": self.protocol.protocol_id, "direction": "inbound", "kind": "worklist", "message": response, "timestamp": _now()})
            worklist = self.protocol.parse_worklist(response, sample_identifier)
        except TransportError as error:
            with self._lock:
                self._transition(AnalyzerState.FAILED, FailureState.TIMEOUT if "timed out" in str(error).lower() else FailureState.HOST_UNAVAILABLE, str(error))
            raise
        except (AnalyzerProtocolError, ValueError) as error:
            with self._lock:
                self._transition(AnalyzerState.FAILED, FailureState.QUERY_REJECTED, str(error))
            raise
        with self._lock:
            self.current_worklist = worklist
            self._transition(AnalyzerState.ORDER_RECEIVED)
            self._transition(AnalyzerState.READY)
            return worklist

    def _prepare_run(self, profile_id: str, sample_identifier: str | None, scenario_id: str | None) -> tuple[SimulationRun, Any, Worklist]:
        profile = self.catalog.get_profile(profile_id)
        scenario_id = scenario_id or self.active_scenario
        if sample_identifier or not self.current_worklist:
            self.query(sample_identifier or next(iter(self.catalog.worklists)), scenario_id)
        with self._lock:
            assert self.current_worklist is not None
            run = SimulationRun(str(uuid.uuid4()), self.current_worklist.sample_identifier, profile_id, scenario_id, AnalyzerState.READY, created_at=_now(), protocol=self.protocol.protocol_id)
            self.runs.insert(0, run)
            self.active_scenario = scenario_id
            self.active_result_profile = profile_id
            self.progress = 0
            return run, profile, self.current_worklist

    def run(self, profile_id: str, sample_identifier: str | None = None, scenario_id: str | None = None) -> SimulationRun:
        run, profile, worklist = self._prepare_run(profile_id, sample_identifier, scenario_id)
        error = self._execute_run(run, profile, worklist)
        if error:
            raise error
        return run

    def start_run(self, profile_id: str, sample_identifier: str | None = None, scenario_id: str | None = None) -> SimulationRun:
        run, profile, worklist = self._prepare_run(profile_id, sample_identifier, scenario_id)
        threading.Thread(target=self._execute_run, args=(run, profile, worklist), daemon=True, name=f"sim-run-{run.run_id[:8]}").start()
        return run

    def _execute_run(self, run: SimulationRun, profile: Any, worklist: Worklist) -> Exception | None:
        started = time.monotonic()
        try:
            with self._lock:
                self._transition(AnalyzerState.PROCESSING)
            duration = max(0.0, profile.processing_seconds)
            if profile.processing_jitter_seconds:
                duration += self.generator.random.uniform(0, profile.processing_jitter_seconds)
            steps = max(1, int(duration / 0.1)) if duration else 1
            for step in range(steps):
                if duration:
                    time.sleep(duration / steps)
                with self._lock:
                    self.progress = int((step + 1) * 100 / steps)
                    run.progress = self.progress
                    run.elapsed_seconds = time.monotonic() - started
                    if worklist.ordered_tests:
                        run.current_test = worklist.ordered_tests[min(len(worklist.ordered_tests) - 1, int((step + 1) * len(worklist.ordered_tests) / steps))].code
            results = self.generator.generate_all(worklist.ordered_tests, profile)
            with self._lock:
                self._transition(AnalyzerState.RESULT_GENERATED)
            result_message, control_id = self.protocol.build_result(worklist, results, self._result_control_id(run.scenario_id))
            self.protocol.validate_message(result_message)
            with self._lock:
                run.message_control_id = control_id
                run.result_count = len(results)
                self.messages.append({"protocol": self.protocol.protocol_id, "direction": "outbound", "kind": "result", "message": result_message, "timestamp": _now()})
            if self.settings.mode == "live":
                with self._lock:
                    self._transition(AnalyzerState.SENDING_RESULT)
                    self._transition(AnalyzerState.WAITING_ACK)
                response = self.transport.exchange(result_message, self._fault(run.scenario_id), self.protocol.expects_response("result"))
                with self._lock:
                    self.last_response = response
                    self.messages.append({"protocol": self.protocol.protocol_id, "direction": "inbound", "kind": "ack", "message": response, "timestamp": _now()})
                ack_code, _ = self.protocol.parse_acknowledgement(response)
                if ack_code not in {"AA", "CA"}:
                    raise AnalyzerProtocolError(f"result rejected with ACK code {ack_code}")
            else:
                ack_code = "AR" if run.scenario_id in {"reject-ack", "nak", "unexpected-response"} else "AA"
                response = "" if self.protocol.protocol_id == "astm" else self.protocol.acknowledgement(control_id, ack_code, "Rejected by scenario" if ack_code == "AR" else "Accepted")
                with self._lock:
                    self.last_response = response
                    self.messages.append({"protocol": self.protocol.protocol_id, "direction": "inbound", "kind": "ack", "message": response, "timestamp": _now()})
                parsed_ack, _ = self.protocol.parse_acknowledgement(response)
                if ack_code not in {"AA", "CA"} or parsed_ack not in {"AA", "CA"}:
                    error_type = Hl7ProtocolError if self.protocol.protocol_id == "hl7" else AnalyzerProtocolError
                    raise error_type(f"result rejected with ACK code {ack_code}")
            with self._lock:
                self.progress = 100
                run.progress = 100
                run.current_test = None
                run.state = AnalyzerState.COMPLETED
                run.completed_at = _now()
                self._transition(AnalyzerState.COMPLETED)
            return None
        except Exception as error:
            with self._lock:
                run.state = AnalyzerState.FAILED
                run.failure = self._failure_for(error, run)
                run.error = str(error)
                self._transition(AnalyzerState.FAILED, run.failure, str(error))
            return error
        finally:
            with self._lock:
                run.elapsed_seconds = time.monotonic() - started

    @staticmethod
    def _failure_for(error: Exception, run: SimulationRun) -> FailureState:
        text = str(error).lower()
        if "timed out" in text or "timeout" in text:
            return FailureState.TIMEOUT
        if isinstance(error, TransportError):
            return FailureState.TRANSMISSION_FAILED
        if "rejected" in text or "ack code" in text:
            return FailureState.RESULT_REJECTED
        if isinstance(error, AnalyzerProtocolError):
            return FailureState.PROTOCOL_ERROR
        return FailureState.PROCESSING_FAILED

    def _result_control_id(self, scenario_id: str) -> str | None:
        if scenario_id == "bad-id":
            return "INVALID CONTROL ID"
        if scenario_id == "duplicate":
            with self._lock:
                previous = next((run for run in self.runs[1:] if run.message_control_id), None)
                return previous.message_control_id if previous else None
        return None

    @staticmethod
    def _fault(scenario_id: str) -> TransportFault:
        mapping = {
            "timeout": "timeout", "delayed-ack": "delayed-ack", "malformed-mllp": "malformed-mllp",
            "malformed-hl7": "malformed-hl7", "invalid-encoding": "invalid-encoding", "disconnect": "disconnect",
            "reset": "connection-reset-between-frames", "no-ack": "no-ack", "unavailable": "unavailable",
            "oversized": "oversized", "invalid-checksum": "invalid-checksum", "wrong-frame-number": "wrong-frame-number",
            "missing-ack": "missing-ack", "duplicate-frame": "duplicate-frame", "corrupted-frame": "corrupted-frame",
            "oversized-frame": "oversized-frame", "connection-reset-mid-frame": "connection-reset-mid-frame",
            "connection-reset-between-frames": "connection-reset-between-frames", "missing-eot": "missing-eot",
            "unexpected-eot": "unexpected-eot", "enq-collision": "enq-collision", "invalid-record-sequence": "invalid-record-sequence",
        }
        return TransportFault(mapping.get(scenario_id, "normal"), 1.0 if scenario_id == "delayed-ack" else 0.0)

    def messages_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self.messages[-100:])

    def runs_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._run_dict(run) for run in self.runs[:100]]

    def run_snapshot(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._run_dict(next((run for run in self.runs if run.run_id == run_id), None))

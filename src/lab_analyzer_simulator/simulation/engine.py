from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..catalog import Catalog
from ..domain import AnalyzerState, FailureState, Settings, SimulationRun, Worklist
from ..protocols.hl7 import Hl7Protocol, Hl7ProtocolError
from ..transports.mllp import MllpError, MllpTransport, TransportFault
from .generators import ResultGenerator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SimulationEngine:
    def __init__(self, root: Path, settings: Settings):
        self.root = root
        self.settings = settings
        self.catalog = Catalog(root)
        self.protocol = Hl7Protocol(settings)
        self.transport = MllpTransport(
            settings.gateway_host,
            settings.gateway_port,
            settings.connect_timeout_seconds,
            settings.read_timeout_seconds,
            settings.max_message_bytes,
        )
        self.generator = ResultGenerator(settings.random_seed)
        self.state = AnalyzerState.DISCONNECTED
        self.failure: FailureState | None = None
        self.progress = 0
        self.current_worklist: Worklist | None = None
        self.last_response = ""
        self.messages: list[dict[str, Any]] = []
        self.runs: list[SimulationRun] = []
        self.events: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def _transition(self, state: AnalyzerState, failure: FailureState | None = None, detail: str = "") -> None:
        self.state = state
        self.failure = failure
        self.events.append({"timestamp": _now(), "state": state, "failure": failure, "detail": detail})

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "mode": self.settings.mode,
                "state": self.state,
                "failure": self.failure,
                "progress": self.progress,
                "sample_identifier": self.current_worklist.sample_identifier if self.current_worklist else None,
                "worklist": self._worklist_dict(self.current_worklist),
                "events": self.events[-50:],
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
            "ordered_tests": [test.__dict__ if hasattr(test, "__dict__") else {"code": test.code, "name": test.name} for test in worklist.ordered_tests],
        }

    def reset(self) -> None:
        with self._lock:
            self.state = AnalyzerState.IDLE
            self.failure = None
            self.progress = 0
            self.current_worklist = None
            self.last_response = ""
            self.events.clear()
            self._transition(AnalyzerState.IDLE, detail="simulator reset")

    def query(self, sample_identifier: str, scenario_id: str = "normal") -> Worklist:
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
            control_id = self.protocol.control_id("QRY")
            message = self.protocol.query_message(sample_identifier, control_id)
            self.messages.append({"direction": "outbound", "kind": "query", "message": message, "timestamp": _now()})
            try:
                response = self.transport.send(message, self._fault(scenario_id))
                self.last_response = response
                self.messages.append({"direction": "inbound", "kind": "worklist", "message": response, "timestamp": _now()})
                worklist = self.protocol.parse_worklist(response, sample_identifier)
            except MllpError as error:
                failure = FailureState.TIMEOUT if "timed out" in str(error).lower() else FailureState.HOST_UNAVAILABLE
                self._transition(AnalyzerState.FAILED, failure, str(error))
                raise
            except Hl7ProtocolError as error:
                self._transition(AnalyzerState.FAILED, FailureState.QUERY_REJECTED, str(error))
                raise
            self.current_worklist = worklist
            self._transition(AnalyzerState.ORDER_RECEIVED)
            self._transition(AnalyzerState.READY)
            return worklist

    def run(self, profile_id: str, sample_identifier: str | None = None, scenario_id: str = "normal") -> SimulationRun:
        with self._lock:
            profile = self.catalog.get_profile(profile_id)
            if sample_identifier or not self.current_worklist:
                self.query(sample_identifier or next(iter(self.catalog.worklists)), scenario_id)
            assert self.current_worklist is not None
            worklist = self.current_worklist
            run = SimulationRun(
                run_id=str(uuid.uuid4()),
                sample_identifier=worklist.sample_identifier,
                profile_id=profile_id,
                scenario_id=scenario_id,
                state=AnalyzerState.READY,
                created_at=_now(),
            )
            self.runs.insert(0, run)
            self._transition(AnalyzerState.PROCESSING)
            duration = max(0.0, profile.processing_seconds)
            if profile.processing_jitter_seconds:
                duration += self.generator.random.uniform(0, profile.processing_jitter_seconds)
            steps = max(1, int(duration / 0.1)) if duration else 1
            for step in range(steps):
                if duration:
                    time.sleep(duration / steps)
                self.progress = int((step + 1) * 100 / steps)
                run.progress = self.progress
            try:
                results = [self.generator.generate(test, profile) for test in worklist.ordered_tests]
            except Exception as error:  # generation is the processing boundary
                run.state = AnalyzerState.FAILED
                run.failure = FailureState.PROCESSING_FAILED
                run.error = str(error)
                self._transition(AnalyzerState.FAILED, FailureState.PROCESSING_FAILED, str(error))
                raise
            self._transition(AnalyzerState.RESULT_GENERATED)
            control_id = self._result_control_id(scenario_id)
            result_message, control_id = self.protocol.result_message(worklist, results, control_id)
            run.message_control_id = control_id
            run.result_count = len(results)
            self.messages.append({"direction": "outbound", "kind": "result", "message": result_message, "timestamp": _now()})
            if self.settings.mode == "live":
                self._transition(AnalyzerState.SENDING_RESULT)
                try:
                    self._transition(AnalyzerState.WAITING_ACK)
                    response = self.transport.send(result_message, self._fault(scenario_id))
                    self.last_response = response
                    self.messages.append({"direction": "inbound", "kind": "ack", "message": response, "timestamp": _now()})
                    ack_code, _ = self.protocol.parse_ack(response)
                    if ack_code not in {"AA", "CA"}:
                        raise Hl7ProtocolError(f"result rejected with ACK code {ack_code}")
                except MllpError as error:
                    run.state = AnalyzerState.FAILED
                    run.failure = FailureState.TIMEOUT if "timed out" in str(error).lower() else FailureState.TRANSMISSION_FAILED
                    run.error = str(error)
                    self._transition(AnalyzerState.FAILED, run.failure, str(error))
                    raise
                except Hl7ProtocolError as error:
                    run.state = AnalyzerState.FAILED
                    run.failure = FailureState.RESULT_REJECTED
                    run.error = str(error)
                    self._transition(AnalyzerState.FAILED, FailureState.RESULT_REJECTED, str(error))
                    raise
            else:
                ack_code = "AR" if scenario_id in {"reject-ack", "nak", "unexpected-response"} else "AA"
                self.last_response = self.protocol.acknowledgement(control_id, ack_code, "Rejected by scenario" if ack_code == "AR" else "Accepted")
                self.messages.append({"direction": "inbound", "kind": "ack", "message": self.last_response, "timestamp": _now()})
                if ack_code not in {"AA", "CA"}:
                    run.state = AnalyzerState.FAILED
                    run.failure = FailureState.RESULT_REJECTED
                    run.error = f"result rejected with ACK code {ack_code}"
                    self._transition(AnalyzerState.FAILED, FailureState.RESULT_REJECTED, run.error)
                    raise Hl7ProtocolError(run.error)
            self.progress = 100
            run.progress = 100
            run.state = AnalyzerState.COMPLETED
            run.completed_at = _now()
            self._transition(AnalyzerState.COMPLETED)
            return run

    def _result_control_id(self, scenario_id: str) -> str | None:
        if scenario_id == "bad-id":
            return "INVALID CONTROL ID"
        if scenario_id == "duplicate":
            previous = next((run for run in self.runs[1:] if run.message_control_id), None)
            if previous:
                return previous.message_control_id
        return None

    @staticmethod
    def _fault(scenario_id: str) -> TransportFault:
        if scenario_id == "timeout":
            return TransportFault("timeout")
        if scenario_id == "delayed-ack":
            return TransportFault("normal", 1.0)
        if scenario_id == "malformed-mllp":
            return TransportFault("malformed-mllp")
        if scenario_id == "malformed-hl7":
            return TransportFault("malformed-hl7")
        if scenario_id == "invalid-encoding":
            return TransportFault("invalid-encoding")
        if scenario_id in {"disconnect", "reset"}:
            return TransportFault("disconnect")
        if scenario_id == "no-ack":
            return TransportFault("no-ack")
        if scenario_id == "unavailable":
            return TransportFault("unavailable")
        if scenario_id == "oversized":
            return TransportFault("oversized")
        return TransportFault()

    def messages_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self.messages[-100:])

    def runs_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [run.__dict__ if hasattr(run, "__dict__") else {field: getattr(run, field) for field in run.__slots__} for run in self.runs[:100]]

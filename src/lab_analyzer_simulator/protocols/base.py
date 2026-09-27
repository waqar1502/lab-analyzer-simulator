from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from ..domain import ResultValue, Settings, Worklist


class AnalyzerProtocolError(ValueError):
    """A protocol message is syntactically invalid or rejected."""


class AnalyzerProtocol(ABC):
    """Protocol contract shared by analyzer implementations.

    A protocol produces/consumes protocol payloads; transport/session classes
    are responsible for bytes, sockets, framing, retries, and acknowledgements.
    """

    protocol_id: str

    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def build_query(self, sample_identifier: str, control_id: str | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse_worklist(self, message: str, requested_sample: str | None = None) -> Worklist:
        raise NotImplementedError

    @abstractmethod
    def build_result(
        self,
        worklist: Worklist,
        results: Iterable[ResultValue],
        control_id: str | None = None,
    ) -> tuple[str, str]:
        raise NotImplementedError

    @abstractmethod
    def parse_acknowledgement(self, message: str) -> tuple[str, str]:
        raise NotImplementedError

    @abstractmethod
    def validate_message(self, message: str) -> None:
        raise NotImplementedError

    def expects_response(self, operation: str) -> bool:
        return operation in {"query", "result"}

    def control_id(self, prefix: str = "SIM") -> str:
        raise NotImplementedError

    # Compatibility names retained for existing clients of the v0.1 HL7 API.
    def query_message(self, sample_identifier: str, control_id: str | None = None) -> str:
        return self.build_query(sample_identifier, control_id)

    def result_message(
        self,
        worklist: Worklist,
        results: Iterable[ResultValue],
        control_id: str | None = None,
    ) -> tuple[str, str]:
        return self.build_result(worklist, results, control_id)

    def parse_ack(self, message: str) -> tuple[str, str]:
        return self.parse_acknowledgement(message)

    def acknowledgement(self, control_id: str, code: str = "AA", text: str = "Accepted") -> str:
        raise AnalyzerProtocolError(f"{self.protocol_id} does not use a message-level acknowledgement")

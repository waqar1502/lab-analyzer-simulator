from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class TransportError(ConnectionError):
    pass


@dataclass(slots=True, frozen=True)
class TransportFault:
    kind: str = "normal"
    delay_seconds: float = 0.0


class AnalyzerTransport(ABC):
    @abstractmethod
    def exchange(
        self,
        message: str,
        fault: TransportFault | None = None,
        expect_response: bool = True,
    ) -> str:
        raise NotImplementedError

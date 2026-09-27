from __future__ import annotations

from collections.abc import Callable

from ..domain import Settings
from .base import AnalyzerProtocol
from .hl7 import Hl7Protocol

ProtocolCreator = Callable[[Settings], AnalyzerProtocol]


class ProtocolRegistry:
    """Registry/factory for protocol adapters selected by configuration."""

    def __init__(self) -> None:
        self._factories: dict[str, ProtocolCreator] = {}
        self.register("hl7", Hl7Protocol)
        from .astm.protocol import AstmProtocol

        self.register("astm", AstmProtocol)

    def register(self, protocol_id: str, factory: ProtocolCreator) -> None:
        self._factories[protocol_id.lower()] = factory

    def create(self, protocol_id: str, settings: Settings) -> AnalyzerProtocol:
        try:
            return self._factories[protocol_id.lower()](settings)
        except KeyError as error:
            raise ValueError(f"Unsupported analyzer protocol: {protocol_id}") from error

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


class ProtocolFactory:
    """Small façade for callers that prefer a factory over direct registry access."""

    def __init__(self, registry: ProtocolRegistry | None = None):
        self.registry = registry or ProtocolRegistry()

    def create(self, protocol_id: str, settings: Settings) -> AnalyzerProtocol:
        return self.registry.create(protocol_id, settings)

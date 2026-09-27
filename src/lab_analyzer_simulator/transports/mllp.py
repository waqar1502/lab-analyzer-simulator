from __future__ import annotations

import socket
import time
from ..protocols.hl7 import Hl7Protocol
from .base import AnalyzerTransport, TransportError, TransportFault


class MllpError(TransportError):
    pass


class MllpTransport(AnalyzerTransport):
    def __init__(self, host: str, port: int, connect_timeout: float, read_timeout: float, max_bytes: int):
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_bytes = max_bytes

    def exchange(
        self,
        message: str,
        fault: TransportFault | None = None,
        expect_response: bool = True,
    ) -> str:
        fault = fault or TransportFault()
        if fault.kind == "unavailable":
            raise MllpError("simulated host unavailable")
        payload = message
        if fault.kind == "invalid-encoding":
            payload = message.replace("|", "¦")
        elif fault.kind == "malformed-hl7":
            payload = "THIS IS NOT AN HL7 MESSAGE"
        elif fault.kind == "oversized":
            payload = message + ("X" * (self.max_bytes + 1))
        frame = Hl7Protocol.start_block + payload + Hl7Protocol.end_block
        if fault.kind == "malformed-mllp":
            frame = payload
        try:
            with socket.create_connection((self.host, self.port), timeout=self.connect_timeout) as connection:
                connection.settimeout(self.read_timeout)
                connection.sendall(frame.encode("utf-8"))
                if not expect_response:
                    return ""
                if fault.kind == "disconnect":
                    return ""
                if fault.kind == "no-ack":
                    return ""
                if fault.delay_seconds:
                    time.sleep(fault.delay_seconds)
                if fault.kind == "timeout":
                    time.sleep(self.read_timeout + 0.1)
                    raise MllpError("MLLP response timed out")
                return self._receive(connection)
        except (OSError, TimeoutError) as error:
            raise MllpError(f"MLLP connection failed to {self.host}:{self.port}: {error}") from error

    def _receive(self, connection: socket.socket) -> str:
        data = bytearray()
        while len(data) <= self.max_bytes:
            try:
                chunk = connection.recv(min(8192, self.max_bytes - len(data) + 1))
            except socket.timeout as error:
                raise MllpError("MLLP response timed out") from error
            if not chunk:
                break
            data.extend(chunk)
            if data.endswith(Hl7Protocol.end_block.encode("ascii")):
                break
        if len(data) > self.max_bytes:
            raise MllpError("MLLP response exceeded max_message_bytes")
        if not data:
            return ""
        if not data.startswith(Hl7Protocol.start_block.encode("ascii")) or not data.endswith(
            Hl7Protocol.end_block.encode("ascii")
        ):
            raise MllpError("response did not use valid MLLP framing")
        return data[1:-2].decode("utf-8")

    def send(self, message: str, fault: TransportFault | None = None) -> str:
        return self.exchange(message, fault, expect_response=True)

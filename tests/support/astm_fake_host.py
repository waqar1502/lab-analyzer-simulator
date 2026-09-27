from __future__ import annotations

import socket
import threading

from lab_analyzer_simulator.protocols.astm.records import parse_records
from lab_analyzer_simulator.transports.astm.framing import (
    ACK,
    ENQ,
    EOT,
    NAK,
    STX,
    AstmFrame,
    AstmFrameError,
)


class AstmFakeHost:
    """In-process ASTM LIS host used only by automated wire-level tests."""

    def __init__(self, worklist: str, expected_sessions: int = 1, nak_first_frame: bool = False):
        self.worklist = worklist
        self.expected_sessions = expected_sessions
        self.nak_first_frame = nak_first_frame
        self.received_queries: list[str] = []
        self.received_results: list[str] = []
        self.events: list[str] = []
        self.error: Exception | None = None
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(5)
        self.host = "127.0.0.1"
        self.port = self._server.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        try:
            self._server.close()
        finally:
            self._thread.join(2)

    def _serve(self) -> None:
        try:
            for _ in range(self.expected_sessions):
                connection, _ = self._server.accept()
                with connection:
                    connection.settimeout(3)
                    payload = self._receive_session(connection)
                    if any(record.record_type == "Q" for record in parse_records(payload)):
                        self.received_queries.append(payload)
                        self._send_session(connection, self.worklist)
                    else:
                        self.received_results.append(payload)
                        connection.sendall(EOT)
        except Exception as error:
            self.error = error

    def _receive_session(self, connection: socket.socket) -> str:
        if self._read_control(connection) != ENQ:
            raise ValueError("fake host expected ENQ")
        self.events.append("RX ENQ")
        connection.sendall(ACK)
        payload = bytearray()
        expected = 1
        first_frame = True
        while True:
            control = self._read_control(connection)
            if control == EOT:
                self.events.append("RX EOT")
                return payload.decode("ascii")
            if control != STX:
                raise ValueError(f"unexpected control byte {control!r}")
            encoded = self._read_frame_after_stx(connection)
            try:
                frame = AstmFrame.decode(STX + encoded)
            except AstmFrameError:
                connection.sendall(NAK)
                continue
            if frame.number != expected:
                if frame.number == (expected - 1) % 8:
                    connection.sendall(ACK)
                    continue
                connection.sendall(NAK)
                continue
            if self.nak_first_frame and first_frame:
                first_frame = False
                connection.sendall(NAK)
                continue
            first_frame = False
            payload.extend(frame.payload)
            expected = (expected + 1) % 8
            connection.sendall(ACK)

    def _send_session(self, connection: socket.socket, payload: str) -> None:
        connection.sendall(ENQ)
        if self._read_control(connection) != ACK:
            raise ValueError("fake host expected ACK for response ENQ")
        encoded = payload.encode("ascii")
        frame_size = 80
        chunks = [encoded[index : index + frame_size] for index in range(0, len(encoded), frame_size)] or [b""]
        for index, chunk in enumerate(chunks):
            frame = AstmFrame((index + 1) % 8, chunk, index == len(chunks) - 1).encode()
            connection.sendall(frame)
            if self._read_control(connection) != ACK:
                raise ValueError("fake host expected ACK for response frame")
        connection.sendall(EOT)

    @staticmethod
    def _read_control(connection: socket.socket) -> bytes:
        value = connection.recv(1)
        if not value:
            raise ConnectionError("fake host connection closed")
        return value

    @staticmethod
    def _read_frame_after_stx(connection: socket.socket) -> bytes:
        data = bytearray()
        while True:
            value = connection.recv(1)
            if not value:
                raise ConnectionError("fake host connection closed in frame")
            data.extend(value)
            if data.endswith(b"\r\n"):
                return bytes(data)

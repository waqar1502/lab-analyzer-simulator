from __future__ import annotations

import socket
import time

from ...transports.base import AnalyzerTransport, TransportError, TransportFault
from .framing import ACK, ENQ, EOT, NAK, STX, AstmFrame, AstmFrameError


class AstmTcpError(TransportError):
    pass


class AstmTcpTransport(AnalyzerTransport):
    """ASTM TCP session transport with ENQ/ACK, framed retries, and EOT."""

    def __init__(self, host: str, port: int, connect_timeout: float, read_timeout: float, frame_size: int, retry_count: int, checksum: bool):
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.frame_size = max(16, frame_size)
        self.retry_count = max(0, retry_count)
        self.checksum = checksum

    def exchange(self, message: str, fault: TransportFault | None = None, expect_response: bool = True) -> str:
        fault = fault or TransportFault()
        if fault.kind == "unavailable":
            raise AstmTcpError("simulated ASTM host unavailable")
        try:
            with self._connect() as connection:
                connection.settimeout(self.read_timeout)
                self._send_control(connection, ENQ)
                if fault.kind == "enq-collision":
                    self._send_control(connection, ENQ)
                self._expect_control(connection, ACK, fault, phase="ENQ")
                if fault.kind == "unexpected-eot":
                    self._send_control(connection, EOT)
                    raise AstmTcpError("unexpected EOT injected before ASTM frames")
                if fault.kind == "invalid-record-sequence":
                    message = message.replace("H|", "R|", 1)
                self._send_frames(connection, message, fault)
                if fault.kind == "missing-eot":
                    if expect_response:
                        return self._receive_message(connection, fault)
                    return ""
                if fault.kind == "disconnect":
                    raise AstmTcpError("ASTM connection reset after frame transmission")
                self._send_control(connection, EOT)
                if not expect_response:
                    return self._try_read_response(connection, fault)
                return self._receive_message(connection, fault)
        except AstmTcpError:
            raise
        except (OSError, TimeoutError) as error:
            raise AstmTcpError(f"ASTM connection failed to {self.host}:{self.port}: {error}") from error

    def _connect(self) -> socket.socket:
        try:
            return socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        except OSError as error:
            raise AstmTcpError(f"ASTM connection failed to {self.host}:{self.port}: {error}") from error

    @staticmethod
    def _send_control(connection: socket.socket, control: bytes) -> None:
        connection.sendall(control)

    def _read_control(self, connection: socket.socket) -> bytes:
        try:
            value = connection.recv(1)
        except socket.timeout as error:
            raise AstmTcpError("ASTM control response timed out") from error
        if not value:
            raise AstmTcpError("ASTM host closed the connection")
        return value

    def _expect_control(self, connection: socket.socket, expected: bytes, fault: TransportFault, phase: str) -> None:
        if fault.kind in {"missing-ack", "no-ack"} and phase == "ENQ":
            raise AstmTcpError("ASTM ENQ acknowledgement was intentionally omitted")
        if fault.delay_seconds:
            time.sleep(fault.delay_seconds)
        received = self._read_control(connection)
        if received != expected:
            raise AstmTcpError(f"ASTM expected {expected!r} during {phase}, received {received!r}")

    def _send_frames(self, connection: socket.socket, message: str, fault: TransportFault) -> None:
        payload = message.encode("ascii")
        chunks = [payload[index : index + self.frame_size] for index in range(0, len(payload), self.frame_size)] or [b""]
        for index, chunk in enumerate(chunks):
            number = (index + 1) % 8
            final = index == len(chunks) - 1
            frame = AstmFrame(number, chunk, final)
            encoded = frame.encode(self.checksum)
            if index == 0 and fault.kind == "invalid-checksum":
                encoded = encoded[:-4] + (b"00" if encoded[-4:-2] != b"00" else b"FF") + encoded[-2:]
            elif index == 0 and fault.kind == "wrong-frame-number":
                encoded = AstmFrame((number + 1) % 8, chunk, final).encode(self.checksum)
            elif index == 0 and fault.kind == "corrupted-frame":
                encoded = encoded[:3] + b"X" + encoded[4:]
            elif index == 0 and fault.kind == "oversized-frame":
                encoded = AstmFrame(number, chunk + b"X" * (self.frame_size + 1), final).encode(self.checksum)
            self._send_frame_with_retry(connection, encoded, number, fault)

    def _send_frame_with_retry(self, connection: socket.socket, encoded: bytes, number: int, fault: TransportFault) -> None:
        attempts = 0
        while True:
            if fault.kind == "connection-reset-mid-frame" and number == 1 and attempts == 0:
                connection.sendall(encoded[: max(1, len(encoded) // 2)])
                raise AstmTcpError("connection reset mid ASTM frame")
            connection.sendall(encoded)
            if fault.kind == "duplicate-frame" and attempts == 0:
                connection.sendall(encoded)
            if fault.kind == "connection-reset-between-frames" and number == 2:
                raise AstmTcpError("connection reset between ASTM frames")
            response = self._read_control(connection)
            if response == ACK:
                return
            if response != NAK:
                raise AstmTcpError(f"ASTM expected ACK/NAK, received {response!r}")
            attempts += 1
            if attempts > self.retry_count:
                raise AstmTcpError(f"ASTM frame {number} exceeded retry count")

    def _receive_message(self, connection: socket.socket, fault: TransportFault) -> str:
        first = self._read_control(connection)
        if first == EOT:
            return ""
        if first != ENQ:
            if first == STX:
                raise AstmTcpError("unexpected ASTM frame before ENQ")
            raise AstmTcpError(f"unexpected ASTM response control {first!r}")
        self._send_control(connection, ACK)
        return self._receive_frames(connection, fault)

    def _try_read_response(self, connection: socket.socket, fault: TransportFault) -> str:
        try:
            return self._receive_message(connection, fault)
        except AstmTcpError as error:
            if fault.kind not in {"timeout", "missing-eot"} and ("timed out" in str(error).lower() or "closed" in str(error).lower()):
                return ""
            raise

    def _receive_frames(self, connection: socket.socket, fault: TransportFault) -> str:
        payload = bytearray()
        expected_number = 1
        retries = 0
        while True:
            first = self._read_control(connection)
            if first == EOT:
                return bytes(payload).decode("ascii")
            if first != STX:
                if first == ENQ:
                    self._send_control(connection, ACK)
                    continue
                raise AstmTcpError(f"unexpected ASTM response byte {first!r}")
            frame_bytes = self._read_frame_after_stx(connection)
            try:
                frame = AstmFrame.decode(STX + frame_bytes, self.checksum)
                if frame.number != expected_number:
                    if frame.number == (expected_number - 1) % 8:
                        self._send_control(connection, ACK)
                        continue
                    self._send_control(connection, NAK)
                    retries += 1
                    if retries > self.retry_count:
                        raise AstmTcpError(f"unexpected ASTM frame number {frame.number}, expected {expected_number}")
                    continue
                payload.extend(frame.payload)
                self._send_control(connection, ACK)
                expected_number = (expected_number + 1) % 8
                retries = 0
                if fault.kind == "missing-eot" and frame.final:
                    time.sleep(self.read_timeout + 0.05)
                if frame.final:
                    continue
            except AstmFrameError as error:
                self._send_control(connection, NAK)
                retries += 1
                if retries > self.retry_count:
                    raise AstmTcpError(str(error)) from error

    def _read_frame_after_stx(self, connection: socket.socket) -> bytes:
        data = bytearray()
        while True:
            try:
                byte = connection.recv(1)
            except socket.timeout as error:
                raise AstmTcpError("ASTM frame timed out") from error
            if not byte:
                raise AstmTcpError("connection closed mid ASTM frame")
            data.extend(byte)
            if data.endswith(b"\r\n"):
                return bytes(data)

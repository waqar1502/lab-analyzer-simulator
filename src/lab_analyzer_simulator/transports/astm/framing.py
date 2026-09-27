from __future__ import annotations

from dataclasses import dataclass

from ...protocols.astm.checksum import calculate_checksum

ENQ = b"\x05"
ACK = b"\x06"
NAK = b"\x15"
STX = b"\x02"
ETX = b"\x03"
ETB = b"\x17"
EOT = b"\x04"
CRLF = b"\x0d\x0a"


class AstmFrameError(ValueError):
    pass


@dataclass(slots=True, frozen=True)
class AstmFrame:
    number: int
    payload: bytes
    final: bool

    def encode(self, checksum: bool = True) -> bytes:
        if not 0 <= self.number <= 7:
            raise AstmFrameError("ASTM frame number must be between 0 and 7")
        terminator = ETX if self.final else ETB
        content = str(self.number).encode("ascii") + self.payload + terminator
        check = calculate_checksum(content).encode("ascii") if checksum else b"00"
        return STX + content + check + CRLF

    @classmethod
    def decode(cls, frame: bytes, checksum: bool = True) -> AstmFrame:
        if not frame.startswith(STX) or not frame.endswith(CRLF):
            raise AstmFrameError("ASTM frame must use STX and CRLF")
        body = frame[1:-2]
        if len(body) < 4:
            raise AstmFrameError("ASTM frame is too short")
        try:
            number = int(chr(body[0]))
        except ValueError as error:
            raise AstmFrameError("ASTM frame number is invalid") from error
        terminator_index = max(body.rfind(ETX), body.rfind(ETB))
        if terminator_index < 2 or len(body) < terminator_index + 3:
            raise AstmFrameError("ASTM frame terminator/checksum is missing")
        terminator = body[terminator_index : terminator_index + 1]
        received = body[terminator_index + 1 : terminator_index + 3].decode("ascii", errors="replace").upper()
        content = body[: terminator_index + 1]
        expected = calculate_checksum(content)
        if checksum and received != expected:
            raise AstmFrameError(f"ASTM checksum mismatch: received {received}, expected {expected}")
        return cls(number, content[1:-1], terminator == ETX)

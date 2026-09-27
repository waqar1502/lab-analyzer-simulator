from __future__ import annotations

from dataclasses import dataclass


class AstmProtocolError(ValueError):
    pass


@dataclass(slots=True, frozen=True)
class AstmRecord:
    record_type: str
    fields: tuple[str, ...]

    def __str__(self) -> str:
        return "|".join((self.record_type, *self.fields))

    @classmethod
    def parse(cls, line: str) -> AstmRecord:
        clean = line.rstrip("\r\n")
        if not clean or "|" not in clean:
            raise AstmProtocolError(f"invalid ASTM record: {line!r}")
        record_type, *fields = clean.split("|")
        if record_type not in {"H", "P", "O", "Q", "R", "C", "L"}:
            raise AstmProtocolError(f"unsupported ASTM record type: {record_type}")
        return cls(record_type, tuple(fields))


def parse_records(message: str) -> list[AstmRecord]:
    records = [AstmRecord.parse(line) for line in message.replace("\r\n", "\r").split("\r") if line]
    if not records:
        raise AstmProtocolError("ASTM payload contains no records")
    return records


def serialize_records(records: list[AstmRecord] | tuple[AstmRecord, ...]) -> str:
    if not records:
        raise AstmProtocolError("cannot serialize an empty ASTM record list")
    return "\r".join(str(record) for record in records) + "\r"

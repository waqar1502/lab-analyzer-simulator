# Scenarios and fault injection

Fault scenarios are selected in the browser or supplied as `scenario_id` in the REST body.

- `normal`: complete fixture or live exchange.
- `unknown-sample`: reject a barcode that has no fixture/host worklist.
- `duplicate`: intentionally reuse a result control ID after a successful run.
- `timeout`: wait past the MLLP read timeout.
- `delayed-ack`: delay before reading the host response.
- `malformed-mllp`: omit MLLP framing.
- `invalid-encoding`: alter a delimiter before transport.
- `disconnect`: close after sending without consuming a response.
- `no-ack`: simulate a host that closes without acknowledging.
- `nak` / `reject-ack`: return an application rejection ACK.
- `malformed-hl7`: send a non-HL7 payload.
- `reset`: simulate a host-side connection reset.
- `unavailable`: fail before opening a host connection.
- `bad-id`: reserve a scenario name for invalid control-ID compatibility tests.
- `oversized`: send a payload beyond the configured transport limit.
- `unexpected-response`: return an application rejection for an unexpected response test.

ASTM-only wire scenarios include `invalid-checksum`, `wrong-frame-number`, `missing-ack`, `duplicate-frame`, `corrupted-frame`, `oversized-frame`, `connection-reset-mid-frame`, `connection-reset-between-frames`, `missing-eot`, `unexpected-eot`, `enq-collision`, and `invalid-record-sequence`. They alter ASTM controls, frame bytes, checksums, or session termination.

Use the state and failure fields in `/api/status` to assert application behavior. A scenario is not complete until the test asserts both the failure state and the resulting wire behavior.

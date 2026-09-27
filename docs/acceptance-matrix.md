# Acceptance matrix — v0.2.0

This matrix separates automated standalone proof from real-host verification. A real-host row is `BLOCKED` when no approved compatible endpoint is available; it is not converted to `PASS` by the fake host tests.

| Feature | Status | Automated | Real Host |
|---|---|---|---|
| Protocol abstraction/registry/factory | PASS | Yes | N/A |
| HL7 v2 | PASS | Yes | BLOCKED until approved endpoint run |
| MLLP | PASS | Yes | BLOCKED until approved endpoint run |
| QRY^R02 | PASS | Yes | BLOCKED until approved endpoint run |
| DSR^Q03/DSP parsing | PASS | Yes | BLOCKED until approved endpoint run |
| ORU^R01 | PASS | Yes | BLOCKED until approved endpoint run |
| ASTM parser/builder | PASS | Yes | BLOCKED until approved endpoint run |
| ASTM host query | PASS | Yes, fake host | BLOCKED unless endpoint supports ASTM |
| ASTM result transmission | PASS | Yes, fake host | BLOCKED unless endpoint supports ASTM |
| ENQ/ACK/NAK/EOT | PASS | Yes, TCP fake host | BLOCKED unless endpoint supports ASTM |
| ASTM checksum | PASS | Yes | BLOCKED until approved endpoint run |
| ASTM multi-frame ETB/ETX | PASS | Yes | BLOCKED until approved endpoint run |
| ASTM retry/timeout | PASS | Yes | BLOCKED until approved endpoint run |
| CBC normal | PASS | Yes | N/A |
| CBC abnormal | PASS | Yes | N/A |
| CBC critical | PASS | Yes | N/A |
| Extended discipline fixtures | PASS | Yes | N/A |
| Derived generator | PASS | Yes | N/A |
| Custom registered generator | PASS | Yes | N/A |
| Fault injection | PASS for tested standalone wire cases | Yes | N/A |
| Live asynchronous progress | PASS | Yes, REST polling | N/A |
| Scenario persistence | PASS | Yes, REST status | N/A |
| Browser E2E | PASS when CI E2E dependencies are installed | CI | N/A |
| Docker HL7 | PASS | Image/Compose smoke | N/A |
| Docker ASTM | PASS | Same image/configuration | N/A |
| Camera barcode/QR | PARTIAL | Optional browser API/manual fallback | N/A |
| GHCR publication | CONFIGURED | Release workflow | Not published by this local change |

## Real-host status

No real host endpoint was changed or contacted during standalone implementation. Existing gateway compatibility requires an approved test endpoint and a separate execution window. If the existing gateway has no ASTM listener, the correct result is:

```text
ASTM REAL-HOST E2E:
BLOCKED — EXISTING GATEWAY DOES NOT PROVIDE ASTM HOST ENDPOINT
```

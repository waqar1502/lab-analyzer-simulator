# Lab Analyzer Simulator

Lab Analyzer Simulator is a standalone, open-source test instrument for laboratory integrations. It models a generic analyzer that scans a specimen identifier, obtains a worklist, generates synthetic results, and exchanges HL7 v2/MLLP or ASTM/TCP messages.

It is designed for local development, integration testing, demonstrations, and protocol troubleshooting. It does not create laboratory orders, connect to a database, require a hospital application, or contain real patient information.

## Features in v0.2.0

- Browser control panel and REST API.
- CLI/headless operation for automation.
- Fixture mode for deterministic local tests without a host system.
- Live mode for sending HL7/MLLP queries and results to a configured host.
- HL7 v2.5 `QRY^R02`, `DSR^Q03`, `ORU^R01`, and ACK message support.
- ASTM/LIS2-style `H`, `P`, `O`, `Q`, `R`, `C`, and `L` record support over ASTM TCP.
- ASTM ENQ/ACK/NAK/EOT sessions, STX/ETX/ETB framing, frame numbers, checksums, retries, and multi-frame messages.
- A protocol registry/factory so the simulation engine is independent of HL7 and ASTM details.
- Explicit analyzer state machine with failure states.
- Generic profiles for hematology/CBC, chemistry, coagulation, immunoassay, urinalysis, and blood gas.
- Fixed, range, choice, percentage, and seedable random result generators.
- Processing delay and progress reporting.
- Fault scenarios for unknown samples, duplicate control IDs, malformed MLLP, timeout, delayed response, invalid encoding, disconnect, and rejected acknowledgements.
- ASTM wire-fault scenarios including invalid checksum, wrong frame, duplicate frame, reset, missing EOT, contention, and invalid record sequence.
- Docker and Docker Compose packaging.
- Synthetic fixtures and automated unit, contract, transport, and API tests.

ASTM support is generic and protocol-oriented. It is not a claim of compatibility with a particular analyzer vendor or model.

The project was initiated with acknowledgement to **Mian Waqar Ali** for the original integration-testing problem and practical direction that motivated this generic simulator. The implementation is intended to remain useful beyond any one product or customer.

## Quick start

Requires Python 3.12+.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m lab_analyzer_simulator --root . validate
python -m lab_analyzer_simulator --root . web
```

Open <http://127.0.0.1:8000>. Select a synthetic sample, choose a result profile, and run it. The protocol console shows the generated ORU message and fixture ACK.

The same workflow can be run headlessly:

```bash
python -m lab_analyzer_simulator --root . run --sample SAMPLE-CBC-001 --profile cbc-normal
python -m lab_analyzer_simulator --root . run --sample SAMPLE-CHEM-001 --profile chemistry-normal
python -m lab_analyzer_simulator --root . query SAMPLE-CBC-001
```

## Docker

```bash
docker compose up --build
```

Then open <http://127.0.0.1:8000>. The image runs as a non-root user and binds to localhost in the Compose example. To test a host system from a container, set `LAB_SIM_MODE=live`, `LAB_SIM_GATEWAY_HOST`, and `LAB_SIM_GATEWAY_PORT` in a local Compose override; do not commit credentials or customer addresses.

## Protocols and modes

The same fixture/result model can run through either protocol:

```text
SIMULATOR_PROTOCOL=hl7   # HL7 v2 over MLLP
SIMULATOR_PROTOCOL=astm  # ASTM records over ASTM TCP
```

### Fixture mode

Fixture mode is the default. The simulator looks up the scanned sample in `fixtures/worklists/`, loads the synthetic worklist, generates results, and records the HL7 conversation in memory. It returns a synthetic `AA` ACK after generating the result. No host or database is required.

### Live mode

Live mode sends a `QRY^R02` request to the configured MLLP host. It parses the `DSR^Q03` response, generates results for the returned tests, sends `ORU^R01`, and validates the returned ACK. Configure it with environment variables:

```text
LAB_SIM_MODE=live
LAB_SIM_GATEWAY_HOST=127.0.0.1
LAB_SIM_GATEWAY_PORT=2575
LAB_SIM_SENDER_APPLICATION=LAB_ANALYZER_SIMULATOR
LAB_SIM_SENDER_FACILITY=SIMULATOR
LAB_SIM_RECEIVER_APPLICATION=LAB_HOST
LAB_SIM_RECEIVER_FACILITY=LAB
```

The simulator uses MLLP framing: vertical-tab (`0x0B`) before the HL7 payload and file-separator/carriage-return (`0x1C 0x0D`) after it. The implementation treats a missing or malformed frame as a protocol/transport failure.

For ASTM mode, the simulator performs an ENQ/ACK session, sends numbered STX frames terminated by ETB or ETX with a two-character checksum and CR/LF, waits for ACK or NAK, sends EOT, and receives the host response session for queries. See [ASTM protocol details](docs/astm.md).

## REST API

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness check |
| GET | `/readyz` | Readiness and configured mode |
| GET | `/api/status` | State, failure, progress, profiles, fixtures, events |
| GET | `/api/messages` | Recent inbound/outbound HL7 messages |
| GET | `/api/runs` | Recent simulation runs |
| GET | `/api/runs/{runId}` | Live state and progress for one run |
| POST | `/api/query` | Body: `{"sample_identifier":"SAMPLE-CBC-001","scenario_id":"normal"}` |
| POST | `/api/run` | Body: `{"sample_identifier":"SAMPLE-CBC-001","profile_id":"cbc-normal","scenario_id":"normal"}` |
| POST | `/api/scenario` | Validate/select a scenario for client workflows |
| POST | `/api/protocol` | Select `hl7` or `astm` |
| POST | `/api/reset` | Reset analyzer state and in-memory history |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/run \
  -H 'content-type: application/json' \
  -d '{"sample_identifier":"SAMPLE-CBC-001","profile_id":"cbc-normal"}'
```

## Scenarios

Scenarios are test behavior, not clinical interpretations:

| Scenario | Purpose |
|---|---|
| `normal` | Complete query/process/result/ACK flow |
| `unknown-sample` | Barcode not found in fixture catalog or rejected query |
| `duplicate` | Reuse the previous result control ID intentionally |
| `timeout` | Exercise response timeout handling in live mode |
| `delayed-ack` | Add transport delay before reading the response |
| `malformed-mllp` | Send a message without MLLP framing |
| `invalid-encoding` | Replace a delimiter with an invalid protocol character |
| `disconnect` | Close after sending without consuming a response |

Normal runs generate unique message-control IDs. Duplicate IDs are only produced by the explicit `duplicate` scenario.

## Extending profiles and fixtures

Add a worklist JSON file under `fixtures/worklists/`. Add result generators under `profiles/results/`. A result profile maps test codes to a generator:

```json
{
  "id": "example-profile",
  "name": "Example profile",
  "analyzer_type": "chemistry",
  "tests": {
    "GLU": {"type": "range", "min": 70, "max": 99, "decimals": 0, "units": "mg/dL"},
    "FLAG": {"type": "choice", "values": ["NEGATIVE", "POSITIVE"]},
    "RATIO": {"type": "percentage", "min": 0, "max": 100, "decimals": 1}
  }
}
```

All public fixtures must be synthetic. Do not add real names, medical record numbers, accession numbers, tenant/facility identifiers, credentials, or production endpoints.

The catalog includes CBC normal/abnormal/critical, hematology differential/ESR, chemistry renal/liver/electrolyte/lipid, coagulation, immunoassay, urinalysis, and blood-gas examples.

## Development and verification

```bash
python -m unittest discover -s tests -v
python -m lab_analyzer_simulator --root . validate
docker compose config
docker build -t lab-analyzer-simulator:local .
```

The compatibility test against a real host is intentionally separate from the default tests. Run it only in an isolated environment with an approved test endpoint; see `docs/compatibility.md`. The automated ASTM fake-host integration test is part of the standard suite.

## Project boundaries and safety

This is a simulator, not a medical device and not a laboratory information system. It must not be connected to production, used with PHI, or used to make clinical decisions. The default server binds to `127.0.0.1`; change the bind address only in a controlled test network.

## License

Apache License 2.0. See [LICENSE](LICENSE). It is permissive and includes an express patent grant, which is appropriate for a reusable protocol-testing project intended for community contributions.

# Quickstart

## Local fixture flow

1. Start the server with `python -m lab_analyzer_simulator --root . web`.
2. Open `http://127.0.0.1:8000`.
3. Select `SAMPLE-CBC-001` and `CBC - normal range`.
4. Select `Scan and query worklist`.
5. Select `Run selected profile`.
6. Inspect the generated `ORU^R01` and synthetic ACK in the protocol console.

This is the recommended first test because it needs no external host. The simulator does not create or look up orders in a database; the worklist is the checked-in synthetic fixture.

## Live host flow

Start the simulator with `LAB_SIM_MODE=live` and a test-only MLLP endpoint. Scan an identifier that the host recognizes. The sequence is:

```text
barcode -> QRY^R02 -> DSR^Q03 worklist -> processing -> ORU^R01 -> ACK
```

The host must accept the simulator's configured sender/receiver values and return valid MLLP framing. Use the message console and `/api/messages` to troubleshoot each exchange.

## ASTM fixture flow

Start with `SIMULATOR_PROTOCOL=astm` or choose `ASTM / TCP` in the browser. In fixture mode the same synthetic worklist and result profile produce `H`, `P`, `O`, `R`, and `L` records. The console displays the ASTM payload; the automated fake-host tests exercise the actual ENQ/ACK/frame/EOT session.

## CLI flow

```bash
python -m lab_analyzer_simulator --root . validate
python -m lab_analyzer_simulator --root . query SAMPLE-CHEM-001
python -m lab_analyzer_simulator --root . run --sample SAMPLE-CHEM-001 --profile chemistry-normal
```

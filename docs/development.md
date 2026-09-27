# Development guide

The runtime is split into four layers:

- `domain.py`: state, worklist, result, and settings models.
- `protocols/`: protocol-neutral contract, HL7 parsing/building, and ASTM records.
- `transports/`: MLLP framing plus ASTM TCP session/framing behavior.
- `simulation/`: generators and analyzer state machine.
- `web/` and `cli.py`: user-facing adapters over the engine.

Keep the engine usable without the web server. Add unit tests for protocol and generator behavior, contract tests for all profile/fixture JSON, wire-level integration tests for MLLP and ASTM TCP, and browser E2E tests for both protocol selections.

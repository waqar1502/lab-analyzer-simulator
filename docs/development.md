# Development guide

The runtime is split into four layers:

- `domain.py`: state, worklist, result, and settings models.
- `protocols/`: HL7 message parsing/building. Future ASTM work belongs here.
- `transports/`: MLLP/TCP framing and socket behavior.
- `simulation/`: generators and analyzer state machine.
- `web/` and `cli.py`: user-facing adapters over the engine.

Keep the engine usable without the web server. Add unit tests for protocol and generator behavior, contract tests for all profile/fixture JSON, and integration tests for local TCP framing.

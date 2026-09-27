# Changelog

## 0.2.1 - 2026-09-27

- Fix HL7 query and result messages so the configured protocol profile is emitted in MSH-21.
- Add regression coverage for the HL7 profile field position.

## 0.2.0 - 2026-09-27

- Initial standalone project.
- HL7 v2.5 over MLLP query, result, and ACK flow.
- ASTM record adapter and real ASTM TCP session/framing implementation.
- Protocol registry/factory, asynchronous run polling, persisted scenario selection, and optional browser camera scanning.
- CBC critical and extended multi-discipline profiles.
- ASTM fake-host wire-level tests and optional browser E2E tests.
- Fixture and live modes.
- Generic analyzer profiles and synthetic worklists.
- Browser UI, REST API, CLI, fault scenarios, Docker packaging, and tests.

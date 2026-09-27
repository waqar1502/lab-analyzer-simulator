# Standalone Lab Analyzer Simulator

This repository is intentionally independent from any application-specific implementation.

## Scope

- Keep the simulator generic and safe for public use.
- Do not add real patient data, tenant identifiers, credentials, database dependencies, or customer-specific defaults.
- Keep protocol, transport, simulation, and web/CLI layers separated.
- Preserve HL7/MLLP interoperability and document any wire-format change.

## Development

- Runtime: Python 3.12 or newer.
- Prefer the standard library for the runtime so the Docker image remains small and easy to audit.
- Run `python -m unittest discover -s tests -v` before submitting a change.
- Run `python -m lab_analyzer_simulator validate` to validate all profiles and fixtures.
- Run `docker compose config` and `docker build -t lab-analyzer-simulator:local .` when changing packaging.
- Never commit generated results, credentials, PHI, or local configuration overrides.

## Public-project rules

- The primary product name is **Lab Analyzer Simulator**.
- Customer-specific integrations belong under `examples/integrations/` and must use placeholders.
- ASTM is supported only through the documented generic profile and tested ASTM session adapter; never claim vendor/device compatibility without verified testing.

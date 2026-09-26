# Contributing

1. Keep the simulator generic. Do not commit customer names, tenant/facility identifiers, credentials, real patient data, or production addresses.
2. Keep protocol implementations independent from transports and the web UI.
3. Add or update a contract test for every new message type or profile format.
4. Run `python -m unittest discover -s tests -v` and `python -m lab_analyzer_simulator --root . validate`.
5. Describe wire-format changes and compatibility impact in the pull request.

Apache-2.0 is the project license. Contributions are accepted under the same license.

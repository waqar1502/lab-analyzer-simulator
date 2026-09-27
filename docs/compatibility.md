# Host compatibility testing

The default test suite validates the simulator without contacting an external host. Compatibility with a specific gateway or LIS must be run separately in an isolated environment.

The repository includes an in-process ASTM fake host and proves ASTM query/result sessions over real localhost TCP. That automated host is not a production LIS and does not replace a real-device compatibility test.

## Procedure

1. Obtain an approved test endpoint and test-only sender/receiver values.
2. Set `LAB_SIM_MODE=live`, host, port, and MSH configuration in an uncommitted environment file.
3. Start the host listener and confirm it accepts MLLP connections.
4. Query a host-owned synthetic sample identifier.
5. Confirm the simulator receives and parses `DSR^Q03`.
6. Run the matching result profile.
7. Confirm the host receives `ORU^R01` and returns `AA` or `CA`.
8. For an ASTM endpoint, repeat the same flow with ENQ/ACK, query records, worklist records, result records, frame ACK/NAK, checksums, retries, and EOT.
9. Verify duplicate, reject, timeout, and malformed-message behavior in a controlled test window.

This repository does not alter the host application, database, gateway, or production configuration. Record the endpoint, test date, message IDs, and outcome in the host integration test report, but do not commit PHI or credentials.

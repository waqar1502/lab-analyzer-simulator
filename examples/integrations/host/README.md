# Generic HL7/MLLP host example

This directory is only an integration example. It is not required by the simulator and contains no application source, database access, tenant/facility data, credentials, or production addresses.

To point a local test deployment at an approved HL7/MLLP listener, use environment variables in a local, uncommitted override:

```text
LAB_SIM_MODE=live
LAB_SIM_GATEWAY_HOST=127.0.0.1
LAB_SIM_GATEWAY_PORT=2575
LAB_SIM_SENDER_APPLICATION=LAB_ANALYZER_SIMULATOR
LAB_SIM_SENDER_FACILITY=TEST_FACILITY
LAB_SIM_RECEIVER_APPLICATION=LAB_HOST
LAB_SIM_RECEIVER_FACILITY=TEST_LAB
```

The host must provide a test-only worklist response for the sample identifier used by the client and must accept the simulator's `ORU^R01` result. Replace the placeholders with values from the approved test environment; never commit them.

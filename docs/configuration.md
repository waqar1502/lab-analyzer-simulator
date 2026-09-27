# Configuration

The default configuration is safe for local fixture testing:

| Variable | Default | Description |
|---|---:|---|
| `LAB_SIM_MODE` | `fixture` | `fixture` or `live` |
| `SIMULATOR_PROTOCOL` | `hl7` | `hl7` or `astm` |
| `LAB_SIM_BIND_HOST` | `127.0.0.1` | HTTP bind address |
| `LAB_SIM_WEB_PORT` | `8000` | Browser/API port |
| `LAB_SIM_GATEWAY_HOST` | `127.0.0.1` | Live MLLP host |
| `LAB_SIM_GATEWAY_PORT` | `2575` | Live MLLP port |
| `LAB_SIM_SENDER_APPLICATION` | `LAB_ANALYZER_SIMULATOR` | MSH-3 |
| `LAB_SIM_SENDER_FACILITY` | `SIMULATOR` | MSH-4 |
| `LAB_SIM_RECEIVER_APPLICATION` | `LAB_HOST` | MSH-5 |
| `LAB_SIM_RECEIVER_FACILITY` | `LAB` | MSH-6 |
| `LAB_SIM_CONNECT_TIMEOUT_SECONDS` | `3.0` | TCP connect timeout |
| `LAB_SIM_READ_TIMEOUT_SECONDS` | `5.0` | MLLP response timeout |
| `LAB_SIM_RANDOM_SEED` | `42` | Reproducible generated results; set empty/`None` for non-deterministic behavior |
| `LAB_SIM_ASTM_FRAME_SIZE` | `240` | Maximum ASTM payload bytes per frame |
| `LAB_SIM_ASTM_RETRY_COUNT` | `3` | ASTM NAK retry limit |
| `LAB_SIM_ASTM_CHECKSUM` | `true` | Validate and emit ASTM checksums |
| `LAB_SIM_ASTM_RECEIVE_TIMEOUT_SECONDS` | `5.0` | ASTM control/frame read timeout |

Environment variables override an optional JSON configuration file. Do not commit local configuration files containing network addresses or secrets.

The nested JSON shape in `config.example.json` is equivalent to these settings. YAML is intentionally not required so the runtime remains standard-library-only.

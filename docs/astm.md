# ASTM/LIS2 protocol

The simulator implements a generic ASTM E1381/E1394-style record and session adapter. It does not claim compatibility with a specific analyzer vendor or model.

## Records

The supported record model is:

```text
H|\\^&|LAB_ANALYZER_SIMULATOR|SIMULATOR|2.0
P|1|PATIENT-ID|||Synthetic Patient
O|1|ACCESSION|ORDER||||TEST^Name\\TEST2^Name|R
Q|1|SAMPLE-ID|ALL|
R|1|TEST^Name|VALUE|UNIT|REFERENCE|N|F
C|1|Comment text
L|1|N
```

Queries use `H`, `Q`, `L`. Worklist responses use `H`, `P`, `O`, `L`. Results use `H`, `P`, `O`, one `R` per result, and `L`. `C` is parsed as a supported record and may be used by a host profile; the generic simulator does not generate comments by default.

## Session and framing

The TCP session uses:

```text
ENQ  0x05  request to transmit
ACK  0x06  positive response
NAK  0x15  negative response / retry
STX  0x02  frame start
ETB  0x17  intermediate frame terminator
ETX  0x03  final frame terminator
EOT  0x04  session end
CRLF 0x0D 0x0A frame suffix
```

A frame is:

```text
STX + frame-number + payload + ETB/ETX + two ASCII checksum characters + CRLF
```

The checksum is the modulo-256 sum of frame-number, payload, and ETB/ETX, formatted as two uppercase hexadecimal characters. Frames are acknowledged individually. NAK causes retransmission up to `astm_retry_count`. Repeated previous frames are acknowledged without duplicating their payload. Query responses begin a second ENQ session after the query EOT.

## Configuration

Use environment variables or `config.example.json`:

```text
SIMULATOR_PROTOCOL=astm
LAB_SIM_MODE=live
LAB_SIM_GATEWAY_HOST=127.0.0.1
LAB_SIM_GATEWAY_PORT=5000
LAB_SIM_ASTM_FRAME_SIZE=240
LAB_SIM_ASTM_RETRY_COUNT=3
LAB_SIM_ASTM_CHECKSUM=true
```

One Docker image supports both HL7 and ASTM. Use `SIMULATOR_PROTOCOL=hl7` or `SIMULATOR_PROTOCOL=astm`; no separate image is required.

## Troubleshooting

- `ASTM control response timed out`: verify the host sends ACK after ENQ and every frame.
- `checksum mismatch`: capture the complete STX-to-CRLF frame and compare the two checksum characters with the modulo-256 sum.
- `unexpected frame number`: check whether the host retransmitted a prior frame; the simulator ACKs the immediately previous frame and NAKs other unexpected numbers.
- `connection closed mid ASTM frame`: inspect host reset behavior and frame-size limits.
- Empty result response: normal ASTM result sessions may end after frame ACKs and EOT; query sessions must return a second ASTM worklist session.

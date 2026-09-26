from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from .domain import Settings


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def load_settings(config_path: Path | None = None) -> Settings:
    settings = Settings()
    if config_path and config_path.exists():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        settings = replace(settings, **{key: value for key, value in raw.items() if hasattr(settings, key)})

    prefix = "LAB_SIM_"
    replacements: dict[str, Any] = {
        "mode": os.getenv(prefix + "MODE"),
        "bind_host": os.getenv(prefix + "BIND_HOST"),
        "web_port": os.getenv(prefix + "WEB_PORT"),
        "gateway_host": os.getenv(prefix + "GATEWAY_HOST"),
        "gateway_port": os.getenv(prefix + "GATEWAY_PORT"),
        "sender_application": os.getenv(prefix + "SENDER_APPLICATION"),
        "sender_facility": os.getenv(prefix + "SENDER_FACILITY"),
        "receiver_application": os.getenv(prefix + "RECEIVER_APPLICATION"),
        "receiver_facility": os.getenv(prefix + "RECEIVER_FACILITY"),
        "hl7_version": os.getenv(prefix + "HL7_VERSION"),
        "protocol_profile": os.getenv(prefix + "PROTOCOL_PROFILE"),
        "connect_timeout_seconds": os.getenv(prefix + "CONNECT_TIMEOUT_SECONDS"),
        "read_timeout_seconds": os.getenv(prefix + "READ_TIMEOUT_SECONDS"),
        "max_message_bytes": os.getenv(prefix + "MAX_MESSAGE_BYTES"),
        "random_seed": os.getenv(prefix + "RANDOM_SEED"),
    }
    converted: dict[str, Any] = {}
    integer_fields = {"web_port", "gateway_port", "max_message_bytes", "random_seed"}
    float_fields = {"connect_timeout_seconds", "read_timeout_seconds"}
    for key, value in replacements.items():
        if value is None or value == "":
            continue
        if key in integer_fields:
            converted[key] = None if value.lower() == "none" else int(value)
        elif key in float_fields:
            converted[key] = float(value)
        else:
            converted[key] = value
    if converted:
        settings = replace(settings, **converted)
    if settings.mode not in {"fixture", "live"}:
        raise ValueError("mode must be 'fixture' or 'live'")
    return settings


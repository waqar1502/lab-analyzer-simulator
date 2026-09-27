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
        flat = dict(raw)
        if isinstance(raw.get("protocol"), dict):
            flat["protocol"] = raw["protocol"].get("type", settings.protocol)
        if isinstance(raw.get("transport"), dict):
            flat["gateway_host"] = raw["transport"].get("host", settings.gateway_host)
            flat["gateway_port"] = raw["transport"].get("port", settings.gateway_port)
            flat["read_timeout_seconds"] = raw["transport"].get("timeout_seconds", settings.read_timeout_seconds)
        if isinstance(raw.get("analyzer"), dict):
            flat["analyzer_name"] = raw["analyzer"].get("name", settings.analyzer_name)
        if isinstance(raw.get("astm"), dict):
            flat.update({
                "astm_frame_size": raw["astm"].get("frame_size", settings.astm_frame_size),
                "astm_retry_count": raw["astm"].get("retry_count", settings.astm_retry_count),
                "astm_checksum": raw["astm"].get("checksum", settings.astm_checksum),
                "astm_receive_timeout_seconds": raw["astm"].get(
                    "receive_timeout_seconds", settings.astm_receive_timeout_seconds
                ),
            })
        settings = replace(settings, **{key: value for key, value in flat.items() if hasattr(settings, key) and not isinstance(value, dict)})

    prefix = "LAB_SIM_"
    replacements: dict[str, Any] = {
        "mode": os.getenv(prefix + "MODE"),
        "protocol": os.getenv("SIMULATOR_PROTOCOL") or os.getenv(prefix + "PROTOCOL"),
        "analyzer_name": os.getenv(prefix + "ANALYZER_NAME"),
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
        "astm_frame_size": os.getenv(prefix + "ASTM_FRAME_SIZE"),
        "astm_retry_count": os.getenv(prefix + "ASTM_RETRY_COUNT"),
        "astm_checksum": os.getenv(prefix + "ASTM_CHECKSUM"),
        "astm_receive_timeout_seconds": os.getenv(prefix + "ASTM_RECEIVE_TIMEOUT_SECONDS"),
    }
    converted: dict[str, Any] = {}
    integer_fields = {"web_port", "gateway_port", "max_message_bytes", "random_seed", "astm_frame_size", "astm_retry_count"}
    float_fields = {"connect_timeout_seconds", "read_timeout_seconds"}
    for key, value in replacements.items():
        if value is None or value == "":
            continue
        if key in integer_fields:
            converted[key] = None if value.lower() == "none" else int(value)
        elif key in float_fields:
            converted[key] = float(value)
        elif key == "astm_receive_timeout_seconds":
            converted[key] = float(value)
        elif key == "astm_checksum":
            converted[key] = _as_bool(value, settings.astm_checksum)
        else:
            converted[key] = value
    if converted:
        settings = replace(settings, **converted)
    if settings.mode not in {"fixture", "live"}:
        raise ValueError("mode must be 'fixture' or 'live'")
    if settings.protocol not in {"hl7", "astm"}:
        raise ValueError("protocol must be 'hl7' or 'astm'")
    return settings

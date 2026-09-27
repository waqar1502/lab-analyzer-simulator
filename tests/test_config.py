import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lab_analyzer_simulator.config import load_settings


class ConfigTests(unittest.TestCase):
    def test_nested_astm_config_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "simulator.json"
            path.write_text(json.dumps({
                "mode": "fixture",
                "protocol": {"type": "astm"},
                "transport": {"host": "lis.example", "port": 5010, "timeout_seconds": 7},
                "astm": {"frame_size": 96, "retry_count": 5, "checksum": False, "receive_timeout_seconds": 9},
            }), encoding="utf-8")
            settings = load_settings(path)

        self.assertEqual("astm", settings.protocol)
        self.assertEqual("lis.example", settings.gateway_host)
        self.assertEqual(5010, settings.gateway_port)
        self.assertEqual(7, settings.read_timeout_seconds)
        self.assertEqual(96, settings.astm_frame_size)
        self.assertEqual(5, settings.astm_retry_count)
        self.assertFalse(settings.astm_checksum)
        self.assertEqual(9, settings.astm_receive_timeout_seconds)

    def test_environment_protocol_overrides_file(self) -> None:
        with patch.dict(os.environ, {"SIMULATOR_PROTOCOL": "astm"}, clear=False):
            settings = load_settings()
        self.assertEqual("astm", settings.protocol)


if __name__ == "__main__":
    unittest.main()

import unittest

from lab_analyzer_simulator.transports.astm.framing import AstmFrame, AstmFrameError, ETB


class AstmFramingTests(unittest.TestCase):
    def test_checksum_round_trip_and_etb(self) -> None:
        encoded = AstmFrame(1, b"H|header\r", final=False).encode()
        decoded = AstmFrame.decode(encoded)
        self.assertEqual(1, decoded.number)
        self.assertEqual(b"H|header\r", decoded.payload)
        self.assertIn(ETB, encoded)
        self.assertFalse(decoded.final)

    def test_invalid_checksum_is_rejected(self) -> None:
        encoded = AstmFrame(1, b"H|header\r", final=True).encode()
        corrupted = encoded[:-4] + b"00" + encoded[-2:]
        with self.assertRaises(AstmFrameError):
            AstmFrame.decode(corrupted)

    def test_frame_numbers_are_bounded(self) -> None:
        with self.assertRaises(AstmFrameError):
            AstmFrame(8, b"x", True).encode()


if __name__ == "__main__":
    unittest.main()

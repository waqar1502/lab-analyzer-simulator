import socket
import threading
import unittest

from lab_analyzer_simulator.domain import Settings
from lab_analyzer_simulator.protocols.hl7 import Hl7Protocol
from lab_analyzer_simulator.transports.mllp import MllpTransport


class MllpTransportTests(unittest.TestCase):
    def test_round_trip_preserves_hl7_payload(self) -> None:
        ready = threading.Event()
        received: list[bytes] = []
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def serve() -> None:
            ready.set()
            connection, _ = server.accept()
            with connection:
                data = connection.recv(10000)
                received.append(data)
                connection.sendall(b"\x0bMSH|^~\\&|HOST|LAB\rMSA|AA|1|Accepted\r\x1c\x0d")
            server.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        ready.wait(1)
        transport = MllpTransport("127.0.0.1", port, 1, 1, 10000)
        response = transport.send("MSH|^~\\&|SIM|LAB\r")
        thread.join(1)
        self.assertIn("MSA|AA|1", response)
        self.assertTrue(received[0].startswith(b"\x0b"))
        self.assertTrue(received[0].endswith(b"\x1c\x0d"))


if __name__ == "__main__":
    unittest.main()

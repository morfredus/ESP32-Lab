"""
Gestion de la connexion série avec un ESP32.
"""

import time
import serial


class SerialConnection:
    """Connexion série simple avec un périphérique ESP32."""

    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    def open(self):
        """Ouvre la connexion série."""

        if self.connection and self.connection.is_open:
            return

        self.connection = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

        # Laisse le temps à l'ESP32 de se stabiliser.
        time.sleep(2)

    def close(self):
        """Ferme la connexion série."""

        if self.connection and self.connection.is_open:
            self.connection.close()

    def is_open(self):
        """Indique si la connexion est ouverte."""

        return self.connection is not None and self.connection.is_open

    def read_line(self):
        """Lit une ligne provenant de l'ESP32."""

        if not self.is_open():
            raise RuntimeError("La connexion série n'est pas ouverte.")

        data = self.connection.readline()

        if not data:
            return None

        return data.decode("utf-8", errors="replace").strip()

    def write_line(self, message):
        """Envoie une ligne à l'ESP32."""

        if not self.is_open():
            raise RuntimeError("La connexion série n'est pas ouverte.")

        self.connection.write((message + "\n").encode("utf-8"))

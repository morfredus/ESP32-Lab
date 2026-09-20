"""
Test manuel de communication série avec un ESP32.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transport.serial_connection import SerialConnection


PORT = "/dev/ttyACM0"


def main():
    connection = SerialConnection(PORT)

    try:
        print(f"Ouverture du port {PORT}...")
        connection.open()

        print("Connexion ouverte.")
        print("Lecture des messages pendant 10 secondes...\n")

        import time

        start_time = time.time()

        while time.time() - start_time < 10:
            line = connection.read_line()

            if line:
                print(f"[ESP32] {line}")

        print("\nFin du test.")

    except Exception as error:
        print(f"Erreur : {error}")

    finally:
        connection.close()
        print("Port série fermé.")


if __name__ == "__main__":
    main()

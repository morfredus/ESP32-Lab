"""
Moniteur série simple pour ESP32.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transport.serial_connection import SerialConnection


PORT = "/dev/ttyACM0"
BAUDRATE = 115200
DURATION = 30


def main():
    connection = SerialConnection(
        port=PORT,
        baudrate=BAUDRATE,
        timeout=0.5,
    )

    try:
        print(f"Connexion à {PORT} à {BAUDRATE} bauds...")
        connection.open()

        print("Moniteur actif pendant 30 secondes.")
        print("Appuie sur RESET de l'ESP32 maintenant.\n")

        start_time = time.time()

        while time.time() - start_time < DURATION:
            line = connection.read_line()

            if line is not None:
                print(f"[SERIE] {line}")

        print("\nFin du moniteur.")

    except KeyboardInterrupt:
        print("\nArrêt demandé.")

    except Exception as error:
        print(f"Erreur : {error}")

    finally:
        connection.close()
        print("Port série fermé.")


if __name__ == "__main__":
    main()

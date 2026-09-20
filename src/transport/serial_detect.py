"""
Détection des ports série disponibles sur le système.
"""

from serial.tools import list_ports


def detect_serial_ports():
    """
    Retourne la liste des ports série détectés.
    """

    ports = []

    for port in list_ports.comports():

        ports.append({
            "device": port.device,
            "description": port.description,
            "manufacturer": port.manufacturer,
            "product": port.product,
            "serial_number": port.serial_number,
            "vid": port.vid,
            "pid": port.pid,
        })

    return ports


if __name__ == "__main__":

    detected_ports = detect_serial_ports()

    if not detected_ports:
        print("Aucun port série détecté.")
    else:
        print(f"{len(detected_ports)} port(s) détecté(s) :\n")

        for port in detected_ports:
            print(f"Port         : {port['device']}")
            print(f"Description  : {port['description']}")
            print(f"Fabricant    : {port['manufacturer']}")
            print(f"Produit      : {port['product']}")
            print(f"Numéro série : {port['serial_number']}")
            print(f"VID          : {port['vid']}")
            print(f"PID          : {port['pid']}")
            print("-" * 50)

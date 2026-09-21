"""
Tests de l'annonce morfBeacon.
"""

import json
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.morfbeacon import (
    APP_NAME,
    BEACON_PORT,
    CAPABILITIES,
    PROTO,
    beacon_payload,
    start_heartbeat,
)


def test_payload_fields():
    payload = beacon_payload("0.5.3", 8765, "test-host", now=1000)
    assert payload["proto"] == PROTO
    assert payload["app"] == APP_NAME
    assert payload["host"] == "test-host"
    assert payload["version"] == "0.5.3"
    assert payload["state"] == "ok"
    assert payload["status_port"] == 8765
    assert payload["instance"] == "ESP32-Lab@test-host"
    assert payload["capabilities"] == CAPABILITIES
    assert payload["capabilities"] == ["esp32-characterization"]
    assert payload["ts"] == 1000


def test_payload_json_serializable():
    # Le heartbeat est diffusé en JSON : il doit être sérialisable.
    json.dumps(beacon_payload("1.0.0", 8765, "h"))


def test_heartbeat_broadcasts():
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("", BEACON_PORT))
    listener.settimeout(3)

    stop = start_heartbeat("9.9.9", 8765, interval=0.2)
    try:
        data, _ = listener.recvfrom(2048)
        payload = json.loads(data.decode("utf-8"))
        assert payload["app"] == APP_NAME
        assert payload["version"] == "9.9.9"
        assert payload["capabilities"] == ["esp32-characterization"]
    finally:
        stop.set()
        listener.close()


if __name__ == "__main__":
    test_payload_fields()
    test_payload_json_serializable()
    test_heartbeat_broadcasts()
    print("Tous les tests morfBeacon sont réussis.")

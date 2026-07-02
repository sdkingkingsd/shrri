"""
IoT Agent — SHRRI AI OS v2 (Phase 5)

No IoT/smart-home integration existed anywhere in this codebase, and
no MQTT broker or devices are currently configured. Rather than fake
device state, this agent is built around real paho-mqtt (just
installed) and honestly reports "no broker configured" until one is
set up — same honesty pattern used in Android Agent for "no device
connected".

To actually control real devices: set MQTT_BROKER_HOST (and
optionally MQTT_BROKER_PORT/MQTT_USERNAME/MQTT_PASSWORD) in
shrri_config_local.py, same pattern as BOT_TOKEN/YOUR_ID, then this
agent's publish/subscribe commands will work against a real broker
(e.g. Mosquitto, Home Assistant's built-in broker, etc).

Intent routing (checked in order):
  - "turn on"/"turn off"/"toggle" + device -> publish an MQTT command
    to a topic derived from the device name
  - "status of"/"check" + device            -> subscribe briefly and
    report the last retained value on that device's status topic
  - everything else                          -> explain setup status
    and available commands
"""

import re
import time

try:
    import paho.mqtt.client as mqtt
    _MQTT_AVAILABLE = True
except ImportError:
    _MQTT_AVAILABLE = False


def _get_broker_config():
    try:
        from shrri_config_local import MQTT_BROKER_HOST
    except ImportError:
        try:
            from shrri_config import MQTT_BROKER_HOST
        except ImportError:
            return None
    port = 1883
    username = None
    password = None
    try:
        from shrri_config_local import MQTT_BROKER_PORT
        port = MQTT_BROKER_PORT
    except ImportError:
        pass
    try:
        from shrri_config_local import MQTT_USERNAME, MQTT_PASSWORD
        username, password = MQTT_USERNAME, MQTT_PASSWORD
    except ImportError:
        pass
    return {"host": MQTT_BROKER_HOST, "port": port, "username": username, "password": password}


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


class IoTAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def _publish(self, topic: str, payload: str) -> str:
        if not _MQTT_AVAILABLE:
            return "GAP: paho-mqtt is not installed on this machine."
        config = _get_broker_config()
        if not config:
            return (
                "No MQTT broker configured yet. Add MQTT_BROKER_HOST to "
                "shrri_config_local.py (same pattern as BOT_TOKEN) to "
                "connect this to real smart-home devices."
            )
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            if config["username"]:
                client.username_pw_set(config["username"], config["password"])
            client.connect(config["host"], config["port"], keepalive=5)
            client.loop_start()
            client.publish(topic, payload, qos=1)
            time.sleep(0.5)
            client.loop_stop()
            client.disconnect()
            return f"Published '{payload}' to {topic}."
        except Exception as e:
            return f"GAP: MQTT publish failed — {e}"

    def _subscribe_once(self, topic: str, timeout: float = 3.0) -> str:
        if not _MQTT_AVAILABLE:
            return "GAP: paho-mqtt is not installed on this machine."
        config = _get_broker_config()
        if not config:
            return (
                "No MQTT broker configured yet. Add MQTT_BROKER_HOST to "
                "shrri_config_local.py (same pattern as BOT_TOKEN) to "
                "connect this to real smart-home devices."
            )
        result = {"value": None}

        def on_message(client, userdata, msg):
            result["value"] = msg.payload.decode(errors="replace")

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            if config["username"]:
                client.username_pw_set(config["username"], config["password"])
            client.on_message = on_message
            client.connect(config["host"], config["port"], keepalive=5)
            client.subscribe(topic)
            client.loop_start()
            time.sleep(timeout)
            client.loop_stop()
            client.disconnect()
            if result["value"] is None:
                return f"No retained value found on {topic} (device may be offline or topic has no retained status)."
            return f"{topic}: {result['value']}"
        except Exception as e:
            return f"GAP: MQTT subscribe failed — {e}"

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[iot_agent] Handling: {prompt[:80]!r}")

        onoff_match = re.search(r"\b(turn on|turn off|toggle)\b\s+(?:the\s+)?(.+)$", low)
        if onoff_match:
            action = onoff_match.group(1)
            device = onoff_match.group(2).strip()
            slug = _slugify(device)
            state = "ON" if "on" in action and "off" not in action else ("TOGGLE" if "toggle" in action else "OFF")
            topic = f"shrri/{slug}/set"
            return self._publish(topic, state)

        status_match = re.search(r"\b(?:status of|check|is)\b\s+(?:the\s+)?(.+?)(?:\s+on\??)?$", low)
        if status_match and ("status" in low or "check" in low):
            device = status_match.group(1).strip()
            slug = _slugify(device)
            topic = f"shrri/{slug}/state"
            return self._subscribe_once(topic)

        config = _get_broker_config()
        if not config:
            return (
                "No smart-home/IoT devices are configured yet — no MQTT "
                "broker is set up. Add MQTT_BROKER_HOST to "
                "shrri_config_local.py to connect real devices, then I "
                "can turn things on/off or check their status."
            )
        return (
            "I can turn a device on/off/toggle, or check a device's "
            "status, over MQTT — say which device and what you want."
        )

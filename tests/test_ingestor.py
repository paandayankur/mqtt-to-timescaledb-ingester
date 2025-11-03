import pytest
from unittest.mock import Mock, patch, call
import json
import time
from queue import Queue

# Import the functions and queues from your ingestor script
from esphome_mqtt_timescaledb_ingestor.ingestor import (
    on_mqtt_message,
    discovery_queue,
    entity_queue,
    state_queue,
    status_queue,
    command_queue,
)

# Pytest fixture to clear queues before each test
@pytest.fixture(autouse=True)
def clear_queues():
    """Ensures all queues are empty before each test runs."""
    while not discovery_queue.empty():
        discovery_queue.get()
    while not entity_queue.empty():
        entity_queue.get()
    while not state_queue.empty():
        state_queue.get()
    while not status_queue.empty():
        status_queue.get()
    while not command_queue.empty():
        command_queue.get()

# Mock MQTT message class for creating test messages
class MockMQTTMessage:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload.encode('utf-8')

# --- Test Cases ---

def test_on_mqtt_message_status():
    """Tests routing of a device status message."""
    msg = MockMQTTMessage("mydevice/status", "online")
    on_mqtt_message(None, None, msg)
    assert not status_queue.empty()
    topic, payload = status_queue.get()
    assert topic == "mydevice/status"
    assert payload == 'online'

def test_on_mqtt_message_command():
    """Tests routing of a command message."""
    msg = MockMQTTMessage("mydevice/light/bulb/command", "TOGGLE")
    on_mqtt_message(None, None, msg)
    assert not command_queue.empty()
    topic, payload = command_queue.get()
    assert topic == "mydevice/light/bulb/command"
    assert payload == 'TOGGLE'

def test_on_mqtt_message_ha_discovery():
    """Tests routing of a Home Assistant discovery message."""
    payload = {
        "name": "Kitchen Light",
        "unique_id": "kitchen_light_abc",
        "device": {"name": "esphome-device1", "identifiers": ["esphome-device1"]},
        "state_topic": "~/state",
        "command_topic": "~/command",
        "component": "light"
    }
    msg = MockMQTTMessage("homeassistant/light/kitchen_light/config", json.dumps(payload))
    on_mqtt_message(None, None, msg)
    assert not entity_queue.empty()
    entity_msg = entity_queue.get()
    assert entity_msg['unique_id'] == 'kitchen_light_abc'
    assert entity_msg['component'] == 'light'

def test_on_mqtt_message_esphome_discovery():
    """Tests routing of an ESPHome discovery message."""
    payload = {
        "name": "esphome-device1",
        "ip": "192.168.1.50",
        "version": "2023.12.0"
    }
    msg = MockMQTTMessage("esphome/discover/esphome-device1", json.dumps(payload))
    on_mqtt_message(None, None, msg)
    assert not discovery_queue.empty()
    disc_msg = discovery_queue.get()
    assert disc_msg['name'] == 'esphome-device1'
    assert disc_msg['ip'] == '192.168.1.50'

def test_non_json_message_on_other_topic():
    """Ensures non-JSON messages on unexpected topics are skipped gracefully."""
    msg = MockMQTTMessage("some/other/topic", "just plain text")
    on_mqtt_message(None, None, msg)
    # Assert that no queues have received this message
    assert discovery_queue.empty()
    assert entity_queue.empty()
    assert state_queue.empty()
    assert status_queue.empty()
    assert command_queue.empty()

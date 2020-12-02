import json
import time
import requests

from numpy import clip
from rudder_config.message import Message
from rudder_config.server import SocketServer
from rudder_config.inputs import get_gamepad, get_key

r = requests.get("http://192.168.0.121:8899/api/rudder")
# 0 is the rudder.
CONFIG_RUDDER = r.json()[0]


def convert_pedals(value: int) -> int:
    """Translate value to 0-255."""
    global CONFIG_RUDDER
    mn = CONFIG_RUDDER["min_pedals"]
    mx = CONFIG_RUDDER["max_pedals"]
    x = (value - mn) / (mx - mn) * 255
    x = clip([x], 0, 255)[0]
    return int(x)


def convert_rudder(value: int) -> int:
    """Translate value to 0-255."""
    global CONFIG_RUDDER
    mn = CONFIG_RUDDER["min_rudder"]
    mx = CONFIG_RUDDER["max_rudder"]
    x = (value - mn) / (mx - mn) * 255
    x = clip([x], 0, 255)[0]
    return int(x)


def get_events(
        start_record,
        stop_record,
        start_keras,
        stop_keras,
        throttle,
        steering,
        reverse,
        movement_left,
        movement_right,
        movement_straight,
        throttle_level
) -> None:
    """Receives event from gamepad."""
    global CONFIG_RUDDER
    while True:
        events = get_gamepad()
        for event_ in events:
            # Direction of travel.
            # Left.
            if event_.code == CONFIG_RUDDER["movement_left"]:
                with movement_left.get_lock():
                    movement_left.value = event_.state
            # Straight.
            if event_.code == CONFIG_RUDDER["movement_straight"]:
                with movement_straight.get_lock():
                    movement_straight.value = event_.state
            # Right.
            if event_.code == CONFIG_RUDDER["movement_right"]:
                with movement_right.get_lock():
                    movement_right.value = event_.state

            # Start/stop keras
            if event_.code == CONFIG_RUDDER["start_keras"]:
                with start_keras.get_lock():
                    print("START KERAS -------------------")
                    start_keras.value = event_.state

            if event_.code == CONFIG_RUDDER["stop_keras"]:
                with stop_keras.get_lock():
                    print("STOP KERAS -------------------")
                    stop_keras.value = event_.state

            # Start/stop recording
            if event_.code == CONFIG_RUDDER["start_record"]:
                with start_record.get_lock():
                    start_record.value = event_.state

            if event_.code == CONFIG_RUDDER["stop_record"]:
                with stop_record.get_lock():
                    stop_record.value = event_.state

            if start_keras.value == 2:
                if event_.code == CONFIG_RUDDER["throttle"]:
                    with throttle.get_lock():
                        throttle.value = convert_pedals(event_.state)
                        throttle.value = int(throttle.value * throttle_level.value)
                if event_.code == CONFIG_RUDDER["steering"]:
                    with steering.get_lock():
                        steering.value = convert_rudder(event_.state)
                        steering.value = clip([steering.value], 0, 254)[0]

                if event_.code == CONFIG_RUDDER["reverse"]:
                    with reverse.get_lock():
                        reverse.value = event_.state


def sends_rudder(throttle, steering, reverse) -> None:
    """Socket server sending message about rudder status."""
    ss = SocketServer(host="0.0.0.0", port=5001)
    ss.start()
    while True:
        # print(throttle.value, steering.value, reverse.value)
        time.sleep(0.05)
        message = Message(
            throttle=throttle.value, steering=steering.value, reverse=reverse.value
        )
        ss.send(msg=message)

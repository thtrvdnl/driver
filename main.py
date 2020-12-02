import sys
import time

from multiprocessing import Process, Value, Array
from PyQt5.QtWidgets import QApplication

from qt.window import MissionTag
from process.vp import VideoPlayer
from process.process_keras import Keras
from process.recording import VideoRecording
from process.rudder import get_events, sends_rudder

if __name__ == "__main__":
    name_process = "video"

    button_start_recording = Value("i", 2)
    button_stop_recording = Value("i", 2)

    button_start_keras = Value("i", 2)
    button_stop_keras = Value("i", 2)

    throttle_shared = Value("i", 0)
    steering_shared = Value("i", 127)
    reverse_shared = Value("i", 0)

    movement_left = Value("i", 2)
    movement_right = Value("i", 2)
    movement_straight = Value("i", 2)

    throttle_level = Value("f", 0.6)
    tag_list = Array("c", 100)

    gps_shared = Value("i")
    compass_shared = Value("i")
    frame_num_shared = Value("i", 0)

    mission_329_327 = Value("i", 2)
    mission_reverse = Value("i", 2)
    mission_327_329 = Value("i", 2)

    video_player = Process(
        target=VideoPlayer,
        args=(
            name_process,
            button_start_recording,
            button_stop_recording,
            button_start_keras,
            button_stop_keras,
            throttle_shared,
            steering_shared,
            reverse_shared,
            frame_num_shared,
            movement_left,
            movement_right,
            movement_straight,
            tag_list,
        ),
    )
    video_player.start()
    keras_process = Process(
        target=Keras,
        args=(
            name_process,
            button_start_keras,
            button_stop_keras,
            throttle_shared,
            steering_shared,
            mission_329_327,
            mission_reverse,
            mission_327_329,
        ),
    )
    keras_process.start()

    # Process qt
    app = QApplication(sys.argv)
    window_qt = MissionTag(
        throttle_level, tag_list, mission_329_327, mission_reverse, mission_327_329
    )

    rudder_event = Process(
        target=get_events,
        args=(
            button_start_recording,
            button_stop_recording,
            button_start_keras,
            button_stop_keras,
            throttle_shared,
            steering_shared,
            reverse_shared,
            movement_left,
            movement_right,
            movement_straight,
            window_qt.throttle_level,
        ),
    )

    rudder = Process(
        target=sends_rudder, args=(throttle_shared, steering_shared, reverse_shared,)
    )

    recording_process = Process(
        target=VideoRecording,
        args=(
            name_process,
            button_start_recording,
            button_stop_recording,
            throttle_shared,
            steering_shared,
            frame_num_shared,
            movement_left,
            movement_right,
            movement_straight,
            window_qt.tag_list,
        ),
    )

    rudder_event.start()
    rudder.start()
    recording_process.start()

    sys.exit(app.exec_())

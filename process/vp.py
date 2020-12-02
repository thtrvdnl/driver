from read_write.write import ShmWrite
import numpy as np
import json
import cv2
import gi
import time

gi.require_version("Gst", "1.0")
from gi.repository import Gst


class VideoPlayer(object):
    fresh_frame = False

    def __init__(
            self,
            name_process: str,
            start_recording,
            stop_recording,
            start_keras,
            stop_keras,
            throttle,
            steering,
            reverse,
            frame_num,
            movement_left,
            movement_right,
            movement_straight,
            tag_list
    ):
        Gst.init(None)
        self._frame = None
        self.video_pipe = None
        self.video_sink = None
        # Shared memory.
        self.start_recording = start_recording
        self.stop_recording = stop_recording

        self.movement_left = movement_left
        self.movement_right = movement_right
        self.movement_straight = movement_straight

        self.keras_start = start_keras
        self.keras_stop = stop_keras

        self.steering = steering
        self.throttle = throttle
        self.reverse = reverse

        self.name_process = name_process
        self.tag_list = tag_list
        self.shm_w = ShmWrite(self.name_process)
        self.frame_num = frame_num

        self.display_image()

    def start_gst(self):
        """ Start gstreamer pipeline and sink
        Args:
            config (list, optional): Gstreamer pileline description list
        """
        with open("process/stream_pipeline.json") as pipe:
            config = json.load(pipe)
            pipeline = config["raspberry-big"]

        self.video_pipe = Gst.parse_launch(pipeline)
        self.video_pipe.set_state(Gst.State.PLAYING)
        self.video_sink = self.video_pipe.get_by_name("appsink0")

    def gst_to_opencv(self, sample: gi.repository.Gst.Sample):
        """Transform byte array into np array
        Args:
            sample (TYPE): Description
        Returns:
            TYPE: Description
        """
        buf = sample.get_buffer()
        caps = sample.get_caps()
        # print(caps.get_structure(0).get_value("format"))
        array = np.ndarray(
            (
                caps.get_structure(0).get_value("height"),
                caps.get_structure(0).get_value("width"),
                3,
            ),
            buffer=buf.extract_dup(0, buf.get_size()),
            dtype=np.uint8,
        )
        # Writing to the shared memory of the process.
        # BGR
        self.shm_w.add(array)
        self.frame_num.value += 1
        return array

    def frame(self) -> np.ndarray:
        """ Get Frame
        Returns:
            iterable: bool and image frame, cap.read() output
        """
        return self._frame

    def frame_available(self) -> bool:
        """Check if frame is available
        Returns:
            bool: true if frame is available
        """
        return type(self._frame) != type(None)

    def run(self) -> None:
        """ Get frame to update _frame. """
        self.start_gst()
        self.video_sink.connect("new-sample", self.callback)

    def callback(self, sink) -> gi.repository.Gst.FlowReturn:
        self.fresh_frame = True
        # print('new frame')
        sample = sink.emit("pull-sample")
        self._frame = self.gst_to_opencv(sample)
        return Gst.FlowReturn.OK

    def _interactive_rudder(self, frame: np.array) -> None:
        """ Draws a square with a dot to represent the AI rotation position and speed."""
        x_k = int(self.steering.value * 200 / 255) + 100
        if self.reverse.value == 0:
            y_k = -100 / 255
        else:
            y_k = 100 / 255
        y_k = int(self.throttle.value * y_k) + 800
        cv2.rectangle(
            frame, pt1=(100, 700), pt2=(300, 900), color=(255, 0, 0), thickness=3
        )
        cv2.circle(frame, center=(x_k, y_k), radius=10, color=(0, 0, 255), thickness=-1)

    def _interactive_rudder_sensor(self, frame: np.array) -> None:
        cv2.putText(
            frame,
            f"throttle: {self.throttle.value}",
            org=(100, 680),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1,
            color=(0, 0, 255),
            thickness=2,
        )
        cv2.putText(
            frame,
            f"steering: {self.steering.value}",
            org=(100, 650),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=1,
            color=(0, 0, 255),
            thickness=2,
        )

    def _predict_keras(self, frame: np.array) -> None:
        """ Beware of the killer mode. """
        if self.keras_start.value == 1 or self.keras_start.value == 0:
            cv2.putText(
                frame,
                "KILLER MODE!",
                org=(500, 100),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                color=(0, 0, 255),
                thickness=2,
            )
        else:
            cv2.putText(
                frame,
                "Quiet mode",
                org=(500, 100),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                color=(255, 0, 0),
                thickness=2,
            )

    def _recording_indicator(self, frame: np.array):
        """ Draws if video is being recorded. """
        if self.start_recording.value == 1 or self.start_recording.value == 0:
            cv2.putText(
                frame,
                "Record",
                org=(120, 100),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                color=(0, 0, 255),
                thickness=2,
            )
            cv2.circle(
                frame, center=(100, 100), radius=10, color=(0, 0, 255), thickness=-1
            )
            self._get_direction_movement(frame)

        else:
            cv2.circle(
                frame, center=(100, 100), radius=10, color=(0, 255, 0), thickness=-1
            )

    def _get_direction_movement(self, frame: np.array):
        """ Drawing movement left / right. """
        if self.movement_left.value == 1 or self.movement_left.value == 0:
            cv2.putText(
                frame,
                "movement left",
                org=(100, 300),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                color=(0, 0, 255),
                thickness=2,
            )

        if self.movement_right.value == 1 or self.movement_right.value == 0:
            cv2.putText(
                frame,
                "movement right",
                org=(100, 300),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                color=(0, 0, 255),
                thickness=2,
            )

    def _fool_check(self, frame):
        """ Check for attentiveness. """
        tag = self.tag_list.value.decode("utf-8").split("-")
        if tag[-1] == '' or tag is None:
            cv2.putText(
                frame,
                "NO TAG",
                org=(1000, 100),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                color=(0, 0, 255),
                thickness=2,
            )

    def display_image(self) -> None:
        """ Display frame with cv2. """
        self.run()
        cv2.namedWindow("main", cv2.WINDOW_AUTOSIZE)
        while True:
            time.sleep(0.005)
            if not self.frame_available() or not self.fresh_frame:
                time.sleep(0.01)
                continue
            self.fresh_frame = False
            frame = self.frame()
            if frame.shape[0] < 640 and frame.shape[1] < 640:
                continue

            self._fool_check(frame)
            self._predict_keras(frame)
            self._interactive_rudder(frame)
            self._interactive_rudder_sensor(frame)
            self._recording_indicator(frame)

            cv2.imshow("main", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                self.shm_w.release()
                break


if __name__ == "__main__":
    VideoPlayer("1", 1, 1)

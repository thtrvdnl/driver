from read_write.read import ShmRead
from pymongo import MongoClient
import datetime
import requests
import logging
import av
import gi

import time

gi.require_version("Gst", "1.0")
from gi.repository import Gst

logging.basicConfig(format="%(process)d-%(levelname)s-%(message)s")


class VideoRecording(object):
    def __init__(
            self,
            name_process,
            start_recording,
            stop_recording,
            throttle,
            steering,
            global_frame_num,
            movement_left,
            movement_right,
            movement_straight,
            tag_list
    ):
        Gst.init(None)
        # Shared memory.
        self.tag_list = tag_list

        self.start_recording = start_recording
        self.stop_recording = stop_recording

        self.throttle = throttle
        self.steering = steering

        self.movement_left = movement_left
        self.movement_right = movement_right
        self.movement_straight = movement_straight

        # block value
        self.block_record = 0

        self.global_frame_num = global_frame_num
        self.local_frame_num = -1
        self.is_recording = False

        # Video capture.
        self.container = None
        self.stream = None

        self.track_pk = None
        self.number_frame = 0

        # Shared array.
        self._shm_r = ShmRead(name_process)
        self._frame = None

        self._create_mongo_client()
        self._start_recording()

    def __init_new_video_file(self):
        self.number_frame = 0
        self._start_requests()
        self.container = av.open(
            f"/mnt/share110/airacing_sample/{self.track_pk}.mp4", mode="w"
        )
        self.stream = self.container.add_stream(
            "libx264",
            rate=25,
            options={
                "profile": "Baseline",
                "preset": "veryfast",
                "movflags": "faststart",
                "b": "5000000",
            },
        )
        self.stream.width = 1296
        self.stream.height = 972
        self.stream.pix_fmt = "yuv420p"

    def __save_frame_to_video(self, frame):
        self.number_frame += 1
        self._recording_mongo()
        av_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
        for packet in self.stream.encode(av_frame):
            self.container.mux(packet)

    def __end_video_file(self):
        for packet in self.stream.encode():
            self.container.mux(packet)
        self.container.close()
        self._stop_requests()
        self.container = None
        self.stream = None
        self.track_pk = None

    def _get_direction_movement(self):
        """ Adds noise to steering. """
        noise_left = 0
        noise_right = 0

        if (
                (self.movement_left.value == 0 and self.movement_right.value == 0)
                or (self.movement_left.value == 1 and self.movement_right.value == 0)
                or (self.movement_left.value == 0 and self.movement_right.value == 1)
        ):
            logging.warning("movement_left.value == 0 and movement_right.value == 0")
            with self.movement_left.get_lock():
                self.movement_left.value = 2
            with self.movement_right.get_lock():
                self.movement_right.value = 2
            noise_left = 0
            noise_right = 0

        if self.movement_left.value == 1 or self.movement_left.value == 0:
            noise_left = 1

        if self.movement_right.value == 1 or self.movement_right.value == 0:
            noise_right = 1

        if self.movement_straight.value == 1:
            with self.movement_left.get_lock():
                self.movement_left.value = 2
            with self.movement_right.get_lock():
                self.movement_right.value = 2

        return noise_left, noise_right

    def _start_requests(self) -> None:
        tag = self.tag_list.value.decode("utf-8").split("-")
        if tag[-1] == '':
            # test
            tag_int = ['test']  # TODO
            logging.warning(" haven't tag ")
        else:
            tag_int = [int(i) for i in tag]
            r = requests.post(
                f"...",
                json={"robocar_pk": 1, "mission_tag_pks": tag_int},
            )
            self.track_pk = r.json()["pk"]

    def _stop_requests(self) -> None:
        requests.get(f"...{self.track_pk}")

    def _create_mongo_client(self) -> None:
        self._db = MongoClient("192.168.0.101", port=27017)
        self._dataset = self._db["airacing"]["dataset"]

    def _transformation_rudder(self):
        pass

    def _recording_mongo(self) -> None:
        movement_left, movement_right = self._get_direction_movement()
        self._dataset.insert_one(
            {
                "file_name": str(self.track_pk),
                "recording_frame_num": self.number_frame,
                "datetime": datetime.datetime.utcnow(),
                "throttle": self.throttle.value,
                "steering": self.steering.value,
                "left": movement_left,
                "right": movement_right,
            }
        )

    def _start_recording(self):
        while True:
            time.sleep(0.01)
            if self.start_recording.value == 1:
                if None in [self.container, self.stream]:
                    self.__init_new_video_file()
                    self.is_recording = True

            if self.stop_recording.value == 1:
                if self.is_recording:
                    self.__end_video_file()
                    with self.start_recording.get_lock():
                        self.start_recording.value = 2
                    with self.stop_recording.get_lock():
                        self.stop_recording.value = 2
                    self.is_recording = False

            if None not in [self.stream, self.container]:
                if self.local_frame_num == self.global_frame_num.value:
                    continue
                self.local_frame_num = self.global_frame_num.value

                self._frame = self._shm_r.get()
                self.__save_frame_to_video(self._frame)


if __name__ == "__main__":
    VideoRecording()

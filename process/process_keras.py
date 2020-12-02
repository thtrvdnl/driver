from keras.models import Sequential, Model
from keras.layers import (
    Reshape,
    Dense,
    Flatten,
    LSTM,
    Activation,
    Dropout,
    BatchNormalization,
    Conv2D,
    MaxPooling2D,
    AveragePooling2D,
    GlobalMaxPooling2D,
    LeakyReLU,
    ELU,
    Input,
    UpSampling2D,
    Concatenate,
)
from keras import regularizers
from keras.optimizers import Adam, Adamax, Adadelta, Adagrad, Nadam, SGD, RMSprop
from keras.models import load_model

from read_write.read import ShmRead

# from generator.aidriver import run
import numpy as np
from threading import Thread
import cv2
import time


class Keras:
    def __init__(
            self,
            name_process: str,
            start_keras,
            stop_keras,
            throttle,
            steering,
            mission_329_327,
            mission_reverse,
            mission_327_329
    ):
        # Shared memory.
        self._shm_r = ShmRead(name_process)

        self.keras_start = start_keras
        self.keras_stop = stop_keras

        self.throttle = throttle
        self.steering = steering

        self.mission_329_327 = mission_329_327
        self.mission_reverse = mission_reverse
        self.mission_327_329 = mission_327_329

        self.model_list = [
            "/mnt/share110/airacing_sample/models/model1.h5",
        ]
        self.model = load_model(self.model_list[0])

        self.killer_mod()

    def _run_predict(self, frame: np.array):
        """ A neural network designed to kill. """
        frame = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA) * (
                1.0 / 255.0
        )

        print("pred 64")
        res = self.model.predict(np.array([frame]))[0]
        return (round(res[0] * 64.0 + 127), round(res[1] * 255.0))

    def _load_mission_model(self, mission_id: int):
        self.model = load_model(self.model_list[mission_id])

    def killer_mod(self):
        """ Run leather bastards. """
        mission_id = 0
        block_value = 0
        self._load_mission_model(mission_id)
        while True:

            frame = self._shm_r.get()

            if (
                    self.keras_start.value == 1
                    or self.keras_start.value == 0
                    and block_value == 0
            ):
                sensor = self._run_predict(frame)

                (steering, throttle) = sensor
                steering = np.clip(steering, 0, 255)
                throttle = np.clip(throttle, 0, 255)

                print("KERAS PREDICT:", sensor)

                with self.steering.get_lock():
                    self.steering.value = int(steering)
                with self.throttle.get_lock():
                    self.throttle.value = int(throttle)

            if self.keras_stop.value == 1:
                block_value = 0
                with self.throttle.get_lock():
                    self.throttle.value = 0
                with self.keras_start.get_lock():
                    self.keras_start.value = 2
                with self.keras_stop.get_lock():
                    self.keras_stop.value = 2

from dataset_merge import DatasetLoader
from pymongo import MongoClient
import random
import math
import cv2
import numpy as np

import requests


def data_generator(tag_pks: list, video_pks: list, batch_size: int = 16, buffer_size: int = 1000):
    buffer = []

    number_frame = 1

    video_list_name = []
    for f in video_pks:
        video_list_name.append("/mnt/share110/airacing_sample/" + str(f) + ".mp4")
    random.shuffle(video_list_name)

    dl = DatasetLoader()

    init_buffer = True

    # Go around all videos.
    video_idx = 0
    while True:
        #        video_idx = video_idx + 1
        if (video_idx >= len(video_list_name)): video_idx = 0
        print('video_idx = ', video_idx)
        # Init new data(mongo).
        track_id = int(video_list_name[video_idx].split("/")[-1].split(".")[0])
        dl.load(track_id)
        print('track_id = ', track_id)
        # Init new video capture.
        cap = cv2.VideoCapture(video_list_name[video_idx])
        frames_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        if (frames_count < buffer_size and init_buffer):
            print('skipping video: not enough frames to fill buffer')
            video_idx += 1
            continue
        print(f"INIT VIDEO CAPTURE:{track_id}, {frames_count}")

        flag = True

        while flag:
            x_batch = []
            y_batch = []

            if init_buffer:
                print(f"INIT BUFFER:{init_buffer}")
                # Initialize the buffer.
                for _ in range(buffer_size):
                    print("INIT", number_frame)
                    _, frame = cap.read()
                    frame = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA) * (1.0 / 255.0)
                    dframe = number_frame + random.randint(2, 8)
                    if (dframe > frames_count - 1): dframe = frames_count - 1

                    predict = dl.get_data(dframe)
                    #                    print(predict)
                    steer_correction = 0.0
                    if 'left' in predict and predict['left'] != 0: steer_correction = -25.0
                    if 'right' in predict and predict['right'] != 0: steer_correction = 25.0
                    predict = [(predict["steering"] + steer_correction - 127) / 32.0, predict["throttle"] / 255.0]

                    buffer.append([frame, predict])
                    number_frame += 1

                init_buffer = False

            else:
                #
                for i in range(batch_size):
                    # Random append in buffer.
                    _, frame = cap.read()
                    frame = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA) * (1.0 / 255.0)
                    dframe = number_frame + random.randint(2, 8)
                    if (dframe > frames_count - 1): dframe = frames_count - 1

                    predict = dl.get_data(dframe)
                    steer_correction = 0.0
                    if 'left' in predict and predict['left'] != 0: steer_correction = -25.0
                    if 'right' in predict and predict['right'] != 0: steer_correction = 25.0
                    predict = [(predict["steering"] + steer_correction - 127) / 32.0, predict["throttle"] / 255.0]

                    id_ = random.randint(0, buffer_size - 1)
                    buffer[id_][0] = frame
                    buffer[id_][1] = predict

                    if number_frame == frames_count:
                        print(f"EXIT--------------")
                        # Go to next video.
                        number_frame = 1
                        video_idx += 1
                        flag = False
                        break

                    number_frame += 1

            for _ in range(batch_size):
                id_ = random.randint(0, buffer_size - 1)
                x_batch.append(buffer[id_][0])
                y_batch.append(buffer[id_][1])

            r = np.array(x_batch), np.array(y_batch)
            yield r


if __name__ == '__main__':

    a = data_generator([])
    stop = 0
    for i in a:
        stop += 1
        x, y = i
        print(f"PREDICT:{y}")
        if stop == 1000:
            break

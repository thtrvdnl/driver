# from dataset_merge import DatasetLoader
from pymongo import MongoClient
import random
import math
import cv2


def data_generator(
        video_list_name: list, batch_size: int = 4, buffer_size: int = 10, frame_id: int = 0
):
    buffer = []
    number_frame = 1
    video_list_name = [
        "/mnt/share110/airacing_sample/87.mp4",
        "/mnt/share110/airacing_sample/86.mp4",
        "/mnt/share110/airacing_sample/85.mp4",
        "/mnt/share110/airacing_sample/84.mp4",
        "/mnt/share110/airacing_sample/83.mp4",
    ]

    dl = DatasetLoader()

    init_buffer = True

    # Go around all videos.
    while True:
        # Init new data(mongo).
        video_idx = random.randint(0, len(video_list_name) - 1)
        track_id = int(video_list_name[video_idx].split("/")[-1].split(".")[0])
        dl.load(track_id)
        # Init new video capture.
        cap = cv2.VideoCapture(video_list_name[video_idx])
        frames_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"INIT VIDEO CAPTURE:{track_id}, {frames_count}")

        flag = True

        while flag:
            x_batch = []
            y_batch = []
            # What frame do we start with.
            # cap.set(arg1, arg2), where arg2 begin in 0.
            print(f"number_frame: {number_frame}")
            cap.set(cv2.CAP_PROP_POS_FRAMES, number_frame - 1)
            if init_buffer:
                print(f"INIT BUFFER:{init_buffer}")
                # Initialize the buffer.
                for i in range(buffer_size):
                    print("INIT", number_frame)
                    _, frame = cap.read()

                    sensor = dl.get_data(number_frame)
                    # center - 56.834718, 60.791521
                    # x - 56.835618 60.791521
                    # y - 56.834718, 60.793721
                    gps_lat = (sensor["gps_lat"] - 56.834718) / 0.0015  # 15
                    gps_lng = (sensor["gps_lng"] - 60.791521) / 0.0015  # 15
                    sensor = [
                        gps_lat,
                        gps_lng,
                        math.cos(sensor["heading"]),
                        math.sin(sensor["heading"]),
                    ]

                    predict = dl.get_data(number_frame)
                    predict = [predict["throttle"], predict["steering"]]

                    print(gps_lat, gps_lng)
                    buffer.append([frame, sensor, predict])
                    number_frame += 1

                init_buffer = False
                print(len(buffer))
            else:
                print(f"RANDOM--------------")
                for i in range(batch_size):
                    # Random append in buffer.
                    print("RANDOM", number_frame)
                    _, frame = cap.read()
                    sensor = dl.get_data(number_frame)
                    sensor = [sensor["gps_lat"], sensor["gps_lng"], math.cos(sensor["heading"]),
                              math.sin(sensor["heading"])]

                    predict = dl.get_data(number_frame)
                    predict = [predict["throttle"], predict["steering"]]

                    id_ = random.randint(0, buffer_size - 1)
                    buffer[id_][0] = frame
                    buffer[id_][1] = sensor
                    buffer[id_][2] = predict

                    if number_frame == frames_count:
                        print(f"EXIT--------------")
                        # Go to next video.
                        number_frame = 1
                        video_idx += 1
                        flag = False
                        break

                    number_frame += 1

            for i in range(batch_size):
                id_ = random.randint(0, buffer_size - 1)
                print(f"YIELD: {id_}")
                x_batch.append(buffer[id_][:2])
                y_batch.append(buffer[id_][2])

            yield x_batch, y_batch


if __name__ == "__main__":
    a = data_generator([])

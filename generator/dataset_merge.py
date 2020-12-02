from pymongo import MongoClient, ASCENDING


class DatasetLoader(object):
    def __init__(self):
        self.dataset = {}
        self.mongo = MongoClient("192.168.0.101").airacing

    def load(self, track_id: int):
        control_data = []
        sensors_data = []

        for a in self.mongo.dataset.find({"file_name": f"{track_id}"}).sort(
                "datetime", ASCENDING
        ):
            d = a.copy()
            del d["_id"]
            control_data.append(d)

        for a in self.mongo.datalogger.find({'track_pk': track_id}).sort("heading_time", ASCENDING):
            d = a.copy()
            del d["_id"]
            sensors_data.append(d)

        for a in control_data:
            self.dataset[a["recording_frame_num"]] = a
            nearest = sensors_data[0]
            nearest_delta = a['datetime'] - nearest['heading_time']

            for b in sensors_data:
                if a['datetime'] < b['heading_time']:
                    break
                if a['datetime'] - b['heading_time'] < nearest_delta:
                    nearest_delta = a['datetime'] - b['heading_time']
                    #
                    nearest = b

            self.dataset[a["recording_frame_num"]].update(nearest)
        print(f"Loaded {len(self.dataset)}")

    def get_data(self, frame_num: int):
        return self.dataset.get(frame_num, None)

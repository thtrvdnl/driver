class Message(object):
    def __init__(self, throttle: int, steering: int, reverse: int):
        """
        :param throttle: 0-255
        :param steering: 0-255
        :param reverse: reverse or not
        """
        self.throttle = throttle
        self.steering = steering
        self.reverse = reverse

    def __str__(self):
        return f"throttle: {self.throttle: <5} steering: {self.steering: <5} reverse: {self.reverse: <5}"


class MessageSerializer(object):
    PACKET_LEN = 4

    @staticmethod
    def serialize(msg: Message):
        return bytes([msg.throttle, msg.steering, msg.reverse, 255])

    @staticmethod
    def deserialize(msg: bytes):
        if len(msg) != MessageSerializer.PACKET_LEN:
            return None
        if bytes([msg[-1]]) != bytes([255]):
            return None
        return Message(throttle=msg[0], steering=msg[1], reverse=msg[2])

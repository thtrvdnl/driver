from rudder_config.message import Message, MessageSerializer
from threading import Lock, Thread
import logging
import socket
import random
import time

logging.basicConfig(
    format="\033[94m[%(asctime)s][%(levelname)s]\033[0m %(message)s", level=logging.INFO
)


class SocketServer(Thread):
    def __init__(self, host, port):
        Thread.__init__(self)
        self.daemon = True

        self.host = host
        self.port = port
        self.socket = None
        self.mutex = Lock()
        self.connections = []
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.bind((self.host, self.port))

    def run(self):
        while True:
            self.socket.listen()
            conn, addr = self.socket.accept()
            logging.info(f"{conn} {addr}")
            self.connections.append(conn)

    def send(self, msg: Message):
        for c in self.connections.copy():
            try:
                serialized_msg = MessageSerializer.serialize(msg=msg)
                c.sendall(serialized_msg)
            except BrokenPipeError as e:
                logging.info(f"disconnected {c}")
                self.connections.remove(c)
            except ConnectionResetError as e:
                logging.info(f"disconnected {c}")
                self.connections.remove(c)


if __name__ == "__main__":
    ss = SocketServer(host="...", port=5000)
    ss.start()
    while True:
        message = Message(
            throttle=random.randint(0, 254),
            steering=random.randint(0, 254),
            reverse=random.randint(0, 1),
        )
        ss.send(msg=message)
        time.sleep(0.1)

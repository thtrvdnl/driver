#!/usr/bin/python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QGridLayout,
    QLineEdit,
    QApplication,
)
from multiprocessing import Value, Array
import requests
import logging
import sys

logging.basicConfig(format="%(process)d-%(levelname)s-%(message)s")


class MissionTag(QWidget):
    def __init__(self, throttle_level, tag_list, mission_329_327, mission_reverse, mission_327_329):
        super().__init__()
        self.mission_list = []
        self.mission_text = []
        self.mission_keras_list = ["Start: 329-327", "Reversal: 329-327", "Start: 327-329"]

        self._get_missiontags()
        self._get_robodrivers()

        self.throttle_level = throttle_level
        self.tag_list = tag_list

        self.mission_329_327 = mission_329_327
        self.mission_reverse = mission_reverse
        self.mission_327_329 = mission_327_329

        self._initUI()

    def _get_missiontags(self):
        """ Receives mission data from django. """
        r = requests.get(f"http://192.168.0.121:8899/api/missiontags")

        self.tag_pk = [i["pk"] for i in r.json()]
        self.tag_name = [i["name"] for i in r.json()]
        self.tag_description = [i["description"] for i in r.json()]

    def _get_robodrivers(self):
        """ Get all paths to model weights from django. """
        r = requests.get("http://192.168.0.121:8899/api/robodrivers")

        self.robodrivers_pk = [i["pk"] for i in r.json()]
        self.robodrivers_name = [i["name"] for i in r.json()]
        self.robodrivers_path_h5 = [i["h5_path"] for i in r.json()]

    def _initUI(self):
        """ Creates a form."""
        grid = QGridLayout()

        positions = [i for i in range(len(self.tag_pk))]

        self.text = QLabel("mission_tags:", self)
        grid.addWidget(self.text, 1, 1)
        # Button.
        for position, name in zip(positions, self.tag_description):
            button = QPushButton(name, self)
            button.setCheckable(True)
            button.clicked[bool].connect(self._set_text_mission)
            grid.addWidget(button, position + 2, 1)
        # Send mission tag
        button = QPushButton("send", self)
        button.clicked[bool].connect(self._set_mission_list)
        grid.addWidget(button, len(self.tag_pk) + 2, 1)

        # Send throttle level
        text_throttle = QLabel("Throttle level:", self)
        self.le = QLineEdit(self)
        grid.addWidget(text_throttle, 2, 2)
        grid.addWidget(self.le, 3, 2)

        button = QPushButton("send throttle", self)
        button.clicked[bool].connect(self._set_throttle)
        grid.addWidget(button, 4, 2)

        # Send mission list
        position_mission = [i for i in range(len(self.mission_keras_list))]
        for position, mission in zip(position_mission, self.mission_keras_list):
            button = QPushButton(mission, self)
            button.clicked.connect(self._set_mission_keras)
            grid.addWidget(button, position + 5, 3)

        # Send Robo Drivers
        positions_robodrivers = [i for i in range(len(self.robodrivers_name))]
        for position, robodriver_name in zip(positions_robodrivers, self.robodrivers_name):
            button = QPushButton(robodriver_name, self)
            button.clicked.connect(self._set_path_h5)
            grid.addWidget(button, position + 5, 4)

        self.setLayout(grid)

        self.setGeometry(300, 300, 580, 370)
        self.setWindowTitle("Toggle button")

        self.show()

    def _set_path_h5(self):
        """ Sets the path to the file h5. """
        source = self.sender()
        if source.text() == self.robodrivers_name[0]:

    def _set_mission_keras(self):
        """ Mission for keras. """
        source = self.sender()
        if source.text() == self.mission_keras_list[0]:
            with self.mission_329_327.get_lock():
                self.mission_329_327.value = 1
        elif source.text() == self.mission_keras_list[1]:
            with self.mission_reverse.get_lock():
                self.mission_reverse.value = 1
        elif source.text() == self.mission_keras_list[2]:
            with self.mission_327_329.get_lock():
                self.mission_327_329.value = 1

    def _set_throttle(self):
        with self.throttle_level.get_lock():
            self.throttle_level.value = float(self.le.text())

    def _set_mission_list(self):
        if not self.mission_list:
            logging.warning("--WARNING--List haven't tag.")
        else:
            tag_str = "-".join(self.mission_list)
            print(tag_str)
            logging.info(tag_str)
            self.tag_list.value = tag_str.encode("utf-8")

    def _set_text_mission(self, pressed: bool):
        source = self.sender()
        try:
            for i in range(len(self.tag_description)):
                if pressed and source.text() == self.tag_description[i]:
                    self.mission_text.append(self.tag_name[i])
                    self.mission_list.append(str(self.tag_pk[i]))
                    self.text.setText(f"mission_tags: {self.mission_text}")

                if not pressed and source.text() == self.tag_description[i]:
                    del self.mission_text[i]
                    del self.mission_list[i]
                    self.text.setText(f"mission_tags: {self.mission_text}")

        except IndexError as error:
            logging.error(error)
            self.mission_text.clear()
            self.mission_list.clear()
            self.text.setText(f"mission_tags: {self.mission_text}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = MissionTag()
    sys.exit(app.exec_())

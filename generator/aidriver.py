# from generator.frame_generator import data_generator
import frame_generator

import keras
from keras import backend as K
from keras.models import Sequential, Model
from keras.layers import Reshape, Dense, Flatten, LSTM, Activation, Dropout, BatchNormalization, Conv2D, MaxPooling2D, \
    AveragePooling2D, GlobalMaxPooling2D, LeakyReLU, ELU, Input, UpSampling2D, Concatenate
from keras import regularizers
from keras.constraints import max_norm
from keras.utils import Sequence

from keras.optimizers import Adam, Adamax, Adadelta, Adagrad, Nadam, SGD, RMSprop
from keras.callbacks import TensorBoard, ReduceLROnPlateau, EarlyStopping
from keras import losses, metrics
# from sklearn.preprocessing import MinMaxScaler
# import pandas_datareader.data as web
import datetime
import math
import numpy as np
import cv2

from keras.models import load_model


def make_model(DIMY=240, DIMX=320):
    global model
    reg = 0.0005
    reg2 = 0.000001

    input_layer = Input(shape=(DIMY, DIMX, 3,), name="main_input")
    start_layer = Conv2D(4, (3, 3))(input_layer)
    #  R=64
    #  R= 2 + 6  +:+  2 * 8  +:+  4 * 8  + 4 * 2=

    x = Conv2D(4, (3, 3), kernel_regularizer=regularizers.l2(reg / 10.0),
               activity_regularizer=regularizers.l2(reg2 / 10.0), padding='same')(start_layer)
    x = ELU()(x)
    x = MaxPooling2D(2)(x)
    #    x = Dropout(0.1)(x)
    x = Conv2D(8, (3, 3), kernel_regularizer=regularizers.l2(reg), activity_regularizer=regularizers.l2(reg2),
               padding='same')(x)
    x = ELU()(x)
    x = MaxPooling2D(2)(x)
    #    x = Dropout(0.1)(x)
    x = Conv2D(16, (3, 3), kernel_regularizer=regularizers.l2(reg), activity_regularizer=regularizers.l2(reg2),
               padding='same')(x)
    x = ELU()(x)
    x = MaxPooling2D(2)(x)
    x = Dropout(0.1)(x)
    x = Conv2D(16, (3, 3), kernel_regularizer=regularizers.l2(reg), activity_regularizer=regularizers.l2(reg2),
               padding='same')(x)
    x = ELU()(x)
    x = MaxPooling2D(2)(x)
    x = Dropout(0.1)(x)
    x = Conv2D(16, (3, 3), kernel_regularizer=regularizers.l2(reg), activity_regularizer=regularizers.l2(reg2),
               padding='same')(x)
    x = ELU()(x)
    mp = GlobalMaxPooling2D()(x)

    x = MaxPooling2D(2)(x)
    x = Conv2D(8, (3, 3), kernel_regularizer=regularizers.l2(reg), activity_regularizer=regularizers.l2(reg2))(x)

    x = Flatten()(x)
    x = Dropout(0.2)(x)
    x = Dense(8, kernel_regularizer=regularizers.l2(reg), activity_regularizer=regularizers.l2(reg2), )(x)
    x = ELU()(x)

    x = Concatenate()([mp, x])
    x = Dense(8, kernel_regularizer=regularizers.l2(reg), activity_regularizer=regularizers.l2(reg2), )(x)
    x = ELU()(x)
    x = Dense(2)(x)

    out_layer = Activation('tanh')(x)

    model = Model(inputs=[input_layer], outputs=[out_layer])

    return model


model = load_model("aidriver1.h5", compile=True)
model.load_weights("aidriver1.h5")


def run(frame):  # returns  (steer,throttle)
    global model
    frame = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA) * (1.0 / 255.0)
    cv2.imshow('frame', frame)
    cv2.waitKey(1)
    print(1111, model.predict(np.array([frame])))
    res = model.predict(np.array([frame]))[0]
    return (round(res[0] * 32.0 + 127), round(res[1] * 255.0))


def test():
    cv2.namedWindow('frame')
    cv2.waitKey(1)
    cap = cv2.VideoCapture("/mnt/share110/airacing_sample/131.mp4")
    while True:
        _, frame = cap.read()
        print(run(frame))


def train(tags, videos, modelfn='aidriver1.h5'):
    global model

    model = make_model()
    try:
        model = load_model(modelfn)
    except:
        print("can't load model ", modelfn)
        pass

    model.summary()
    model.compile(optimizer=Nadam(lr=0.001), loss='logcosh')
    ron = keras.callbacks.ReduceLROnPlateau(monitor='loss', factor=0.4, patience=2, verbose=1, cooldown=3,
                                            min_lr=0.00001)

    for t in range(0, 3):
        model.fit_generator(frame_generator.data_generator(tags, videos), epochs=15, steps_per_epoch=100,
                            validation_steps=0, shuffle=True, use_multiprocessing=True, workers=8, callbacks=[ron])
        model.save(modelfn)


if __name__ == "__main__":
    train([6], [166, 168, 170, 172, 174, 184, 186, 187, 188, 189], "327-329.h5")  # 6 - forward,  7 - backward

from __future__ import print_function

# ==============================================================================
# -- find carla module ---------------------------------------------------------
# ==============================================================================


import glob
import os
import sys

# Important! Find correct eggs
import time

try:
    sys.path.append('carla/dist/carla-0.9.11-py3.7-linux-x86_64.egg')
    # sys.path.append('../carla/dist/carla-*%d.%d-%s.egg' % (
    #     sys.version_info.major,
    #     sys.version_info.minor,
    #     'win-amd64' if os.name == 'nt' else 'linux-x86_64'))
except IndexError:
    pass

# ==============================================================================
# -- imports -------------------------------------------------------------------
# ==============================================================================


import carla
import random as rd
import time
import numpy as np
import cv2
import math

IMG_WIDTH = 640
IMG_HEIGHT = 480
SHOW_PREVIEW = False


class CarEnv:
    SHOW_CAM = SHOW_PREVIEW
    STEER_AMT = 1.0

    im_width = IMG_WIDTH
    im_height = IMG_HEIGHT
    actor_list = []

    front_camera = None
    collision_hist = []

    def __init__(self):
        self.client = carla.Client('localhost', 2000)
        self.client.set_timeout(2.0)

        # Once we have a client we can retrieve the world that is currently
        # running.
        self.world = self.client.get_world()

        world = self.client.load_world('Town04')
        # world = self.client.load_world('Town05_Opt')

        # The world contains the list blueprints that we can use for adding new
        # actors into the simulation.
        blueprint_library = self.world.get_blueprint_library()

        # Now let's filter all the blueprints of type 'vehicle' and choose one
        # at random.
        # print(blueprint_library.filter('vehicle'))
        self.model_3 = blueprint_library.filter('model3')[0]

    def reset(self):
        self.collision_hist = []
        self.actor_list = []

        self.transform = rd.choice(self.world.get_map().get_spawn_points())
        self.vehicle = self.world.spawn_actor(self.model_3, self.transform)
        self.actor_list.append(self.vehicle)

        self.rgb_cam = self.world.get_blueprint_library().find('sensor.camera.rgb')

        self.rgb_cam.set_attribute('image_size_x', f'{self.im_width}')
        self.rgb_cam.set_attribute('image_size_y', f'{self.im_height}')
        self.rgb_cam.set_attribute('fov', '110')

        transform = carla.Transform(carla.Location(x=2.5, z=0.7))

        self.sensor = self.world.spawn_actor(self.rgb_cam, transform, attach_to=self.vehicle)

        self.actor_list.append(self.sensor)
        self.sensor.listen(lambda data: self.process_img(data))
        self.vehicle.apply_control(carla.VehicleControl(throttle=0.0,
                                                        brake=0.0)) # initially passing some commands seems to help with time. Not sure why.
        time.sleep(4)  # sleep to get things started and to not detect a collision when the car spawns/falls from sky.

        colsensor = self.world.get_blueprint_library().find('sensor.other.collision')
        self.colsensor = self.world.spawn_actor(colsensor, transform, attach_to=self.vehicle)
        self.actor_list.append(self.colsensor)
        self.colsensor.listen(lambda event: self.collision_data(event))
        while self.front_camera is None:
            time.sleep(0.01)
        self.episode_start = time.time()

        self.vehicle.apply_control(carla.VehicleControl(brake=0.0, throttle=0.0))

        return self.front_camera

    def collision_data(self, event):
        self.collision_hist.append(event)

    def process_img(self, image):
        i = np.array(image.raw_data)
        # np.save("iout.npy", i)
        i2 = i.reshape((self.im_height, self.im_width, 4))
        i3 = i2[:, :, :3]
        if self.SHOW_CAM:
            cv2.imshow("", i3)
            cv2.waitKey(1)
        self.front_camera = i3

    def make_step(self, throttle, steer):
        self.vehicle.apply_control(carla.VehicleControl(throttle=throttle * 1.0, steer=steer * self.STEER_AMT))

    # def step(self, action):
    #     '''
    #     For now let's just pass steer left, center, right?
    #     0, 1, 2
    #     '''
    #     if action == 0:
    #         self.vehicle.apply_control(carla.VehicleControl(throttle=1.0, steer=0))
    #     if action == 1:
    #         self.vehicle.apply_control(carla.VehicleControl(throttle=1.0, steer=-1*self.STEER_AMT))
    #     if action == 2:
    #         self.vehicle.apply_control(carla.VehicleControl(throttle=1.0, steer=1*self.STEER_AMT))
    #
    #     v = self.vehicle.get_velocity()
    #     kmh = int(3.6 * math.sqrt(v.x**2 + v.y**2 + v.z**2))
    #
    #     done = False
    #
    #     if len(self.collision_hist) != 0:
    #         done = True
    #         reward = -200
    #     elif kmh < 50:
    #         reward = -1
    #     else:
    #         reward = 1
    #
    #
    #     return self.front_camera, reward, done, None

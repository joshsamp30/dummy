"""Scene 3: Washington Avenue loft district at street level, Eads Bridge at the end of the street."""
import math
import os
import random

import bpy
from mathutils import Vector

from . import actors as A
from . import common as C
from . import landmarks as L
from . import streets as S
from .common import PAL, box, pbr, smooth, smoother, lerp

Y = L.EADS_Y            # Washington Avenue runs straight onto the Eads Bridge deck
ROAD_W, WALK_W = 16.0, 6.5
LOGO = os.path.join(C.ASSETS, "localhowl_logo_navy.png")


class Washington:
    def __init__(self, scene, duration=16.0, seed=4):
        self.scene = scene
        rnd = random.Random(seed)
        coll = scene.collection
        sun = Vector((-0.55, -0.60, 0.40)).normalized()      # late afternoon, raking down the street wall
        C.make_world(scene, (0.92, 0.74, 0.62), (0.52, 0.66, 0.84), (0.12, 0.30, 0.66), strength=1.0, cloud=0.45,
                     cloud_col=(1.0, 0.93, 0.85), cloud_dark=(0.55, 0.58, 0.70), sun_dir=sun, sun_glow=(1.0, 0.8, 0.55), seed=7.0)
        C.make_sun(scene, sun, (1.0, 0.86, 0.68), 4.0, angle=1.5)
        scene.view_settings.exposure = -0.3
        box("ground", (5000, 5000, 0.5), (-800, Y, -0.7), C.ground_mat("CityGround", (0.13, 0.13, 0.135), (0.2, 0.2, 0.2), scale=0.02), coll=coll)
        x0, x1 = -1560.0, -250.0
        S.street(x0, x1, Y, ROAD_W, WALK_W, coll=coll, lamps=0.0, lamp_gap=22.0, rnd=rnd)
        # the district's signature "zipper" paving strip down the centre line
        for k in range(int((x1 - x0) / 3.0)):
            box("zipper", (1.2, 0.5, 0.012), (x0 + k * 3.0, Y + (0.35 if k % 2 else -0.35), 0.003),
                pbr("Zipper", (0.55, 0.52, 0.46), 0.5), coll=coll)
        # loft buildings: tall brick and terracotta warehouses, 7-12 storeys, shops at street level
        walls = ["brick", "darkbrick", "buff", "terracotta", "brick", "cream", "darkbrick", "buff"]
        awn = [None, "navy", "red", None, "teal", "cream", None, "pink"]
        self.fronts = []
        for facing, yy in ((-1, Y + ROAD_W / 2 + WALK_W), (1, Y - ROAD_W / 2 - WALK_W)):
            x = x0 + 10
            i = 0
            while x < -700:
                w = rnd.choice([34, 40, 46, 52, 58])
                if (x + w) % 110 < 14:      # cross streets every block
                    x += 16
                h = rnd.choice([30, 34, 38, 42, 46, 50])
                S.storefront(x + w / 2, yy, w, 40, h, facing, wall=walls[(i + (facing > 0) * 3) % len(walls)],
                             awning=awn[(i * 3 + (facing > 0)) % len(awn)], lit=0.05, coll=coll, seed=i * 7 + (facing > 0),
                             shop_glow=(1.0, 0.78, 0.55), glow=2.2)
                x += w
                i += 1
        # east end: the convention centre, towers, then the bridge
        F = C.facade_mat
        glassy = F("FBlueGlass", (0.16, 0.22, 0.27), (0.03, 0.07, 0.11), bay=1.5, floor=3.9, win_w=0.88, win_h=0.8, wall_rough=0.25, seed=4, metal_glass=0.7)
        pale = F("FPale", (0.66, 0.64, 0.58), (0.03, 0.04, 0.06), bay=2.0, floor=3.9, win_w=0.45, win_h=0.6, seed=3)
        box("ConventionCenter", (260, 110, 26), (-560, Y + ROAD_W / 2 + WALK_W + 55, 0), pale, coll=coll)
        box("SixHundredWash", (44, 38, 114), (-565, Y - ROAD_W / 2 - WALK_W - 19, 0), glassy, coll=coll)
        box("OneFinancial", (60, 44, 52), (-470, Y - ROAD_W / 2 - WALK_W - 22, 0), glassy, coll=coll)
        box("Marriott", (70, 36, 78), (-650, Y - ROAD_W / 2 - WALK_W - 18, 0), pale, coll=coll)
        box("Hotel_N", (50, 40, 60), (-360, Y + ROAD_W / 2 + WALK_W + 20, 0), pale, coll=coll)
        self.eads = L.eads_bridge(coll=coll, simple=False)
        # ground east of 3rd Street drops to the river
        box("river", (2400, 5000, 0.2), (1300, Y, L.WATER_Z), C.water_mat("River", color=(0.06, 0.05, 0.034), rough=0.05), coll=coll)
        self.arch = L.gateway_arch(coll)
        C.haze_box("Haze", (-2500, -1500, -24), (1500, 2500, 400), density=0.0003, color=(0.95, 0.9, 0.85), aniso=0.5)
        # --- life ---
        self.walkers, self.idlers = [], []
        S.sidewalk_crowd(self, rnd, -1400, -900, Y, ROAD_W, WALK_W, 34, duration, coll=coll)
        # the Local Howl food truck at the kerb with a queue
        self.truck, self.cook = A.food_truck((-1170, Y - ROAD_W / 2 + 1.3, 0), 0.0, coll=coll, logo=LOGO)
        for k in range(6):
            w = A.Wolf(rnd, coll=coll)
            w.place((-1171 + rnd.uniform(-0.3, 0.3) - k * 0.0, Y - ROAD_W / 2 - 1.2 - k * 0.95, 0.14), math.pi / 2 + rnd.uniform(-0.2, 0.2))
            self.idlers.append((w, 0.3))
        # traffic: a signal at the cross street holds eastbound cars, then releases them
        S.crosswalk(-1128, Y, ROAD_W, coll=coll)
        self.sig = S.signal(-1124, Y - ROAD_W / 2 - 0.6, coll=coll)
        self.red = lambda t: t < 7.5       # noqa: E731
        self.lanes = []
        east = C.Path([(-1560, Y - 2.4, 0.0), (-250, Y - 2.4, 0.0)])
        cars = [A.Car(rnd, coll=coll) for _ in range(6)]
        self.lanes.append(A.Lane(east, cars, [395, 372, 350, 300, 240, 170], v0=10.0, stop_s=-1131 + 1560,
                                 signal=self.red, duration=duration + 2))
        west = C.Path([(-250, Y + 2.4, 0.0), (-1560, Y + 2.4, 0.0)])
        cars = [A.Car(rnd, coll=coll) for _ in range(5)]
        self.lanes.append(A.Lane(west, cars, [1010, 930, 800, 640, 500], v0=10.0, stop_s=1560 - 250 - 430 - 6,
                                 signal=self.red, duration=duration + 2))
        # wolves cross on the zebra while the light is red
        cross = C.Path([(-1128, Y - ROAD_W / 2 - 2, 0.02), (-1128, Y + ROAD_W / 2 + 2, 0.02)])
        for k in range(7):
            d = 1 if k % 2 else -1
            self.walkers.append(A.Walker(A.Wolf(rnd, coll=coll), cross, rnd.uniform(0, 5) if d > 0 else cross.length - rnd.uniform(0, 5),
                                         rnd.uniform(1.2, 1.6), rnd.uniform(-1.2, 1.2), (), d, loop=False))
        self.train = A.Train(coll=coll)

    def update(self, t):
        for w in self.walkers:
            w.update(t)
        for w, g in self.idlers:
            w.idle(t, gesture=g)
        self.cook.idle(t, gesture=1.0)
        for ln in self.lanes:
            ln.update(t)
        S.set_signal(self.sig, self.red(t))
        e = self.eads
        self.train.place((e["x0"] + 20 + 15.0 * t, e["y"], e["rail_z"]), 0.0)


def shot3(scene):
    """Crane down onto Washington Avenue, then a slow push east toward the bridge."""
    w = Washington(scene, duration=16.0)
    cam = C.make_camera(scene, lens=35.0)

    def frame(t):
        w.update(t)
        u = smoother(t / 16.0)
        d = smooth(min(1.0, t / 9.0))
        pos = Vector((lerp(-1265, -1205, u), Y + lerp(-3.0, -5.6, d), lerp(30.0, 2.1, d)))
        tgt = Vector((pos.x + 200, Y + lerp(0.0, 1.5, d), lerp(8.0, 4.2, d)))
        cam.data.lens = lerp(30.0, 40.0, u)
        C.look_at(cam, pos, tgt)
    return frame, 16.0

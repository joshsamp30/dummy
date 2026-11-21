"""Character and vehicle line-up: quick look-dev check."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from stl import actors as A  # noqa: E402
from stl import common as C  # noqa: E402

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/lineup.jpg"
scene = C.reset()
C.setup_render(scene, 1280, 720, samples=32)
C.make_world(scene, (0.95, 0.62, 0.5), (0.55, 0.62, 0.8), (0.2, 0.35, 0.7), strength=1.0,
             sun_dir=(1, -1, 0.5), sun_glow=(1, 0.8, 0.5))
C.make_sun(scene, (1, -1, 0.7), strength=3.0)
C.box("ground", (200, 200, 1), (0, 0, -1), C.pbr("G", C.PAL["blush"], 0.8))
rnd = random.Random(3)
for i in range(7):
    w = A.Wolf(rnd, fur=i % 5)
    w.place((i * 0.95 - 3, 0, 0), -math.pi / 2 + (0.5 if i % 2 else 0))
    w.walk(i * 0.37, 1.0)
p = A.Pup(rnd)
p.place((4, 0.5, 0), -math.pi / 2)
p.walk(0.3, 0, speed=3)
q = A.Quad(rnd)
q.place((5, 0, 0), -math.pi / 2 + 0.6)
q.walk(0.2, 0)
cy = A.Cyclist(rnd)
cy.place((-5, 0, 0), -0.4)
cy.ride(1.0, 0)
car = A.Car(rnd, "sedan", "pink")
car.place((-4, 5, 0), 0.3)
car2 = A.Car(rnd, "suv", "teal")
car2.place((2, 5, 0), -0.2)
A.food_truck((8, 6, 0), math.pi, logo=os.path.join(C.ASSETS, "localhowl_logo_navy.png"))
cam = C.make_camera(scene, lens=40)
C.look_at(cam, (0.5, -11, 2.2), (0.5, 0, 1.1))
scene.render.filepath = out
import bpy  # noqa: E402
bpy.ops.render.render(write_still=True)

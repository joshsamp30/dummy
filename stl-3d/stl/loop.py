"""Scene 4: the Delmar Loop at dusk.

Delmar Blvd runs east-west. Blueberry Hill (6504 Delmar) is on the south side;
The Pageant (6161) and the Moonrise Hotel (6177) are on the north side about
520 m further east. The two blocks keep their real separation, so the scene
plays as two slow moves joined by a dissolve rather than moving a landmark.
"""
import math
import os
import random

import bpy
from mathutils import Vector

from . import actors as A
from . import common as C
from . import streets as S
from .common import PAL, box, cyl, new_obj, pbr, smooth, smoother, lerp

ROAD_W, WALK_W = 15.0, 5.0
BH_X = -260.0            # Blueberry Hill block
PG_X = 260.0             # Pageant / Moonrise block
N_LINE = ROAD_W / 2 + WALK_W        # frontage lines
S_LINE = -(ROAD_W / 2 + WALK_W)


class Loop:
    def __init__(self, scene, duration=20.0, seed=9):
        self.scene = scene
        rnd = random.Random(seed)
        coll = scene.collection
        sun = Vector((-0.95, 0.2, -0.04)).normalized()        # just set, glow in the west
        C.make_world(scene, (0.95, 0.38, 0.22), (0.42, 0.20, 0.46), (0.03, 0.05, 0.20), strength=0.28, cloud=0.5,
                     cloud_col=(1.0, 0.42, 0.34), cloud_dark=(0.16, 0.10, 0.22), sun_dir=sun, sun_glow=(1.0, 0.4, 0.15),
                     glow_power=12.0, glow_strength=1.2, seed=5.0, stars=0.6)
        scene.view_settings.exposure = -0.2
        box("ground", (3000, 2000, 0.5), (0, 0, -0.7), pbr("LoopGround", (0.05, 0.05, 0.055), 0.8), coll=coll)
        S.street(-560, 560, 0.0, ROAD_W, WALK_W, coll=coll, wet=0.75, lamps=8.0, lamp_gap=20.0, rnd=rnd, tracks=True, stars=True)
        self.walkers, self.idlers, self.lanes = [], [], []
        self._blueberry_block(coll, rnd)
        self._pageant_block(coll, rnd)
        self._infill(coll, rnd)
        C.haze_box("Haze", (-800, -400, -1), (800, 400, 120), density=0.0022, color=(0.9, 0.75, 0.8), aniso=0.6)
        # --- life: busy sidewalks, cruising traffic ---
        S.sidewalk_crowd(self, rnd, BH_X - 90, BH_X + 90, 0.0, ROAD_W, WALK_W, 30, duration, coll=coll)
        S.sidewalk_crowd(self, rnd, PG_X - 90, PG_X + 90, 0.0, ROAD_W, WALK_W, 30, duration, coll=coll)
        for d, yy in ((1, -2.3), (-1, 2.3)):
            pts = [(-560 * d, yy, 0), (560 * d, yy, 0)]
            cars = [A.Car(rnd, coll=coll, lights=1.0) for _ in range(9)]
            starts = [60 + k * rnd.uniform(48, 70) for k in range(9)][::-1]
            self.lanes.append(A.Lane(C.Path(pts), cars, starts, v0=7.0, duration=duration + 2))
        # parked cars along both kerbs
        for sgn in (1, -1):
            for xx in list(range(int(BH_X) - 80, int(BH_X) + 81, 13)) + list(range(int(PG_X) - 80, int(PG_X) + 81, 13)):
                cam_side = (sgn > 0 and xx < 0) or (sgn < 0 and xx > 0)     # keep the camera kerbs clear
                if rnd.random() < 0.7 and not cam_side:
                    c = A.Car(rnd, coll=coll)
                    c.place((xx + rnd.uniform(-1, 1), sgn * (ROAD_W / 2 - 1.15), 0), 0 if sgn < 0 else math.pi)

    # ------------------------------------------------------------------
    def _blueberry_block(self, coll, rnd):
        """South side: Blueberry Hill's long two-storey brick front, green awnings, neon in every window."""
        x = BH_X
        S.storefront(x, S_LINE, 46, 30, 9.5, 1, wall="brick", sign="Blueberry Hill", sign_color="blue", awning="teal",
                     lit=0.7, coll=coll, seed=3, floors=1, shop_glow=(1.0, 0.62, 0.30), glow=3.0, name="BlueberryHill",
                     sign_size=1.25, blade="BLUEBERRY", blade_color="red")
        # window neon: the bar's collection of beer signs and memorabilia
        cols = ["red", "blue", "green", "yellow", "pink", "cyan", "orange", "violet"]
        for k in range(16):
            xx = x - 21 + k * 2.8
            col = cols[k % len(cols)]
            m = C.emissive("Neon_%s_45" % col, S.NEON[col], 45.0)
            if k % 3 == 0:
                new_obj("win_neon", C.m_torus(0.33, 0.035, 20, 6), m, (xx, S_LINE + 0.25, 2.5), coll=coll)
            elif k % 3 == 1:
                box("win_neon", (1.1, 0.06, 0.09), (xx, S_LINE + 0.25, 2.6), m, coll=coll)
                box("win_neon", (0.8, 0.06, 0.09), (xx, S_LINE + 0.25, 2.25), m, coll=coll)
            else:
                S.text("win_neon", "OPEN", 0.36, (xx, S_LINE + 0.28, 2.4), (math.pi / 2, 0, math.pi), m, coll=coll)
        # music spilling from the open door: warm light pool and a knot of wolves outside
        ld = bpy.data.lights.new("doorglow", "AREA")
        ld.energy = 2600
        ld.color = (1.0, 0.55, 0.25)
        ld.size = 2.4
        lo = bpy.data.objects.new("doorglow", ld)
        lo.location = (x + 6, S_LINE + 0.4, 2.6)
        lo.rotation_euler = (math.radians(-65), 0, 0)
        C.link(lo, coll)
        for k in range(7):
            w = A.Wolf(rnd, coll=coll)
            a = rnd.uniform(0, 6.28)
            w.place((x + 6 + math.cos(a) * rnd.uniform(0.8, 2.6), S_LINE + 2.2 + math.sin(a) * 1.2, 0.14), a + math.pi)
            self.idlers.append((w, 0.9))
        # neighbours on the block and across the street
        specs_s = [(-58, 22, 11, "buff", "RECORDS", "pink", "red"), (-34, 20, 13, "cream", "PIZZA", "red", None),
                   (36, 22, 12, "darkbrick", "BOOKS", "cyan", "navy"), (60, 24, 14, "buff", "TACOS", "yellow", "pink")]
        for dx, w, h, wall, sign, col, awn in specs_s:
            S.storefront(x + dx + (0 if abs(dx) > 30 else 0), S_LINE, w, 26, h, 1, wall=wall, sign=sign, sign_color=col,
                         awning=awn, lit=0.6, coll=coll, seed=int(dx) + 80, glow=2.5)
        specs_n = [(-62, 26, 12, "brick", "ROOT BEER", "orange", "red"), (-34, 28, 14, "cream", "VINYL", "violet", None),
                   (-4, 30, 11, "darkbrick", "DINER", "pink", "teal"), (28, 30, 16, "buff", "CINEMA", "yellow", None),
                   (60, 30, 12, "brick", "THAI", "green", "yellow")]
        for dx, w, h, wall, sign, col, awn in specs_n:
            S.storefront(x + dx, N_LINE, w, 26, h, -1, wall=wall, sign=sign, sign_color=col, awning=awn, lit=0.6,
                         coll=coll, seed=int(dx) + 200, glow=2.5)

    # ------------------------------------------------------------------
    def _pageant_block(self, coll, rnd):
        """North side: The Pageant's marquee and the Moonrise Hotel with its rooftop moon."""
        x = PG_X
        # The Pageant: broad concert hall, wraparound marquee with chaser bulbs, vertical blade sign
        hall = pbr("PageantWall", (0.34, 0.25, 0.20), 0.7)
        box("Pageant", (62, 46, 15), (x + 22, N_LINE + 23, 0), hall, coll=coll)
        box("Pageant_tower", (9, 9, 22), (x - 5, N_LINE + 4.5, 0), hall, coll=coll)
        marq = pbr("Marquee", (0.03, 0.03, 0.035), 0.4)
        box("marquee", (30, 4.2, 2.4), (x + 14, N_LINE - 2.1, 4.2), marq, coll=coll)
        face = C.emissive("MarqueeFace", (1.0, 0.93, 0.80), 4.0)
        box("marquee_face", (28, 0.1, 1.5), (x + 14, N_LINE - 4.25, 4.65), face, coll=coll)
        S.text("marquee_txt", "TONIGHT   THE LOCAL HOWL PACK   LIVE", 0.72, (x + 14, N_LINE - 4.32, 5.4),
               (math.pi / 2, 0, 0), pbr("MarqueeInk", (0.01, 0.01, 0.01), 0.6), coll=coll, extrude=0.01)
        self.bulbs = []
        for k in range(46):
            for z in (4.3, 6.5):
                on = C.emissive("Bulb%d" % (k % 3), (1.0, 0.72, 0.30), 60.0)
                b = new_obj("bulb", C.m_sphere(6, 4), on, (x - 0.6 + k * 0.65, N_LINE - 4.3, z), scale=(0.09,) * 3, coll=coll)
        under = bpy.data.lights.new("marquee_under", "AREA")
        under.energy = 5200
        under.color = (1.0, 0.82, 0.55)
        under.size = 20
        under.size_y = 3
        under.shape = "RECTANGLE"
        uo = bpy.data.objects.new("marquee_under", under)
        uo.location = (x + 14, N_LINE - 2.1, 4.1)
        C.link(uo, coll)
        S.neon_sign("THE PAGEANT", 1.9, (x + 14, N_LINE - 4.3, 9.6), "red", strength=40.0, facing=-1, coll=coll)
        S.neon_sign("PAGEANT", 1.5, (x - 5, N_LINE - 0.1, 21.0), "yellow", strength=40.0, facing=-1, coll=coll, vertical=True)
        box("Pageant_doors", (16, 0.2, 3.2), (x + 14, N_LINE + 0.02, 0.2), C.emissive("LobbyGlow", (1.0, 0.7, 0.42), 3.0), coll=coll)
        for k in range(12):      # the queue under the marquee
            w = A.Wolf(rnd, coll=coll)
            w.place((x + 4 + k * 1.6 + rnd.uniform(-0.3, 0.3), N_LINE - 1.4 + rnd.uniform(-0.5, 0.5), 0.14),
                    rnd.choice((0.0, math.pi, -math.pi / 2)) + rnd.uniform(-0.4, 0.4))
            self.idlers.append((w, rnd.uniform(0.2, 1.0)))
        # Moonrise Hotel: eight storeys, colour-washed facade, the big rotating moon on the roof
        hx = x - 40
        hotel = C.facade_mat("FMoonrise", (0.30, 0.31, 0.34), (0.03, 0.04, 0.06), bay=3.3, floor=3.5, win_w=0.72, win_h=0.62,
                             lit=0.55, lit_col=(1.0, 0.78, 0.5), lit_strength=5.0, seed=13, base=4.8, metal_glass=0.4)
        box("MoonriseHotel", (38, 30, 33), (hx, N_LINE + 15, 0), hotel, coll=coll)
        wash = C.emissive("MoonriseWash", (0.25, 0.20, 1.0), 6.0)
        for k in range(5):
            box("moonrise_fin", (0.5, 0.5, 28), (hx - 16 + k * 8, N_LINE - 0.2, 4.8), wash, coll=coll)
        box("moonrise_lobby", (30, 0.2, 3.6), (hx, N_LINE + 0.02, 0.3), C.emissive("LobbyGlow2", (1.0, 0.8, 0.6), 3.0), coll=coll)
        box("moonrise_canopy", (14, 3.2, 0.3), (hx, N_LINE - 1.6, 4.0), pbr("Canopy", (0.75, 0.75, 0.76), 0.25, 0.9), coll=coll)
        S.neon_sign("MOONRISE HOTEL", 1.25, (hx, N_LINE - 0.1, 6.2), "white", strength=30.0, facing=-1, coll=coll)
        box("moon_mast", (0.6, 0.6, 5.0), (hx + 9, N_LINE + 8, 33), pbr("Mast", (0.3, 0.3, 0.32), 0.4, 0.8), coll=coll)
        mm, nb, out = C.new_mat("Moon")
        em = nb.new("ShaderNodeEmission")
        tc = nb.new("ShaderNodeTexCoord")
        n = nb.noise(tc.outputs["Object"], scale=2.2, detail=6.0, rough=0.6)[0]
        nb.l.new(nb.ramp(n, [(0.35, (0.35, 0.36, 0.42)), (0.7, (1.0, 0.96, 0.85))]), em.inputs[0])
        em.inputs[1].default_value = 7.0
        nb.l.new(em.outputs[0], out.inputs[0])
        self.moon = new_obj("Moon", C.m_sphere(32, 16), mm, (hx + 9, N_LINE + 8, 41.5), scale=(4.2,) * 3, coll=coll)
        # rooftop bar glow
        box("rooftop_bar", (20, 12, 3), (hx - 6, N_LINE + 10, 33), C.emissive("RoofBar", (1.0, 0.5, 0.7), 3.0), coll=coll)
        # the rest of the block and the south side opposite
        S.storefront(hx - 34, N_LINE, 26, 28, 9, -1, wall="darkbrick", sign="BOWL", sign_color="pink", lit=0.6, coll=coll,
                     seed=41, glow=3.0, blade="BOWLING", blade_color="cyan")
        S.storefront(x + 70, N_LINE, 28, 28, 12, -1, wall="brick", sign="BAR", sign_color="green", awning="navy", lit=0.6, coll=coll, seed=42, glow=2.5)
        specs_s = [(-70, 26, 12, "buff", "COFFEE", "yellow", "teal"), (-42, 26, 15, "brick", "GALLERY", "white", None),
                   (-14, 26, 11, "cream", "RAMEN", "red", "red"), (14, 26, 13, "darkbrick", "COMICS", "cyan", None),
                   (42, 26, 16, "buff", "BBQ", "orange", "navy"), (70, 26, 12, "brick", "ICE CREAM", "pink", "pink")]
        for dx, w, h, wall, sign, col, awn in specs_s:
            S.storefront(x + dx, S_LINE, w, 26, h, 1, wall=wall, sign=sign, sign_color=col, awning=awn, lit=0.6,
                         coll=coll, seed=int(dx) + 300, glow=2.5)

    def _infill(self, coll, rnd):
        """Low brick blocks between and beyond the two hero blocks so the street reads continuous."""
        walls = ["brick", "buff", "darkbrick", "cream"]
        for facing, line in ((-1, N_LINE), (1, S_LINE)):
            x = -550
            i = 0
            while x < 550:
                w = rnd.choice([20, 24, 28])
                cx = x + w / 2
                if not (BH_X - 76 < cx < BH_X + 76 or PG_X - 90 < cx < PG_X + 90):
                    S.storefront(cx, line, w, 24, rnd.choice([9, 11, 13, 15]), facing, wall=walls[i % 4], lit=0.5,
                                 coll=coll, seed=500 + i + (facing > 0) * 50, glow=1.5)
                x += w
                i += 1

    def update(self, t):
        for w in self.walkers:
            w.update(t)
        for w, g in self.idlers:
            w.idle(t, gesture=g)
        for ln in self.lanes:
            ln.update(t)
        self.moon.rotation_euler = (0.3, 0, t * 0.35)


def shot4(scene):
    """Two slow moves: Blueberry Hill and the Walk of Fame, then the Pageant and the Moonrise."""
    w = Loop(scene, duration=20.0)
    cam = C.make_camera(scene, lens=30.0)

    def frame(t):
        w.update(t)
        if t < 10.0:
            u = smooth(t / 10.0)
            # low over the Walk of Fame stars, pushing toward Blueberry Hill's neon windows
            pos = Vector((lerp(BH_X - 38, BH_X - 16, u), lerp(N_LINE - 2.6, N_LINE - 3.4, u), lerp(0.9, 1.9, u)))
            tgt = Vector((BH_X + 6, S_LINE, lerp(3.4, 4.2, u)))
            cam.data.lens = lerp(26.0, 30.0, u)
        else:
            u = smooth((t - 10.0) / 10.0)
            # from the south kerb, rising gently to take in the marquee and the moon
            pos = Vector((lerp(PG_X + 52, PG_X + 30, u), lerp(S_LINE + 2.2, S_LINE + 3.0, u), lerp(1.7, 3.2, u)))
            tgt = Vector((lerp(PG_X - 8, PG_X - 14, u), N_LINE + 4, lerp(10.0, 14.0, u)))
            cam.data.lens = lerp(22.0, 25.0, u)
        C.look_at(cam, pos, tgt)
    return frame, 20.0

"""Riverfront set: Gateway Arch grounds, Mississippi, Old Courthouse, skyline.

Used by scene 1 (dawn), scene 2 (Arch grounds) and scene 5 (golden-hour finale).
"""
import math
import os
import random

import bpy
from mathutils import Vector

from . import actors as A
from . import common as C
from . import landmarks as L
from .common import PAL, box, cyl, new_obj, pbr, smooth, smoother, lerp

MOODS = {
    # sky colours are art-directed toward the Local Howl pastel palette
    "dawn": dict(horizon=(1.0, 0.50, 0.34), mid=(0.80, 0.44, 0.52), zenith=(0.16, 0.22, 0.46), sky=0.55,
                 cloud=0.50, cloud_col=(1.0, 0.55, 0.45), cloud_dark=(0.30, 0.22, 0.36),
                 sun=(0.96, -0.25, 0.035), sun_col=(1.0, 0.55, 0.32), sun_power=1.1, glow=(1.0, 0.45, 0.2),
                 lit=0.10, lamps=3.0, mist=0.012, haze=0.00045, exposure=0.35),
    "day": dict(horizon=(0.86, 0.80, 0.78), mid=(0.50, 0.68, 0.86), zenith=(0.10, 0.30, 0.66), sky=1.0,
                cloud=0.42, cloud_col=(1.0, 0.97, 0.93), cloud_dark=(0.60, 0.64, 0.74),
                sun=(0.55, -0.62, 0.52), sun_col=(1.0, 0.93, 0.82), sun_power=4.2, glow=(1.0, 0.9, 0.7),
                lit=0.0, lamps=0.0, mist=0.0, haze=0.00022, exposure=-0.35),
    "sunset": dict(horizon=(1.0, 0.46, 0.16), mid=(0.90, 0.46, 0.44), zenith=(0.14, 0.20, 0.48), sky=0.75,
                   cloud=0.52, cloud_col=(1.0, 0.50, 0.30), cloud_dark=(0.34, 0.22, 0.34),
                   sun=(-0.93, -0.33, 0.075), sun_col=(1.0, 0.50, 0.20), sun_power=2.6, glow=(1.0, 0.42, 0.12),
                   lit=0.25, lamps=4.0, mist=0.0, haze=0.0004, exposure=0.1),
}


def _terrain(coll):
    """West bank cross-section extruded along the river, river bed, east bank."""
    grass = C.ground_mat("Lawn", (0.045, 0.14, 0.03), (0.09, 0.22, 0.05), scale=0.03, rough=0.95, bump=0.15)
    cobble = C.ground_mat("Cobble", (0.20, 0.19, 0.18), (0.10, 0.10, 0.10), scale=1.2, rough=0.8, bump=0.7)
    city = C.ground_mat("CityGround", (0.13, 0.13, 0.135), (0.20, 0.20, 0.20), scale=0.02, rough=0.85, bump=0.1)
    y0, y1 = -3200.0, 3200.0
    prof = [(-290.0, 0.0), (58.0, 0.0), (150.0, -15.0), (178.0, -15.0), (205.0, -23.5)]
    verts, faces = [], []
    for x, z in prof:
        verts += [(x, y0, z), (x, y1, z)]
    for i in range(len(prof) - 1):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    new_obj("WestBank", C.mesh_from("WestBank", verts, faces), grass, coll=coll)
    new_obj("Levee", C.m_plane(), cobble, ((178 + 205) / 2, 0, -19.2), scale=(27.6, y1 - y0, 1), coll=coll).rotation_euler = (0, math.atan2(8.5, 27), 0)
    box("LKSBlvd", (22, y1 - y0, 0.1), (164, 0, -15.0), pbr("Asphalt", (0.045, 0.045, 0.05), 0.75), coll=coll)
    box("Trail", (4.0, y1 - y0, 0.12), (175.5, 0, -15.0), pbr("TrailConc", (0.48, 0.46, 0.42), 0.8), coll=coll)
    box("City", (3400, y1 - y0, 0.5), (-290 - 1700, 0, -0.5), city, coll=coll)
    # Illinois side: low floodplain behind a grassy levee
    ev = []
    for x, z in [(L.SHORE_E - 12, -23.5), (L.SHORE_E + 14, -14.0), (L.SHORE_E + 60, -14.0), (5000, -14.0)]:
        ev += [(x, y0, z), (x, y1, z)]
    ef = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(3)]
    new_obj("EastBank", C.mesh_from("EastBank", ev, ef), grass, coll=coll)
    box("RiverBed", (L.SHORE_E - 150, y1 - y0, 0.5), ((L.SHORE_E + 190) / 2, 0, -24.5), pbr("Bed", (0.05, 0.04, 0.03), 0.9), coll=coll)
    water = C.water_mat("River", color=(0.060, 0.050, 0.034), rough=0.045, scale=0.055, strength=0.42, flow=(0.0, -1.6))
    new_obj("Mississippi", C.m_plane(), water, ((L.SHORE_E + 190) / 2, 0, L.WATER_Z), scale=(L.SHORE_E - 150, y1 - y0, 1), coll=coll)
    return water


def _grand_staircase(coll):
    stone = pbr("StairStone", (0.52, 0.50, 0.46), 0.8)
    n = 46
    for i in range(n):
        x = 60 + i * 2.0
        box("stair", (2.05, 86 - i * 0.2, 0.4), (x + 1.0, 0, -0.33 * (i + 1) - 0.08), stone, coll=coll)
    box("overlook", (16, 110, 0.5), (54, 0, -0.42), stone, coll=coll)


def _pond_outline(cx, cy, sign):
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        r = 1.0 + 0.16 * math.sin(3 * a + 0.7 * sign) + 0.08 * math.sin(5 * a)
        x = cx + math.cos(a) * 46 * r + 18 * math.sin(a * 1.0) * sign * 0.0
        y = cy + math.sin(a) * 118 * r
        # bend the pond around the leg like Dan Kiley's plan
        x += 0.0016 * (y - cy) ** 2 * (1 if sign > 0 else 1)
        pts.append((x, y))
    return pts


def _grounds(coll, rnd, lamps):
    """Reflecting ponds, walks, tree allees, museum entrance, Luther Ely Smith Square."""
    walk = pbr("Walk", (0.50, 0.47, 0.42), 0.75)
    pond = C.water_mat("Pond", color=(0.020, 0.045, 0.040), rough=0.02, scale=0.35, strength=0.10, flow=(0.2, 0.1))
    ponds = []
    for sign in (1, -1):
        pts = _pond_outline(-150.0, sign * 300.0, sign)
        C.polygon_plane("Pond", pts, 0.05, pond, coll=coll)
        rim = [(x + (x + 150) * 0.04, y + (y - sign * 300) * 0.025) for x, y in pts]
        C.polygon_plane("PondRim", rim, 0.02, walk, coll=coll)
        ponds.append(pts)
    paths = {}
    # riverfront overlook walk and the long curving walks that echo the Arch's catenary
    paths["overlook"] = [(46, y) for y in range(-470, 471, 20)]
    for sign in (1, -1):
        pts = []
        for i in range(41):
            u = i / 40
            y = sign * (30 + 440 * u)
            x = -30 - 62 * (math.cosh(2.2 * u) - 1) / (math.cosh(2.2) - 1) * 3.2
            pts.append((x, y))
        paths["sweep%+d" % sign] = pts
        pts = [(-232 + 38 * math.cos(u * math.pi), sign * (150 + 330 * u)) for u in [i / 30 for i in range(31)]]
        paths["outer%+d" % sign] = pts
    paths["axis"] = [(x, 0) for x in range(-285, -20, 15)]
    paths["cross_n"] = [(x, 96) for x in range(-90, 50, 14)]
    paths["cross_s"] = [(x, -96) for x in range(-90, 50, 14)]
    widths = {"overlook": 9.0, "axis": 13.0}
    for name, pts in paths.items():
        C.strip_mesh("walk_" + name, pts, widths.get(name, 5.0), 0.035, walk, coll=coll)
    # museum west entrance: circular plaza with the curved glass front set in a berm
    plaza = [(-118 + 34 * math.cos(a), 34 * math.sin(a)) for a in [i * math.pi / 24 for i in range(48)]]
    C.polygon_plane("MuseumPlaza", plaza, 0.045, pbr("Plaza", (0.56, 0.54, 0.50), 0.6), coll=coll)
    glass = pbr("MuseumGlass", (0.03, 0.05, 0.06), 0.03, spec=1.0, coat=1.0)
    for i in range(-9, 10):
        a = i * math.pi / 22
        g = box("museum_glass", (0.2, 4.0, 5.2), (-118 + 30 * math.cos(a), 30 * math.sin(a), 0.0), glass, rot=a, coll=coll)
    new_obj("museum_berm", C.m_sphere(24, 10, hemi=True), bpy.data.materials["Lawn"], (-76, 0, -0.3), scale=(44, 62, 6.5), coll=coll)
    box("museum_canopy", (4.0, 58, 0.5), (-88.5, 0, 5.2), pbr("Canopy", (0.75, 0.75, 0.76), 0.25, 0.9), coll=coll)
    # Luther Ely Smith Square and the park lid over I-44
    box("I44", (46, 6400, 0.2), (-272, 0, 0.02), pbr("Asphalt", (0.045, 0.045, 0.05), 0.75), coll=coll)
    box("ParkLid", (52, 96, 0.3), (-272, 0, 0.05), bpy.data.materials["Lawn"], coll=coll)
    box("SmithSquare", (72, 96, 0.3), (-335, 0, 0.03), bpy.data.materials["Lawn"], coll=coll)
    box("Fourth", (16, 6400, 0.2), (-378, 0, 0.03), pbr("Asphalt", (0.045, 0.045, 0.05), 0.75), coll=coll)
    box("MemorialDr", (14, 6400, 0.2), (-300, 0, 0.03), pbr("Asphalt", (0.045, 0.045, 0.05), 0.75), coll=coll)
    box("ParkLid2", (20, 96, 0.3), (-300, 0, 0.06), walk, coll=coll)
    # trees: allees along the walks plus clusters, keeping the Arch axis and legs clear
    leafs = [C.leaf_mat("Leaf", (0.035, 0.11, 0.02), (0.11, 0.22, 0.035)),
             C.leaf_mat("Leaf2", (0.05, 0.14, 0.03), (0.16, 0.26, 0.05))]

    def in_pond(x, y):
        for sign in (1, -1):
            if ((x + 150) / 60) ** 2 + ((y - sign * 300) / 135) ** 2 < 1.0:
                return True
        return False

    def clear(x, y):
        if in_pond(x, y):
            return False
        if abs(y) < 22 and x > -300:            # axis view to the Old Courthouse
            return False
        if math.hypot(x, abs(y) - 91) < 34:     # Arch legs
            return False
        if -15 < x < 75 and 70 < y < 260:        # open north lawn (scene 2 ends here)
            return False
        if math.hypot(x + 118, y) < 40 or (x > -120 and x < -30 and abs(y) < 66):
            return False
        return True

    count = 0
    for name, pts in paths.items():
        if name in ("axis",):
            continue
        p = C.Path(pts)
        s = 6.0
        while s < p.length:
            pos, h = p.at(s)
            for side in (1, -1):
                off = (widths.get(name, 5.0) / 2 + 4.0) * side
                x, y = pos.x - math.sin(h) * off, pos.y + math.cos(h) * off
                if clear(x, y) and x < 40:
                    C.tree((x, y, 0), rnd.uniform(11, 16), rnd=rnd, coll=coll, leaf=rnd.choice(leafs))
                    count += 1
            s += 11.0
    for _ in range(520):
        x, y = rnd.uniform(-262, 44), rnd.uniform(-520, 520)
        if clear(x, y) and min(abs(x - px) + abs(y - py) for pts in paths.values() for px, py in pts[::2]) > 9:
            C.tree((x, y, 0), rnd.uniform(9, 17), rnd=rnd, coll=coll, leaf=rnd.choice(leafs))
            count += 1
    # slope trees and the riverfront promenade trees
    for y in range(-520, 521, 14):
        if abs(y) > 52:
            for x in (78, 100, 124):
                C.tree((x + rnd.uniform(-4, 4), y + rnd.uniform(-4, 4), -(x - 58) * 15 / 92), rnd.uniform(8, 13), rnd=rnd, coll=coll, leaf=rnd.choice(leafs))
        C.street_lamp((152.5, y, -15.0), 5.5, power=lamps, coll=coll)
    for name in ("overlook", "sweep+1", "sweep-1", "axis"):
        p = C.Path(paths[name])
        s = 4.0
        while s < p.length:
            pos, h = p.at(s)
            off = widths.get(name, 5.0) / 2 + 0.8
            if clear(pos.x - math.sin(h) * off, pos.y + math.cos(h) * off) or name == "axis":
                C.street_lamp((pos.x - math.sin(h) * off, pos.y + math.cos(h) * off, 0), 4.0, power=lamps, coll=coll)
            s += 26.0
    print("grounds trees:", count)
    return paths, pond


def _east_bank(coll, rnd, lit):
    """Illinois side: trees, grain elevators, casino hotel, the overlook."""
    leaf = C.leaf_mat("Leaf2", (0.05, 0.14, 0.03), (0.16, 0.26, 0.05))
    for _ in range(260):
        x = L.SHORE_E + rnd.uniform(18, 420)
        y = rnd.uniform(-1500, 1700)
        if abs(y - L.EADS_Y) < 25 or abs(y - L.POPLAR_Y) < 30 or abs(y - L.MLK_Y) < 20:
            continue
        C.tree((x, y, -14.0), rnd.uniform(9, 16), rnd=rnd, coll=coll, leaf=leaf)
    conc = pbr("Silo", (0.62, 0.60, 0.55), 0.8)
    for k in range(9):       # Cargill-style grain elevator south of the Arch axis
        cyl("silo", 7.5, 34, (L.SHORE_E + 80 + (k % 3) * 15.5, -330 + (k // 3) * 15.5, -14), conc, seg=16, coll=coll)
    box("elevator_head", (22, 50, 16), (L.SHORE_E + 95, -315, 20), conc, coll=coll)
    hotel = C.facade_mat("FCasino", (0.60, 0.55, 0.45), (0.03, 0.04, 0.05), bay=3.2, floor=3.3, win_w=0.6, win_h=0.5, lit=lit, seed=11)
    box("CasinoHotel", (26, 70, 42), (L.SHORE_E + 230, 760, -14), hotel, coll=coll)
    box("Casino", (90, 120, 14), (L.SHORE_E + 150, 660, -14), hotel, coll=coll)
    box("MMMPark_overlook", (14, 40, 12), (L.SHORE_E + 90, 0, -14), pbr("OverlookConc", (0.6, 0.6, 0.58), 0.7), coll=coll)
    return hotel


class Riverfront:
    def __init__(self, scene, mood="day", duration=22.0, seed=1, crowd=1.0, quality=1.0):
        self.scene, self.mood_name, self.duration = scene, mood, duration
        m = self.m = MOODS[mood]
        rnd = random.Random(seed)
        coll = scene.collection
        sun_dir = Vector(m["sun"]).normalized()
        C.make_world(scene, m["horizon"], m["mid"], m["zenith"], strength=m["sky"], cloud=m["cloud"],
                     cloud_col=m["cloud_col"], cloud_dark=m["cloud_dark"], sun_dir=sun_dir, sun_glow=m["glow"],
                     ground=(0.03, 0.035, 0.03), seed=3.0)
        self.sun = C.make_sun(scene, sun_dir, m["sun_col"], m["sun_power"], angle=1.2)
        scene.view_settings.exposure = m["exposure"]
        self.river = _terrain(coll)
        _grand_staircase(coll)
        self.arch = L.gateway_arch(coll)
        self.paths, self.pond = _grounds(coll, rnd, m["lamps"])
        self.ch_mat, self.flag = L.old_courthouse(coll=coll, lit=m["lit"] * 0.6)
        self.facades = L.downtown(coll=coll, lit=m["lit"])
        self.facades["casino"] = _east_bank(coll, rnd, m["lit"])
        self.eads = L.eads_bridge(coll=coll, lamps=m["lamps"])
        L.girder_bridge(L.POPLAR_Y, coll=coll, name="PoplarBridge")
        L.girder_bridge(L.MLK_Y, coll=coll, name="MLKBridge", truss=True)
        # atmosphere
        self.haze = C.haze_box("Haze", (-3000, -3200, -24), (3000, 3200, 420), density=m["haze"],
                               color=tuple(lerp(1.0, c, 0.35) for c in m["horizon"]), aniso=0.55)
        self.mist = None
        if m["mist"] > 0:
            self.mist = C.haze_box("RiverMist", (150, -1500, L.WATER_Z), (L.SHORE_E + 40, 1500, L.WATER_Z + 22),
                                   density=m["mist"], color=(1.0, 0.86, 0.8), aniso=0.2, noise_scale=0.012,
                                   height_fade=(L.WATER_Z + 1.0, L.WATER_Z + 20.0))
        self._actors(rnd, crowd)

    # ------------------------------------------------------------------
    def _actors(self, rnd, crowd):
        coll = self.scene.collection
        m = self.m
        self.walkers, self.idlers = [], []
        dur = self.duration
        lights = 1.0 if m["lamps"] > 0 else 0.0
        # the riverboat works the channel off the levee
        self.boat = A.Riverboat(coll=coll, lights=lights)
        self.boat_path = C.Path([(318, 420), (318, -900)])
        # MetroLink over the Eads Bridge
        self.train = A.Train(coll=coll, lights=lights)
        # strollers on the walks
        specs = [("overlook", 26), ("sweep+1", 22), ("sweep-1", 18), ("axis", 16), ("outer+1", 10), ("outer-1", 8),
                 ("cross_n", 5), ("cross_s", 5)]
        for name, n in specs:
            path = C.Path(self.paths[name])
            wid = 9.0 if name == "overlook" else (13.0 if name == "axis" else 5.0)
            for _ in range(int(n * crowd)):
                kind = rnd.random()
                lat = rnd.uniform(-wid / 2 + 0.6, wid / 2 - 0.6)
                d = rnd.choice((1, -1))
                s0 = rnd.uniform(0, path.length)
                if kind < 0.10:
                    actor, speed = A.Pup(rnd, coll=coll), rnd.uniform(2.6, 3.6)        # kids running
                elif kind < 0.16:
                    actor, speed = A.Quad(rnd, coll=coll), 1.3                        # wolf on a walk ...
                    owner = A.Wolf(rnd, coll=coll)                                    # ... with its person
                    self.walkers.append(A.Walker(owner, path, s0 - d * 1.1, 1.3, lat + 0.7, (), d))
                else:
                    actor, speed = A.Wolf(rnd, coll=coll), rnd.uniform(1.05, 1.55)
                pauses = A.make_pauses(rnd, dur, 0.25) if isinstance(actor, A.Wolf) and not isinstance(actor, A.Pup) and kind >= 0.16 else ()
                self.walkers.append(A.Walker(actor, path, s0, speed, lat, pauses, d))
        # groups standing at the pond edge and on the overlook, talking and pointing at the Arch
        spots = [(-96, 300 + k * 9, math.pi) for k in range(-4, 5)] + [(52, y, 0.0) for y in range(-40, 41, 10)] + \
                [(-150 + 20 * math.cos(a), 20 * math.sin(a), a + math.pi) for a in (0.5, 1.4, 2.5, 3.6, 4.6, 5.6)]
        for (x, y, face) in spots:
            for k in range(rnd.choice((1, 2, 2, 3))):
                w = A.Wolf(rnd, coll=coll)
                w.place((x + rnd.uniform(-1.2, 1.2), y + rnd.uniform(-1.5, 1.5), 0.0 if x < 50 else -0.0), face + rnd.uniform(-0.7, 0.7))
                self.idlers.append((w, rnd.uniform(0.3, 1.0)))
        # cyclists and joggers on the riverfront trail, traffic on the boulevard
        trail = C.Path([(175.5, -900, -14.88), (175.5, 900, -14.88)])
        for _ in range(int(9 * crowd)):
            d = rnd.choice((1, -1))
            self.walkers.append(A.Walker(A.Cyclist(rnd, coll=coll), trail, rnd.uniform(200, 1600), rnd.uniform(4.5, 6.5),
                                         rnd.uniform(-1.2, 1.2), (), d))
        for _ in range(int(8 * crowd)):
            d = rnd.choice((1, -1))
            self.walkers.append(A.Walker(A.Wolf(rnd, coll=coll), trail, rnd.uniform(300, 1500), rnd.uniform(2.4, 3.2),
                                         rnd.uniform(-1.6, 1.6), (), d))
        self.lanes = []
        for lane_x, d in ((160.5, 1), (167.5, -1)):
            pts = [(lane_x, -1100 * d, -14.9), (lane_x, 1100 * d, -14.9)]
            cars = [A.Car(rnd, coll=coll, lights=lights) for _ in range(7)]
            starts = sorted([rnd.uniform(300, 1900) for _ in cars], reverse=True)
            starts = [s + i * -12 for i, s in enumerate(starts)]
            self.lanes.append(A.Lane(C.Path(pts), cars, starts, v0=11.0, duration=dur + 2))
        # cyclists also loop the overlook walk on the grounds
        ov = C.Path(self.paths["overlook"])
        for _ in range(int(4 * crowd)):
            self.walkers.append(A.Walker(A.Cyclist(rnd, coll=coll), ov, rnd.uniform(0, ov.length), rnd.uniform(4.0, 5.5),
                                         rnd.uniform(-3.5, 3.5), (), rnd.choice((1, -1))))

    # ------------------------------------------------------------------
    def update(self, t, boat_s0=380.0, train_s0=0.0, train_dir=1, lit=None):
        C.set_time(self.river, t)
        C.set_time(self.pond, t)
        if self.mist:
            C.set_time(self.mist.material_slots[0].material, t * 0.05)
        p, h = self.boat_path.at(boat_s0 + 2.6 * t)
        self.boat.place((p.x, p.y, L.WATER_Z + 0.3), h, t)
        e = self.eads
        if train_dir > 0:
            self.train.place((e["x0"] + train_s0 + 15.5 * t, e["y"], e["rail_z"]), 0.0)
        else:
            self.train.place((e["x1"] - train_s0 - 15.5 * t, e["y"], e["rail_z"]), math.pi)
        for w in self.walkers:
            w.update(t)
        for w, g in self.idlers:
            w.idle(t, gesture=g)
        for ln in self.lanes:
            ln.update(t)
        self.flag.rotation_euler = (0, 0, 0.25 * math.sin(t * 1.7))
        if lit is not None:
            for mat in self.facades.values():
                C.set_lit(mat, lit)
            C.set_lit(self.ch_mat, lit * 0.6)


# ----------------------------------------------------------------------------
# shots
# ----------------------------------------------------------------------------
def shot1(scene):
    """Dawn on the river: slow push-in across the water toward the Arch."""
    w = Riverfront(scene, "dawn", duration=12.0, crowd=0.35)
    cam = C.make_camera(scene, lens=32.0)

    def frame(t):
        u = smooth(t / 12.0)
        w.update(t, boat_s0=372.0, train_s0=260.0)
        pos = Vector((lerp(640, 455, u), lerp(-150, -118, u), lerp(-4.0, -9.5, u)))
        tgt = Vector((0, lerp(4, 0, u), lerp(78, 86, u)))
        cam.data.lens = lerp(30.0, 34.0, u)
        C.look_at(cam, pos, tgt)
        # first light: the sun clears the Illinois horizon during the push-in
        w.sun.data.energy = lerp(0.25, 1.6, smooth((t - 3.0) / 9.0))
    return frame, 12.0


def shot2(scene):
    """Arch grounds: descend to the north pond, then orbit from the north side."""
    w = Riverfront(scene, "day", duration=20.0, crowd=1.0)
    cam = C.make_camera(scene, lens=28.0)

    def frame(t):
        w.update(t, boat_s0=120.0, train_s0=500.0, train_dir=-1)
        u = smoother(t / 20.0)
        # one move: from high over the river, down to the overlook walk north-east of the Arch,
        # ending in a gentle orbit with the Old Courthouse and skyline behind the steel
        d = smooth(min(1.0, t / 13.0))
        o = smooth((t - 9.0) / 11.0)
        pos = Vector((lerp(340, 76, d) - 16 * o, lerp(430, 232, d) - 78 * o, lerp(150, 6.0, d) - 1.4 * o))
        tgt = Vector((lerp(0, -70, u), lerp(0, -12, u), lerp(74, 66, u)))
        cam.data.lens = lerp(26.0, 24.0, u)
        C.look_at(cam, pos, tgt)
    return frame, 20.0


def shot5(scene):
    """Golden-hour finale: one continuous pull-back up and out over the river."""
    w = Riverfront(scene, "sunset", duration=22.0, crowd=0.7)
    cam = C.make_camera(scene, lens=35.0)

    def frame(t):
        u = smoother(t / 22.0)
        lit = lerp(0.12, 0.62, smooth(t / 18.0))                     # downtown windows come on
        w.update(t, boat_s0=560.0, train_s0=180.0, lit=lit)
        pos = Vector((lerp(168, 880, u), lerp(-46, -210, u), lerp(-11.5, 150, u ** 1.3)))
        tgt = Vector((lerp(-40, -40, u), lerp(6, 20, u), lerp(92, 84, u)))
        cam.data.lens = lerp(22.0, 40.0, u)
        C.look_at(cam, pos, tgt)
        w.sun.data.energy = lerp(2.8, 1.4, u)
    return frame, 22.0

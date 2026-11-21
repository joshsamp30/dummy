"""Characters and vehicles: the Local Howl wolf pack, cars, train, riverboat.

All motion is a pure function of time so every render worker reproduces the
same frame. Forward is +X in each actor's local space.
"""
import math
import os
import random

import bpy
import bmesh
from mathutils import Matrix, Vector

from . import common as C
from .common import PAL, box, cached, cyl, empty, new_obj, pbr

FUR = [
    ((0.80, 0.78, 0.74), (0.90, 0.89, 0.86)),   # white wolf (the brand mascot)
    ((0.30, 0.28, 0.26), (0.62, 0.58, 0.52)),   # grey
    ((0.14, 0.12, 0.11), (0.38, 0.34, 0.30)),   # dark
    ((0.42, 0.30, 0.19), (0.74, 0.66, 0.54)),   # timber / tan
    ((0.52, 0.50, 0.48), (0.82, 0.80, 0.76)),   # silver
]
OUTFITS = [  # (jacket, trousers) - suits and coveralls from the brand shoots
    ("blue", "blue"), ("blue", "blue"), ("tan", "tan"), ("cream", "cream"), ("navy", "navy"),
    ("pink", "cream"), ("yellow", "navy"), ("teal", "tan"), ("blush", "blush"), ("mint", "cream"),
    ("white", "navy"), ("red", "char"), ("char", "char"), ("tan", "navy"),
]


# ----------------------------------------------------------------------------
# meshes
# ----------------------------------------------------------------------------
def _loft(name, rings, seg=12):
    """Loft elliptical rings [(z, rx, ry, cx)] into a closed smooth mesh."""
    verts, faces = [], []
    for z, rx, ry, cx in rings:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((cx + rx * math.cos(a), ry * math.sin(a), z))
    for r in range(len(rings) - 1):
        for i in range(seg):
            a, b = r * seg + i, r * seg + (i + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    faces.append(tuple(reversed(range(seg))))
    faces.append(tuple(range((len(rings) - 1) * seg, len(rings) * seg)))
    return C.mesh_from(name, verts, faces, smooth=True)


def _torso_mesh():
    return cached("wolf_torso", lambda: _loft("torso", [
        (-0.36, 0.118, 0.185, 0.0), (-0.24, 0.115, 0.175, 0.0), (-0.02, 0.125, 0.19, 0.005),
        (0.14, 0.13, 0.215, 0.0), (0.22, 0.10, 0.20, -0.005), (0.27, 0.06, 0.09, 0.0)]))


def _head_mesh():
    """Wolf head: slots 0 fur, 1 muzzle, 2 dark (nose, eyes, inner ears)."""
    def mk():
        bm = bmesh.new()

        def add(kind, mat_i, matrix, **kw):
            n0 = len(bm.faces)
            if kind == "sph":
                bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0, matrix=matrix)
            else:
                bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=1.0,
                                      radius2=kw.get("r2", 0.02), depth=1.0, matrix=matrix)
            bm.faces.ensure_lookup_table()
            for f in bm.faces[n0:]:
                f.material_index = mat_i

        T, S, R = Matrix.Translation, Matrix.Diagonal, Matrix.Rotation
        add("sph", 0, T((0, 0, 0)) @ S((0.125, 0.115, 0.112, 1)))                 # skull
        add("sph", 0, T((-0.035, 0, -0.045)) @ S((0.11, 0.165, 0.105, 1)))        # cheek ruff
        add("sph", 0, T((-0.06, 0, -0.12)) @ S((0.10, 0.13, 0.10, 1)))            # neck ruff
        # snout along +X
        add("cone", 1, T((0.175, 0, -0.03)) @ R(math.pi / 2, 4, "Y") @ S((0.05, 0.058, 0.17, 1)), r2=0.62)
        add("sph", 1, T((0.09, 0, -0.045)) @ S((0.07, 0.085, 0.055, 1)))          # muzzle base
        add("sph", 2, T((0.265, 0, -0.012)) @ S((0.026, 0.03, 0.024, 1)))         # nose
        for sy in (-1, 1):
            add("sph", 2, T((0.098, sy * 0.052, 0.038)) @ S((0.016, 0.016, 0.018, 1)))   # eyes
            ear = T((-0.03, sy * 0.075, 0.135)) @ R(sy * -0.28, 4, "X") @ R(-0.1, 4, "Y") @ S((0.04, 0.05, 0.15, 1))
            add("cone", 0, ear, r2=0.05)
            inner = T((-0.018, sy * 0.076, 0.13)) @ R(sy * -0.28, 4, "X") @ R(-0.1, 4, "Y") @ S((0.022, 0.03, 0.11, 1))
            add("cone", 2, inner, r2=0.05)
        me = C.bm_to_mesh(bm, "wolf_head", smooth=True)
        for _ in range(3):
            me.materials.append(None)
        return me
    return cached("wolf_head", mk)


def _tail_mesh():
    return cached("wolf_tail", lambda: _loft("tail", [
        (-0.50, 0.012, 0.012, 0), (-0.44, 0.05, 0.05, 0), (-0.30, 0.075, 0.075, 0),
        (-0.12, 0.06, 0.06, 0), (0.0, 0.035, 0.035, 0)], seg=8))


def _shoe_mesh():
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=1.0,
                                  matrix=Matrix.Translation((0.05, 0, 0.0)) @ Matrix.Diagonal((0.13, 0.055, 0.05, 1)))
        return C.bm_to_mesh(bm, "shoe", smooth=True)
    return cached("wolf_shoe", mk)


def fur_mats(i):
    fur, light = FUR[i % len(FUR)]
    return (pbr("Fur%d" % i, fur, 0.95, spec=0.2), pbr("Muzzle%d" % i, light, 0.95, spec=0.2),
            pbr("WolfDark", (0.012, 0.012, 0.014), 0.35))


def cloth(name):
    return pbr("Cloth_" + name, PAL[name], 0.85, spec=0.25)


# ----------------------------------------------------------------------------
# the wolf-person
# ----------------------------------------------------------------------------
class Wolf:
    """Upright wolf in a suit or coveralls, with a procedural walk cycle."""

    def __init__(self, rnd=random, scale=1.0, fur=None, outfit=None, coll=None, tail=True):
        fur = rnd.randrange(len(FUR)) if fur is None else fur
        outfit = outfit or rnd.choice(OUTFITS)
        f, mz, dark = fur_mats(fur)
        jacket, pants = cloth(outfit[0]), cloth(outfit[1])
        shoe = pbr("Shoe", (0.05, 0.03, 0.02), 0.5)
        self.scale = scale * rnd.uniform(0.94, 1.06)
        self.root = empty("wolf", coll=coll)
        self.root.scale = (self.scale,) * 3
        self.body = empty("wolf_body", parent=self.root, coll=coll)
        b = self.body
        cap = C.m_capsule
        self.torso = new_obj("torso", _torso_mesh(), jacket, (0, 0, 1.27), parent=b, coll=coll)
        new_obj("hips", C.m_sphere(10, 6), pants, (0, 0, 0.93), scale=(0.115, 0.178, 0.12), parent=b, coll=coll)
        self.head = new_obj("head", _head_mesh(), [f, mz, dark], (0.02, 0, 1.71), scale=(1.22,) * 3,
                            parent=b, coll=coll)
        shirt = pbr("Shirt", (0.85, 0.84, 0.8), 0.8)
        new_obj("collar", C.m_sphere(8, 6), shirt, (0.045, 0, 1.5), scale=(0.075, 0.085, 0.06), parent=b, coll=coll)
        self.legs = []
        for sy in (1, -1):
            up = new_obj("thigh", cap(0.078, 0.38), pants, (0, sy * 0.088, 0.93), parent=b, coll=coll)
            lo = new_obj("shin", cap(0.062, 0.38), pants, (0, 0, -0.42), parent=up, coll=coll)
            new_obj("shoe", _shoe_mesh(), shoe, (0.0, 0, -0.44), parent=lo, coll=coll)
            self.legs.append((up, lo))
        self.arms = []
        for sy in (1, -1):
            up = new_obj("arm", cap(0.056, 0.25), jacket, (0, sy * 0.235, 1.455), parent=b, coll=coll)
            lo = new_obj("forearm", cap(0.048, 0.22), jacket, (0, 0, -0.28), parent=up, coll=coll)
            new_obj("paw", C.m_sphere(8, 6), f, (0, 0, -0.27), scale=(0.05, 0.045, 0.06), parent=lo, coll=coll)
            lo.rotation_euler = (0, -0.16, 0)
            up.rotation_euler = (sy * -0.06, 0, 0)
            self.arms.append((up, lo, sy))
        self.tail = None
        if tail:
            self.tail = new_obj("tail", _tail_mesh(), f, (-0.1, 0, 0.98), (0, -2.2, 0), parent=b, coll=coll)
        self.phase0 = rnd.uniform(0, 6.28)
        self.stride = 1.45 * self.scale * rnd.uniform(0.92, 1.08)   # metres per full cycle
        self.amp = rnd.uniform(0.9, 1.1)

    def place(self, pos, heading):
        self.root.location = pos
        self.root.rotation_euler = (0, 0, heading)

    def walk(self, dist, t, speed=1.3):
        """Pose for having walked `dist` metres; t in seconds drives idle sway."""
        ph = self.phase0 + 2 * math.pi * dist / self.stride
        k = min(1.0, speed / 1.3)
        A = (0.42 + 0.18 * min(speed / 1.3, 2.0)) * self.amp * min(1.0, speed * 4.0)
        s, c = math.sin(ph), math.cos(ph)
        (lu, ll), (ru, rl) = self.legs
        lu.rotation_euler = (0, A * s, 0)
        ru.rotation_euler = (0, -A * s, 0)
        ll.rotation_euler = (0, (0.12 + 0.95 * max(0.0, -c)) * min(1.0, speed * 4.0) * (0.7 + 0.3 * k), 0)
        rl.rotation_euler = (0, (0.12 + 0.95 * max(0.0, c)) * min(1.0, speed * 4.0) * (0.7 + 0.3 * k), 0)
        for up, lo, sy in self.arms:
            up.rotation_euler = (sy * -0.06, -sy * 0.75 * A * s, 0)
        self.body.location.z = 0.022 * math.cos(2 * ph) * min(1.0, speed * 4.0)
        self.body.rotation_euler = (0, 0.04 * k, 0.05 * s * k)
        idle = 1.0 - min(1.0, speed * 2.0)
        self.head.rotation_euler = (0, 0.03 * math.sin(ph * 2), 0.10 * math.sin(t * 0.6 + self.phase0)
                                    + idle * 0.5 * math.sin(t * 0.9 + self.phase0 * 3))
        if self.tail:
            self.tail.rotation_euler = (0, -2.2 + 0.08 * math.sin(2 * ph),
                                        0.28 * s + idle * 0.5 * math.sin(t * 5.0 + self.phase0))

    def idle(self, t, gesture=0.0):
        """Standing: weight shift, head turns, tail wag, the odd paw gesture."""
        self.walk(0.0, t, speed=0.0)
        p = self.phase0
        self.body.rotation_euler = (0.02 * math.sin(t * 0.7 + p), 0.0, 0.05 * math.sin(t * 0.45 + p))
        up, lo, sy = self.arms[0]
        g = gesture * max(0.0, math.sin(t * 1.3 + p))
        up.rotation_euler = (sy * -0.06, -0.9 * g, 0)
        lo.rotation_euler = (0, -0.16 - 1.2 * g, 0)


class Pup(Wolf):
    """Kid wolf: smaller, runs."""

    def __init__(self, rnd=random, **kw):
        super().__init__(rnd=rnd, scale=0.58, **kw)
        self.stride = 1.1
        self.head.scale = (1.45, 1.45, 1.45)


class Quad:
    """Four-legged wolf (the 'dog' on a walk)."""

    def __init__(self, rnd=random, fur=None, coll=None, scale=1.0):
        fur = rnd.randrange(len(FUR)) if fur is None else fur
        f, mz, dark = fur_mats(fur)
        self.root = empty("quad", coll=coll)
        self.root.scale = (scale,) * 3
        self.body = empty("quad_body", parent=self.root, coll=coll)
        new_obj("qbody", C.m_sphere(12, 8), f, (0, 0, 0.58), scale=(0.42, 0.15, 0.17), parent=self.body, coll=coll)
        new_obj("qchest", C.m_sphere(10, 6), f, (0.22, 0, 0.62), scale=(0.2, 0.16, 0.2), parent=self.body, coll=coll)
        self.head = new_obj("qhead", _head_mesh(), [f, mz, dark], (0.48, 0, 0.82), scale=(0.95,) * 3,
                            parent=self.body, coll=coll)
        self.tail = new_obj("qtail", _tail_mesh(), f, (-0.4, 0, 0.62), (0, -1.9, 0), parent=self.body, coll=coll)
        self.legs = []
        for sx, sy in ((0.27, 0.09), (0.27, -0.09), (-0.3, 0.09), (-0.3, -0.09)):
            leg = new_obj("qleg", C.m_capsule(0.035, 0.5), f, (sx, sy, 0.55), parent=self.body, coll=coll)
            self.legs.append(leg)
        self.phase0 = rnd.uniform(0, 6.28)
        self.stride = 0.9 * scale

    def place(self, pos, heading):
        self.root.location = pos
        self.root.rotation_euler = (0, 0, heading)

    def walk(self, dist, t, speed=1.3):
        ph = self.phase0 + 2 * math.pi * dist / self.stride
        s = math.sin(ph)
        A = 0.32 * min(1.0, speed * 3.0)
        for leg, sign in zip(self.legs, (1, -1, -1, 1)):
            leg.rotation_euler = (0, sign * A * s, 0)
        self.body.location.z = 0.015 * math.cos(2 * ph)
        self.tail.rotation_euler = (0, -1.9 + 0.1 * s, 0.5 * math.sin(t * 6.0 + self.phase0))
        self.head.rotation_euler = (0, 0.1 * math.sin(t * 0.8 + self.phase0), 0.25 * math.sin(t * 0.5 + self.phase0))


class Cyclist:
    """Wolf on a bicycle. Wheels and legs turn with distance travelled."""

    def __init__(self, rnd=random, fur=None, outfit=None, coll=None):
        fur = rnd.randrange(len(FUR)) if fur is None else fur
        outfit = outfit or rnd.choice(OUTFITS)
        f, mz, dark = fur_mats(fur)
        jacket, pants = cloth(outfit[0]), cloth(outfit[1])
        frame = pbr("Bike_" + outfit[0], PAL[rnd.choice(["pink", "teal", "yellow", "cream", "red"])], 0.35, 0.3)
        tyre = pbr("Tyre", (0.015, 0.015, 0.015), 0.8)
        self.root = empty("cyclist", coll=coll)
        r = self.root
        self.wheels = []
        for x in (0.52, -0.52):
            w = new_obj("wheel", C.m_torus(0.33, 0.022, 20, 6), tyre, (x, 0, 0.35), parent=r, coll=coll)
            self.wheels.append(w)

        def tube(a, b, rad=0.018):
            a, b = Vector(a), Vector(b)
            d = b - a
            o = new_obj("tube", C.m_cyl(6), frame, a, scale=(rad, rad, d.length), parent=r, coll=coll)
            o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        seat, bb, head, bar = (-0.22, 0, 0.92), (-0.05, 0, 0.36), (0.42, 0, 0.88), (0.44, 0, 1.0)
        tube((-0.52, 0, 0.35), bb)
        tube(bb, seat)
        tube(seat, head)
        tube(bb, head)
        tube((-0.52, 0, 0.35), seat)
        tube(head, (0.52, 0, 0.35))
        tube(head, bar)
        tube((0.44, -0.22, 1.0), (0.44, 0.22, 1.0))
        new_obj("saddle", C.m_sphere(8, 6), tyre, (-0.24, 0, 0.95), scale=(0.13, 0.07, 0.03), parent=r, coll=coll)
        self.body = empty("rider", (-0.2, 0, 0.0), parent=r, coll=coll)
        b = self.body
        tor = new_obj("torso", _torso_mesh(), jacket, (0.1, 0, 1.33), (0, 0.55, 0), parent=b, coll=coll)
        new_obj("hips", C.m_sphere(10, 6), pants, (-0.04, 0, 1.0), scale=(0.115, 0.178, 0.12), parent=b, coll=coll)
        self.head = new_obj("head", _head_mesh(), [f, mz, dark], (0.36, 0, 1.68), parent=b, coll=coll)
        self.tail = new_obj("tail", _tail_mesh(), f, (-0.16, 0, 1.0), (0, -1.5, 0), parent=b, coll=coll)
        for sy in (1, -1):
            up = new_obj("arm", C.m_capsule(0.056, 0.25), jacket, (0.26, sy * 0.225, 1.5), (0, -1.0, 0), parent=b, coll=coll)
            lo = new_obj("forearm", C.m_capsule(0.048, 0.22), jacket, (0, 0, -0.28), (0, -0.25, 0), parent=up, coll=coll)
            new_obj("paw", C.m_sphere(8, 6), f, (0, 0, -0.27), scale=(0.05, 0.045, 0.06), parent=lo, coll=coll)
        self.legs = []
        for sy in (1, -1):
            up = new_obj("thigh", C.m_capsule(0.078, 0.38), pants, (-0.02, sy * 0.1, 0.98), parent=b, coll=coll)
            lo = new_obj("shin", C.m_capsule(0.062, 0.38), pants, (0, 0, -0.42), parent=up, coll=coll)
            new_obj("shoe", _shoe_mesh(), pbr("Shoe", (0.05, 0.03, 0.02), 0.5), (0, 0, -0.44), parent=lo, coll=coll)
            self.legs.append((up, lo))
        self.phase0 = rnd.uniform(0, 6.28)

    def place(self, pos, heading):
        self.root.location = pos
        self.root.rotation_euler = (0, 0, heading)

    def ride(self, dist, t):
        ang = dist / 0.35
        for w in self.wheels:
            w.rotation_euler = (0, ang, 0)
        ph = self.phase0 + dist / 2.2 * 2 * math.pi   # one crank turn every 2.2 m
        for (up, lo), off in zip(self.legs, (0.0, math.pi)):
            a = ph + off
            up.rotation_euler = (0, -1.05 + 0.38 * math.sin(a), 0)
            lo.rotation_euler = (0, 1.25 + 0.42 * math.cos(a), 0)
        self.tail.rotation_euler = (0, -1.5, 0.25 * math.sin(t * 3.0 + self.phase0))
        self.head.rotation_euler = (0, 0, 0.12 * math.sin(t * 0.7 + self.phase0))
        self.root.rotation_euler.x = 0.03 * math.sin(ph)


# ----------------------------------------------------------------------------
# vehicles
# ----------------------------------------------------------------------------
CAR_COLORS = ["cream", "pink", "teal", "navy", "yellow", "white", "mint", "red", "char", "blush", "tan", "blue"]


def _cabin_mesh(top=0.62):
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            if v.co.z > 0:
                v.co.x *= top
                v.co.y *= 0.86
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.04, segments=2, affect="EDGES")
        return C.bm_to_mesh(bm, "cabin", smooth=False)
    return cached(("cabin", top), mk)


class Car:
    def __init__(self, rnd=random, kind=None, color=None, coll=None, lights=0.0):
        kind = kind or rnd.choice(["sedan", "sedan", "suv", "hatch", "pickup"])
        color = color or rnd.choice(CAR_COLORS)
        paint = pbr("Paint_" + color, PAL[color], 0.28, 0.0, coat=1.0)
        glass = pbr("CarGlass", (0.02, 0.03, 0.04), 0.05, 0.0, spec=1.0)
        tyre = pbr("Tyre", (0.015, 0.015, 0.015), 0.8)
        hub = pbr("Hub", (0.6, 0.6, 0.62), 0.3, 1.0)
        L, W, H, cab, cabx, cabh, top = {
            "sedan": (4.5, 1.8, 0.62, 2.5, -0.15, 0.56, 0.62),
            "suv": (4.6, 1.9, 0.82, 3.0, -0.35, 0.66, 0.78),
            "hatch": (4.0, 1.75, 0.66, 2.4, -0.3, 0.58, 0.7),
            "pickup": (5.3, 1.95, 0.80, 1.7, 0.45, 0.68, 0.8),
        }[kind]
        self.length = L
        self.root = empty("car", coll=coll)
        r = self.root
        new_obj("car_body", C.m_box(0.12), paint, (0, 0, 0.32 + H / 2), scale=(L, W, H), parent=r, coll=coll)
        new_obj("car_cabin", _cabin_mesh(top), glass, (cabx, 0, 0.32 + H + cabh / 2 - 0.03),
                scale=(cab, W * 0.93, cabh), parent=r, coll=coll)
        new_obj("car_roof", C.m_box(0.1), paint, (cabx, 0, 0.32 + H + cabh - 0.02),
                scale=(cab * top * 0.97, W * 0.8, 0.06), parent=r, coll=coll)
        self.wheels = []
        for sx in (L * 0.31, -L * 0.31):
            for sy in (1, -1):
                w = empty("wheel", (sx, sy * (W / 2 - 0.1), 0.34), parent=r, coll=coll)
                new_obj("tyre", C.m_cyl(16), tyre, (0, -0.11, 0), (-math.pi / 2, 0, 0), (0.34, 0.34, 0.22), parent=w, coll=coll)
                new_obj("hub", C.m_cyl(8), hub, (0, sy * 0.115 - 0.005, 0), (-math.pi / 2, 0, 0), (0.2, 0.2, 0.01), parent=w, coll=coll)
                self.wheels.append(w)
        hl = C.emissive("Headlight%g" % lights, (1.0, 0.93, 0.78), 4.0 + 60.0 * lights)
        tl = C.emissive("Taillight%g" % lights, (1.0, 0.03, 0.02), 1.5 + 10.0 * lights)
        for sy in (1, -1):
            new_obj("hl", C.m_box(), hl, (L / 2 - 0.02, sy * (W / 2 - 0.3), 0.32 + H * 0.62), scale=(0.06, 0.34, 0.12), parent=r, coll=coll)
            new_obj("tl", C.m_box(), tl, (-L / 2 + 0.02, sy * (W / 2 - 0.3), 0.32 + H * 0.68), scale=(0.06, 0.36, 0.1), parent=r, coll=coll)
        if lights > 0.3:
            ld = bpy.data.lights.new("carbeam", "SPOT")
            ld.energy = 2500 * lights
            ld.spot_size = math.radians(70)
            ld.spot_blend = 0.6
            ld.color = (1.0, 0.92, 0.78)
            ld.shadow_soft_size = 0.2
            lo = bpy.data.objects.new("carbeam", ld)
            lo.parent = r
            lo.location = (L / 2 + 0.1, 0, 0.75)
            lo.rotation_euler = (0, -math.radians(97), 0)
            C.link(lo, coll)
        # the driver is a wolf too (head and shoulders through the glass)
        f, mz, dark = fur_mats(rnd.randrange(len(FUR)))
        new_obj("driver", _head_mesh(), [f, mz, dark], (cabx + 0.15, 0.36, 0.32 + H + cabh * 0.45),
                scale=(0.9,) * 3, parent=r, coll=coll)

    def place(self, pos, heading, dist=0.0):
        self.root.location = pos
        self.root.rotation_euler = (0, 0, heading)
        for w in self.wheels:
            w.rotation_euler = (0, dist / 0.34, 0)


def food_truck(loc, heading=0.0, coll=None, lights=0.0, logo=None):
    """The Local Howl food truck: cream box van, pink awning, logo on the side."""
    r = empty("food_truck", loc, coll=coll)
    r.rotation_euler = (0, 0, heading)
    cream = pbr("TruckCream", PAL["cream"], 0.35, coat=0.5)
    navy = pbr("TruckNavy", PAL["navy"], 0.4)
    pink = pbr("TruckPink", PAL["pink"], 0.7)
    glass = pbr("CarGlass", (0.02, 0.03, 0.04), 0.05, spec=1.0)
    tyre = pbr("Tyre", (0.015, 0.015, 0.015), 0.8)
    new_obj("ft_box", C.m_box(0.03), cream, (-0.6, 0, 1.95), scale=(4.8, 2.3, 2.6), parent=r, coll=coll)
    new_obj("ft_cab", C.m_box(0.08), cream, (2.55, 0, 1.45), scale=(1.6, 2.2, 1.6), parent=r, coll=coll)
    new_obj("ft_wind", C.m_box(0.02), glass, (3.3, 0, 1.85), scale=(0.12, 1.9, 0.7), parent=r, coll=coll)
    new_obj("ft_stripe", C.m_box(), navy, (-0.6, 0, 0.85), scale=(4.84, 2.34, 0.25), parent=r, coll=coll)
    # serving hatch on the -Y side (kerb side)
    warm = C.emissive("TruckInterior%g" % lights, (1.0, 0.78, 0.5), 2.0 + 14.0 * lights)
    new_obj("ft_hatch", C.m_box(), warm, (-0.9, -1.16, 2.1), scale=(2.4, 0.04, 0.9), parent=r, coll=coll)
    new_obj("ft_counter", C.m_box(), navy, (-0.9, -1.35, 1.62), scale=(2.6, 0.4, 0.06), parent=r, coll=coll)
    aw = new_obj("ft_awning", C.m_box(), pink, (-0.9, -1.7, 2.75), scale=(2.8, 1.1, 0.05), parent=r, coll=coll)
    aw.rotation_euler = (0.32, 0, 0)
    for sx in (1.9, -2.0):
        for sy in (1, -1):
            new_obj("ft_tyre", C.m_cyl(16), tyre, (sx, sy * 1.02 - 0.13 * (sy > 0) * 0 - 0.13, 0.42),
                    (-math.pi / 2, 0, 0), (0.42, 0.42, 0.26), parent=r, coll=coll)
    if logo and os.path.exists(logo):
        C.decal("ft_logo", logo, 1.9, (0.95, -1.165, 2.25), (math.pi / 2, 0, 0), parent=r, coll=coll, emit=0.15 * lights)
        C.decal("ft_logo2", logo, 2.6, (-0.6, 1.165, 2.1), (math.pi / 2, 0, math.pi), parent=r, coll=coll, emit=0.15 * lights)
    # a wolf in blue coveralls works the hatch
    rnd = random.Random(7)
    w = Wolf(rnd, fur=0, outfit=("blue", "blue"), coll=coll, tail=False)
    w.root.parent = r
    w.root.location = (-0.9, -0.6, 0.55)
    w.root.rotation_euler = (0, 0, -math.pi / 2)
    return r, w


class Train:
    """Two-car MetroLink light-rail set (white, red and blue stripe)."""

    CAR = 27.0

    def __init__(self, coll=None, lights=0.0):
        self.root = empty("metrolink", coll=coll)
        white = pbr("LRVWhite", (0.82, 0.82, 0.80), 0.3, coat=0.6)
        red = pbr("LRVRed", (0.6, 0.03, 0.03), 0.4)
        blue = pbr("LRVBlue", (0.02, 0.06, 0.35), 0.4)
        dark = pbr("LRVDark", (0.02, 0.02, 0.022), 0.5)
        win = C.emissive("LRVWin%g" % lights, (1.0, 0.86, 0.62), 0.6 + 5.0 * lights) if lights > 0.05 else \
            pbr("LRVGlass", (0.03, 0.04, 0.05), 0.05, spec=1.0)
        for i, x0 in enumerate((self.CAR / 2 + 0.4, -self.CAR / 2 - 0.4)):
            r = empty("lrv", (x0, 0, 0), parent=self.root, coll=coll)
            new_obj("lrv_body", C.m_box(0.03), white, (0, 0, 2.3), scale=(self.CAR, 2.65, 2.7), parent=r, coll=coll)
            new_obj("lrv_win", C.m_box(), win, (0, 0, 2.75), scale=(self.CAR - 2.4, 2.69, 0.95), parent=r, coll=coll)
            new_obj("lrv_red", C.m_box(), red, (0, 0, 1.85), scale=(self.CAR + 0.02, 2.68, 0.22), parent=r, coll=coll)
            new_obj("lrv_blue", C.m_box(), blue, (0, 0, 1.58), scale=(self.CAR + 0.02, 2.68, 0.2), parent=r, coll=coll)
            new_obj("lrv_skirt", C.m_box(), dark, (0, 0, 0.6), scale=(self.CAR - 1.0, 2.5, 0.8), parent=r, coll=coll)
            new_obj("lrv_roof", C.m_box(0.05), dark, (0, 0, 3.75), scale=(self.CAR - 4.0, 1.8, 0.25), parent=r, coll=coll)
            for k in range(-3, 4):   # door pillars break up the window band
                new_obj("lrv_pillar", C.m_box(), white, (k * 3.6, 0, 2.75), scale=(0.35, 2.7, 0.97), parent=r, coll=coll)
            # pantograph
            new_obj("panto", C.m_box(), dark, (2.0, 0, 4.35), scale=(1.8, 0.06, 0.06), parent=r, coll=coll).rotation_euler = (0, 0.5, 0)
            new_obj("panto2", C.m_box(), dark, (1.3, 0, 4.78), scale=(0.08, 1.6, 0.05), parent=r, coll=coll)
        hl = C.emissive("LRVHead", (1.0, 0.95, 0.85), 30.0)
        for sy in (0.8, -0.8):
            new_obj("lrv_hl", C.m_box(), hl, (self.CAR + 0.42, sy, 1.35), scale=(0.05, 0.3, 0.16), parent=self.root, coll=coll)
        self.length = 2 * self.CAR + 0.8

    def place(self, pos, heading):
        self.root.location = pos
        self.root.rotation_euler = (0, 0, heading)


class Riverboat:
    """Sternwheel excursion boat like the ones that work the St. Louis levee."""

    def __init__(self, coll=None, lights=0.0):
        self.root = empty("riverboat", coll=coll)
        r = self.root
        white = pbr("BoatWhite", (0.86, 0.85, 0.82), 0.5)
        red = pbr("BoatRed", (0.55, 0.04, 0.03), 0.5)
        black = pbr("BoatBlack", (0.02, 0.02, 0.02), 0.6)
        deckm = pbr("BoatDeck", (0.35, 0.25, 0.16), 0.8)
        win = C.emissive("BoatWin%g" % lights, (1.0, 0.75, 0.45), 1.0 + 9.0 * lights)
        L, W = 46.0, 11.0
        # hull with a pointed bow
        hv = [(-L / 2, -W / 2, 0), (L / 2 - 9, -W / 2, 0), (L / 2, 0, 0), (L / 2 - 9, W / 2, 0), (-L / 2, W / 2, 0)]
        verts = [(x, y, -0.8) for x, y, _ in hv] + [(x, y, 1.6) for x, y, _ in hv]
        faces = [(0, 1, 2, 3, 4)[::-1], (5, 6, 7, 8, 9)] + [(i, (i + 1) % 5, (i + 1) % 5 + 5, i + 5) for i in range(5)]
        new_obj("hull", C.mesh_from("hull", verts, faces), white, parent=r, coll=coll)
        new_obj("hull_band", C.m_box(), red, (-4.5, 0, 0.25), scale=(L - 9.2, W + 0.06, 0.3), parent=r, coll=coll)
        z = 1.6
        for d, (dl, dw, dh, x0) in enumerate([(34, 9.6, 3.1, -3.5), (30, 9.0, 2.9, -4.5), (10, 6.0, 2.6, 2.0)]):
            new_obj("cabin%d" % d, C.m_box(), white, (x0, 0, z + dh / 2), scale=(dl, dw, dh), parent=r, coll=coll)
            new_obj("winband%d" % d, C.m_box(), win, (x0, 0, z + dh * 0.58), scale=(dl - 1.5, dw + 0.04, dh * 0.32), parent=r, coll=coll)
            n = int(dl / 1.6)
            for k in range(n + 1):   # mullions
                new_obj("mull", C.m_box(), white, (x0 - dl / 2 + 0.75 + k * (dl - 1.5) / n, 0, z + dh * 0.58),
                        scale=(0.22, dw + 0.06, dh * 0.34), parent=r, coll=coll)
            new_obj("deck%d" % d, C.m_box(), deckm, (x0 + 1.0, 0, z + dh + 0.08), scale=(dl + 4.0, dw + 1.6, 0.16), parent=r, coll=coll)
            for sy in (1, -1):       # railings
                new_obj("rail", C.m_box(), white, (x0 + 1.0, sy * (dw / 2 + 0.75), z + dh + 1.1),
                        scale=(dl + 4.0, 0.06, 0.06), parent=r, coll=coll)
                for k in range(int((dl + 4) / 2.5) + 1):
                    new_obj("post", C.m_box(), white, (x0 + 1.0 - (dl + 4) / 2 + k * 2.5, sy * (dw / 2 + 0.75), z + dh + 0.6),
                            scale=(0.06, 0.06, 1.0), parent=r, coll=coll)
            z += dh + 0.16
        for sy in (1.6, -1.6):       # twin stacks with crowns
            cyl("stack", 0.5, 7.5, (9.0, sy, z - 2.6), black, parent=r, coll=coll, seg=12)
            cyl("crown", 0.75, 0.5, (9.0, sy, z + 4.7), red, r2=1.25, parent=r, coll=coll, seg=12)
        # stern paddlewheel
        self.wheel = empty("paddle", (-L / 2 - 2.6, 0, 1.3), parent=r, coll=coll)
        for k in range(12):
            a = k * math.pi / 6
            p = new_obj("blade", C.m_box(), red, (math.cos(a) * 2.3, 0, math.sin(a) * 2.3), (0, -a, 0),
                        (1.5, 8.6, 0.12), parent=self.wheel, coll=coll)
        for sy in (4.4, -4.4):
            new_obj("rim", C.m_torus(2.9, 0.09, 24, 6), red, (0, sy, 0), parent=self.wheel, coll=coll)
        new_obj("axle", C.m_cyl(8), black, (0, -4.6, 0), (-math.pi / 2, 0, 0), (0.2, 0.2, 9.2), parent=self.wheel, coll=coll)
        # passengers on the top deck: wolves at the rail
        rnd = random.Random(11)
        self.crew = []
        for k in range(10):
            w = Wolf(rnd, coll=coll)
            w.root.parent = r
            sy = rnd.choice((1, -1))
            w.root.location = (rnd.uniform(-18, 8), sy * 4.6, 7.92)
            w.root.rotation_euler = (0, 0, sy * math.pi / 2 + rnd.uniform(-0.4, 0.4))
            self.crew.append(w)

    def place(self, pos, heading, t):
        self.root.location = (pos[0], pos[1], pos[2] + 0.06 * math.sin(t * 0.8))
        self.root.rotation_euler = (0.006 * math.sin(t * 0.6), 0.004 * math.sin(t * 0.47), heading)
        self.wheel.rotation_euler = (0, t * 1.1, 0)
        for w in self.crew:
            w.idle(t, gesture=0.6)


# ----------------------------------------------------------------------------
# crowd + traffic simulation
# ----------------------------------------------------------------------------
class Walker:
    """An agent following a path with its own pace, pauses and lateral lane."""

    def __init__(self, actor, path, s0, speed, lateral=0.0, pauses=(), direction=1, loop=True):
        self.actor, self.path, self.s0, self.speed = actor, path, s0, speed
        self.lateral, self.pauses, self.dir, self.loop = lateral, pauses, direction, loop

    def state(self, t):
        """Distance walked and current speed at time t (pauses = (start, length))."""
        walked, v = 0.0, self.speed
        tt = t
        for (ps, pl) in self.pauses:
            if t >= ps + pl:
                tt -= pl
            elif t > ps:
                tt -= (t - ps)
                # ease in/out of the stop
                v = 0.0
        # soften stops: ramp speed within 0.6 s of a pause boundary
        for (ps, pl) in self.pauses:
            if ps - 0.6 < t <= ps:
                v = self.speed * (ps - t) / 0.6
            elif ps + pl <= t < ps + pl + 0.6:
                v = self.speed * (t - ps - pl) / 0.6
        walked = self.speed * tt
        return walked, v

    def update(self, t):
        walked, v = self.state(t)
        s = self.s0 + self.dir * walked
        if not self.path.closed and self.loop:
            s %= self.path.length
        p, h = self.path.at(s)
        if self.dir < 0:
            h += math.pi
        n = Vector((-math.sin(h), math.cos(h), 0))
        pos = p + n * self.lateral
        a = self.actor
        a.place(pos, h)
        if isinstance(a, Cyclist):
            a.ride(walked, t)
        else:
            a.walk(walked, t, speed=v)


class Lane:
    """One traffic lane with car-following and a stop line (simple IDM-style sim).

    The whole timeline is integrated once at build time so any frame can be
    rendered independently.
    """

    def __init__(self, path, cars, starts, v0=11.0, stop_s=None, signal=None, duration=30.0, dt=1 / 24.0):
        self.path, self.cars = path, cars
        n = len(cars)
        s = list(starts)
        v = [v0 * 0.9] * n
        steps = int(duration / dt) + 2
        self.track = [[0.0] * steps for _ in range(n)]
        order = sorted(range(n), key=lambda i: -s[i])
        for k in range(steps):
            t = k * dt
            red = signal(t) if signal else False
            for rank, i in enumerate(order):
                gap = 1e9
                if rank > 0:
                    j = order[rank - 1]
                    gap = s[j] - s[i] - (cars[j].length + cars[i].length) / 2
                if red and stop_s is not None and s[i] < stop_s - 1.0:
                    gap = min(gap, stop_s - s[i] - cars[i].length / 2 - 1.0)
                desired = 2.0 + v[i] * 1.2 + v[i] * v[i] / 5.0
                acc = 2.0 * (1 - (v[i] / v0) ** 4 - (desired / max(gap, 0.1)) ** 2)
                v[i] = max(0.0, v[i] + max(acc, -8.0) * dt)
                s[i] += v[i] * dt
                self.track[i][k] = s[i]
        self.dt = dt

    def update(self, t):
        k = min(int(t / self.dt), len(self.track[0]) - 2)
        f = t / self.dt - k
        for car, tr in zip(self.cars, self.track):
            s = tr[k] + (tr[k + 1] - tr[k]) * f
            if self.path.closed or s < self.path.length:
                p, h = self.path.at(s)
                car.place(p, h, s)
            else:
                p, h = self.path.at(self.path.length - 1e-3)
                d = Vector((math.cos(h), math.sin(h), 0))
                car.place(p + d * (s - self.path.length), h, s)


def make_pauses(rnd, duration, chance=0.35):
    if rnd.random() > chance:
        return ()
    ps = rnd.uniform(1.0, max(1.5, duration - 4.0))
    return ((ps, rnd.uniform(1.5, 4.5)),)

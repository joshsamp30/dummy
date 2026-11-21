"""Street-scene kit: storefront rows, signs, sidewalks, shared by Washington Ave and the Delmar Loop."""
import math
import random

import bpy

from . import actors as A
from . import common as C
from .common import PAL, box, cyl, new_obj, pbr

NEON = {
    "pink": (1.0, 0.10, 0.35), "red": (1.0, 0.05, 0.03), "blue": (0.10, 0.35, 1.0), "cyan": (0.05, 0.9, 1.0),
    "green": (0.10, 1.0, 0.25), "yellow": (1.0, 0.75, 0.08), "white": (1.0, 0.92, 0.80), "orange": (1.0, 0.35, 0.03),
    "violet": (0.55, 0.15, 1.0),
}


def text(name, body, size, loc, rot=(math.pi / 2, 0, 0), mat=None, extrude=0.03, coll=None, align="CENTER", parent=None):
    """Text object (upright, facing -Y by default)."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = 1.05
    o = bpy.data.objects.new(name, cu)
    o.location = loc
    o.rotation_euler = rot
    if mat:
        cu.materials.append(mat)
    if parent is not None:
        o.parent = parent
    C.link(o, coll)
    return o


def neon_sign(body, size, loc, color="pink", strength=28.0, facing=-1, coll=None, backing=True, vertical=False):
    """Glowing sign lettering on a dark backing board. facing=-1 faces -Y, +1 faces +Y."""
    col = NEON[color]
    mat = C.emissive("Neon_%s_%g" % (color, strength), col, strength)
    rz = 0.0 if facing < 0 else math.pi
    if vertical:
        body = "\n".join(body)
    o = text("sign_" + body[:8], body, size, (loc[0], loc[1] + facing * 0.12, loc[2]), (math.pi / 2, 0, rz), mat, coll=coll)
    if vertical:
        o.data.space_line = 0.85
        o.data.align_y = "TOP"
    if backing:
        if vertical:
            n = len(body.split("\n"))
            box("sign_back", (size * 1.5, 0.16, size * 0.9 * n + 0.6), (loc[0], loc[1], loc[2] - size * 0.9 * n - 0.1),
                pbr("SignBack", (0.02, 0.02, 0.025), 0.5), coll=coll)
        else:
            w = max(1.0, len(body) * size * 0.68)
            box("sign_back", (w + 0.6, 0.16, size * 1.5), (loc[0], loc[1], loc[2] - size * 0.75),
                pbr("SignBack", (0.02, 0.02, 0.025), 0.5), coll=coll)
    return o


def storefront(x, y, w, d, h, facing, wall="brick", sign=None, sign_color="pink", awning=None, lit=0.6,
               coll=None, seed=0, floors=None, shop_glow=(1.0, 0.72, 0.42), glow=6.0, name="shop", sign_size=None,
               blade=None, blade_color="red", cornice=True):
    """One building in a street wall. (x, y) is the centre of its street frontage line.

    facing = -1: building sits north of the line and faces south (-Y); +1 the opposite.
    """
    rnd = random.Random(seed)
    cy = y - facing * d / 2
    walls = {
        "brick": ((0.30, 0.10, 0.065), True), "darkbrick": ((0.16, 0.07, 0.05), True), "buff": ((0.50, 0.38, 0.24), True),
        "cream": ((0.70, 0.64, 0.52), False), "white": ((0.75, 0.74, 0.70), False), "grey": ((0.35, 0.35, 0.36), False),
        "terracotta": ((0.62, 0.50, 0.36), False), "teal": (PAL["teal"], False), "pink": (PAL["blush"], False),
        "navy": (PAL["navy"], False), "yellow": (PAL["yellow"], False),
    }
    wc, is_brick = walls[wall]
    fl = floors or max(1, int((h - 4.6) / 3.9))
    mat = C.facade_mat("F_%s_%d" % (wall, seed % 5), wc, (0.03, 0.035, 0.04), bay=rnd.choice([2.2, 2.6, 3.0]),
                       floor=(h - 4.6) / max(fl, 1) if fl else 4.0, win_w=rnd.choice([0.45, 0.55, 0.62]),
                       win_h=0.6, lit=lit, brick=is_brick, seed=seed % 5, base=4.6)
    box(name, (w - 0.3, d, h), (x, cy, 0), mat, coll=coll)
    trim = pbr("Trim_" + wall, tuple(min(1, c * 1.35 + 0.05) for c in wc), 0.7)
    if cornice:
        box("cornice", (w - 0.1, 0.9, 0.7), (x, y + facing * 0.25, h - 0.5), trim, coll=coll)
        box("band", (w - 0.2, 0.35, 0.4), (x, y + facing * 0.1, 4.5), trim, coll=coll)
    # ground-floor shopfront: glowing glass between piers
    interior = C.emissive("ShopGlow_%g_%g_%g_%g" % (*shop_glow, glow), shop_glow, glow)
    frame = pbr("ShopFrame", (0.03, 0.03, 0.035), 0.4)
    nb = max(1, int(w / 5.5))
    bw = (w - 0.6) / nb
    for k in range(nb):
        bx = x - w / 2 + 0.3 + bw * (k + 0.5)
        box("shopglass", (bw - 0.5, 0.12, 3.1), (bx, y + facing * 0.06, 0.55), interior, coll=coll)
        box("shopsill", (bw - 0.3, 0.3, 0.55), (bx, y + facing * 0.1, 0), frame, coll=coll)
        box("shophead", (bw - 0.3, 0.3, 0.35), (bx, y + facing * 0.1, 3.65), frame, coll=coll)
        box("mullion", (0.08, 0.2, 3.1), (bx, y + facing * 0.12, 0.55), frame, coll=coll)
    if awning:
        am = pbr("Awning_" + awning, PAL[awning], 0.8)
        for k in range(nb):
            bx = x - w / 2 + 0.3 + bw * (k + 0.5)
            a = box("awning", (bw - 0.7, 1.5, 0.08), (bx, y + facing * 0.8, 3.55), am, coll=coll)
            a.rotation_euler = (-facing * 0.38, 0, 0)
    if sign:
        ss = sign_size or min(1.1, (w - 2.0) / (len(sign) * 0.68))
        neon_sign(sign, ss, (x, y + facing * 0.2, 4.2 + ss * 0.9), sign_color, facing=facing, coll=coll)
    if blade:
        bs = 0.8
        o = text("blade", "\n".join(blade), bs, (x + w / 2 - 1.2, y + facing * 1.2, min(h - 0.5, 5.0 + bs * 0.9 * len(blade))),
                 (math.pi / 2, 0, math.pi / 2), C.emissive("Neon_%s_30" % blade_color, NEON[blade_color], 30.0), coll=coll)
        o.data.space_line = 0.85
        o.data.align_y = "TOP"
        box("blade_back", (0.2, 1.4, bs * 0.9 * len(blade) + 0.6), (x + w / 2 - 1.2, y + facing * 1.2,
            min(h - 0.5, 5.0 + bs * 0.9 * len(blade)) - bs * 0.9 * len(blade) - 0.3), pbr("SignBack", (0.02, 0.02, 0.025), 0.5), coll=coll)
    return mat


def street(x0, x1, y, road_w=14.0, walk_w=5.5, coll=None, wet=0.0, lamps=0.0, lamp_gap=24.0, trees=True, rnd=random,
           centre_line=True, tracks=False, stars=False):
    """East-west street centred on y with kerbs, sidewalks, lamps, trees and lane paint."""
    asphalt = C.ground_mat("Asphalt_%g" % wet, (0.035, 0.035, 0.04), (0.06, 0.06, 0.065), scale=0.6, rough=0.75 - 0.6 * wet, bump=0.15)
    walk = C.ground_mat("Sidewalk_%g" % wet, (0.36, 0.34, 0.31), (0.46, 0.44, 0.40), scale=0.8, rough=0.8 - 0.45 * wet, bump=0.1)
    L = x1 - x0
    cx = (x0 + x1) / 2
    box("road", (L, road_w, 0.2), (cx, y, -0.2), asphalt, coll=coll)
    paint = pbr("LanePaint", (0.75, 0.62, 0.12), 0.6)
    white = pbr("LaneWhite", (0.7, 0.7, 0.68), 0.6)
    if centre_line:
        for dy in (-0.12, 0.12):
            box("centre", (L, 0.1, 0.01), (cx, y + dy, 0.001), paint, coll=coll)
    if tracks:
        steel = pbr("Rail", (0.4, 0.4, 0.42), 0.3, 1.0)
        for dy in (-2.6, -1.17):
            box("rail", (L, 0.07, 0.012), (cx, y + dy, 0.001), steel, coll=coll)
    for sgn in (1, -1):
        box("sidewalk", (L, walk_w, 0.34), (cx, y + sgn * (road_w / 2 + walk_w / 2), -0.2), walk, coll=coll)
        box("kerb", (L, 0.2, 0.36), (cx, y + sgn * (road_w / 2 + 0.1), -0.2), pbr("Kerb", (0.5, 0.49, 0.46), 0.7), coll=coll)
        n = int(L / lamp_gap)
        for k in range(n):
            lx = x0 + lamp_gap / 2 + k * lamp_gap + (lamp_gap / 2 if sgn > 0 else 0)
            C.street_lamp((lx, y + sgn * (road_w / 2 + 0.7), 0.14), 5.2, power=lamps, coll=coll)
            if lamps > 0 and k % 2 == 0:
                ld = bpy.data.lights.new("lamp", "POINT")
                ld.energy = 900
                ld.color = (1.0, 0.72, 0.42)
                ld.shadow_soft_size = 0.3
                lo = bpy.data.objects.new("lamp", ld)
                lo.location = (lx, y + sgn * (road_w / 2 + 0.5), 5.3)
                C.link(lo, coll)
            if trees and k % 2 == 0:
                C.tree((lx + lamp_gap / 2, y + sgn * (road_w / 2 + 1.1), 0.14), rnd.uniform(11.0, 13.0), spread=2.0, rnd=rnd, coll=coll)
        if stars:   # St. Louis Walk of Fame: brass stars set into the sidewalk
            brass = pbr("Brass", (0.75, 0.52, 0.18), 0.25, 1.0)
            star = C.cached("star", _star_mesh)
            k = 0
            xx = x0 + 3.0
            while xx < x1 - 3:
                new_obj("fame_star", star, brass, (xx, y + sgn * (road_w / 2 + 2.3), 0.146), scale=(0.34, 0.34, 1), coll=coll)
                box("fame_plaque", (0.5, 0.32, 0.006), (xx, y + sgn * (road_w / 2 + 2.3) - 0.62, 0.142), brass, coll=coll)
                xx += 3.4
                k += 1


def _star_mesh():
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        r = 1.0 if i % 2 == 0 else 0.42
        pts.append((math.cos(a) * r, math.sin(a) * r, 0))
    return C.mesh_from("star", pts + [(0, 0, 0)], [(i, (i + 1) % 10, 10) for i in range(10)])


def crosswalk(x, y, road_w, coll=None):
    white = pbr("LaneWhite", (0.7, 0.7, 0.68), 0.6)
    n = int(road_w / 1.2)
    for k in range(n):
        box("zebra", (3.0, 0.55, 0.01), (x, y - road_w / 2 + 0.6 + k * 1.2, 0.002), white, coll=coll)


def signal(x, y, coll=None):
    """Traffic signal head on a mast arm. Returns (red, green) materials to switch."""
    iron = pbr("LampIron", (0.02, 0.02, 0.022), 0.5, 0.6)
    cyl("sig_post", 0.1, 6.0, (x, y, 0.14), iron, seg=8, coll=coll)
    box("sig_arm", (0.12, 5.0, 0.12), (x, y + (2.5 if y < 0 else -2.5) * 0 - 2.5, 6.0), iron, coll=coll)
    red, _, _ = C.new_mat("SigRed")
    grn, _, _ = C.new_mat("SigGreen")
    for m, col in ((red, (1, 0.03, 0.02)), (grn, (0.05, 1, 0.3))):
        nt = m.node_tree
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs[0].default_value = (*col, 1)
        nt.links.new(e.outputs[0], [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"][0].inputs[0])
        m["_emit"] = e.name
    box("sig_head", (0.35, 0.4, 1.1), (x - 0.1, y - 4.6, 5.3), iron, coll=coll)
    new_obj("sig_r", C.m_sphere(8, 6), red, (x - 0.3, y - 4.6, 6.1), scale=(0.13,) * 3, coll=coll)
    new_obj("sig_g", C.m_sphere(8, 6), grn, (x - 0.3, y - 4.6, 5.55), scale=(0.13,) * 3, coll=coll)
    return red, grn


def set_signal(mats, is_red):
    red, grn = mats
    red.node_tree.nodes[red["_emit"]].inputs[1].default_value = 40.0 if is_red else 0.3
    grn.node_tree.nodes[grn["_emit"]].inputs[1].default_value = 0.3 if is_red else 40.0


def sidewalk_crowd(world, rnd, x0, x1, y, road_w, walk_w, n, duration, coll=None, pup=0.06, quad=0.05):
    """Wolves walking both sidewalks, some pausing at shop windows."""
    for sgn in (1, -1):
        yy = y + sgn * (road_w / 2 + walk_w / 2 + 0.3)
        path = C.Path([(x0, yy, 0.14), (x1, yy, 0.14)])
        for _ in range(n):
            k = rnd.random()
            d = rnd.choice((1, -1))
            lat = rnd.uniform(-walk_w / 2 + 1.0, walk_w / 2 - 0.6)
            s0 = rnd.uniform(0, path.length)
            if k < pup:
                actor, sp = A.Pup(rnd, coll=coll), rnd.uniform(2.4, 3.2)
            elif k < pup + quad:
                actor, sp = A.Quad(rnd, coll=coll), 1.3
                world.walkers.append(A.Walker(A.Wolf(rnd, coll=coll), path, s0 - d * 1.1, 1.3, lat + 0.6, (), d))
            else:
                actor, sp = A.Wolf(rnd, coll=coll), rnd.uniform(1.0, 1.6)
            pauses = A.make_pauses(rnd, duration, 0.3) if type(actor) is A.Wolf else ()
            world.walkers.append(A.Walker(actor, path, s0, sp, lat, pauses, d))

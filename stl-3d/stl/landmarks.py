"""St. Louis landmarks built to published dimensions.

Local grid: origin at the centre of the Gateway Arch at ground level.
X = east toward the Mississippi, Y = north along the downtown street grid.
"""
import math
import random

import bpy
import bmesh
from mathutils import Matrix, Vector

from . import common as C
from .common import FT, box, cyl, new_obj, pbr

WATER_Z = -21.0          # normal river stage relative to the Arch grounds
SHORE_W = 196.0          # west water edge
SHORE_E = 670.0          # Illinois bank
EADS_Y = 560.0           # Eads Bridge sits ~6 blocks north of the Arch axis
POPLAR_Y = -590.0
MLK_Y = 900.0


# ----------------------------------------------------------------------------
# Gateway Arch
# ----------------------------------------------------------------------------
def arch_centroid(yf):
    """Centroid height (ft) at horizontal position yf (ft). Saarinen/Bandel equation."""
    return 693.8597 - 68.7672 * math.cosh(0.0100333 * yf)


def arch_side(yf):
    """Side of the equilateral cross-section (ft): 54 ft at the base, 17 ft at the top."""
    q = 125.1406 * math.cosh(0.0100333 * yf)
    return math.sqrt(4.0 * q / math.sqrt(3.0))


def gateway_arch(coll=None, stations=240):
    """630 ft x 630 ft weighted catenary with tapering equilateral sections.

    One flat face is on the extrados, the ridge points to the intrados. Each of
    the three skins is its own strip so the ridges stay razor sharp while the
    steel reads smooth along the curve. UVs are in metres (plates in the shader).
    """
    half = 299.2239
    # sample evenly in arc length
    dense = [(-half + 2 * half * i / 4000.0) for i in range(4001)]
    pts = [(y * FT, arch_centroid(y) * FT) for y in dense]
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = cum[-1]
    rows = []
    j = 0
    for i in range(stations + 1):
        s = total * i / stations
        while j < len(cum) - 2 and cum[j + 1] < s:
            j += 1
        f = (s - cum[j]) / max(cum[j + 1] - cum[j], 1e-9)
        yf = dense[j] + (dense[j + 1] - dense[j]) * f
        y, z = yf * FT, arch_centroid(yf) * FT
        dz = -68.7672 * 0.0100333 * math.sinh(0.0100333 * yf)      # dz/dy
        t = Vector((0, 1, dz)).normalized()
        n = Vector((0, t.z, -t.y))                                 # in-plane normal
        if n.z > 0:
            n = -n                                                 # make it point to the intrados
        side = arch_side(yf) * FT
        p = Vector((0, y, z))
        inner = p + n * (side / math.sqrt(3))
        oe = p - n * (side / (2 * math.sqrt(3))) + Vector((side / 2, 0, 0))
        ow = p - n * (side / (2 * math.sqrt(3))) - Vector((side / 2, 0, 0))
        rows.append((s, side, inner, oe, ow))
    verts, faces, uvs = [], [], []
    for a_i, b_i in ((3, 4), (4, 2), (2, 3)):        # extrados, west skin, east skin
        base = len(verts)
        for s, side, inner, oe, ow in rows:
            r = (s, side, inner, oe, ow)
            verts += [tuple(r[a_i]), tuple(r[b_i])]
            uvs += [(-side / 2, s), (side / 2, s)]
        for i in range(stations):
            faces.append((base + 2 * i, base + 2 * i + 1, base + 2 * i + 3, base + 2 * i + 2))
    me = bpy.data.meshes.new("GatewayArch")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.update()
    arch = new_obj("GatewayArch", me, C.steel_mat(), coll=coll)
    # observation windows: 16 slits each side of the crown on the lower skins
    dark = pbr("ArchWindow", (0.01, 0.01, 0.012), 0.1)
    top = 625.0925 * FT
    side = 17.0 * FT
    for sx in (1, -1):
        # lower skin runs from the outer edge (x = ±side/2) down to the ridge (x = 0)
        nrm = Vector((sx * math.sin(math.radians(60)), 0, -math.cos(math.radians(60))))
        mid = Vector((sx * side / 4, 0, top - side / (2 * math.sqrt(3)) - side * math.sqrt(3) / 4))
        for k in range(16):
            y = (k - 7.5) * 1.15
            w = new_obj("arch_win", C.m_box(), dark, mid + nrm * 0.02 + Vector((0, y, -0.04 * abs(k - 7.5))),
                        scale=(0.02, 0.69, 0.18), coll=coll)
            w.rotation_euler = (0, -sx * math.radians(30), 0)
    return arch


# ----------------------------------------------------------------------------
# Old Courthouse
# ----------------------------------------------------------------------------
def old_courthouse(loc=(-425.0, 0.0, 0.0), coll=None, lit=0.0):
    """Greek Revival cruciform courthouse with its tall Renaissance dome."""
    x0, y0, z0 = loc
    stone = C.facade_mat("CourthouseStone", wall=(0.74, 0.70, 0.62), glass=(0.04, 0.05, 0.06), bay=3.4, floor=5.2,
                         win_w=0.34, win_h=0.62, lit=lit, wall_rough=0.8)
    plain = pbr("CourthouseTrim", (0.78, 0.75, 0.68), 0.75)
    dome_m = pbr("CourthouseDome", (0.36, 0.47, 0.42), 0.55)
    roof = pbr("CourthouseRoof", (0.22, 0.25, 0.24), 0.6)
    parts = []
    H = 15.6
    parts.append(box("ch_core", (30, 30, H + 3), (x0, y0, z0), stone, coll=coll))
    parts.append(box("ch_ew", (86, 21, H), (x0, y0, z0), stone, coll=coll))
    parts.append(box("ch_ns", (21, 70, H), (x0, y0, z0), stone, coll=coll))
    parts.append(box("ch_cornice_ew", (87.2, 22.2, 0.9), (x0, y0, z0 + H), plain, coll=coll))
    parts.append(box("ch_cornice_ns", (22.2, 71.2, 0.9), (x0, y0, z0 + H), plain, coll=coll))
    parts.append(box("ch_plinth", (90, 74, 1.2), (x0, y0, z0 - 0.2), plain, coll=coll))
    # porticos on all four fronts: six Doric columns and a pediment
    for dx, dy, wid, along_x in ((43, 0, 21, False), (-43, 0, 21, False), (0, 35, 21, True), (0, -35, 21, True)):
        sgn = 1 if (dx + dy) > 0 else -1
        depth = 5.5
        cx, cy = x0 + dx + (sgn * depth / 2 if not along_x else 0), y0 + dy + (sgn * depth / 2 if along_x else 0)
        for k in range(6):
            off = (k - 2.5) * (wid - 2.4) / 5
            px = cx + (off if along_x else sgn * (depth / 2 - 0.9))
            py = cy + (off if not along_x else sgn * (depth / 2 - 0.9))
            parts.append(cyl("ch_col", 0.72, H - 1.6, (px, py, z0 + 1.0), plain, r2=0.82, seg=14, coll=coll))
        sz = (wid, depth, 1.0) if along_x else (depth, wid, 1.0)
        parts.append(box("ch_entab", sz, (cx, cy, z0 + H - 0.6), plain, coll=coll))
        parts.append(box("ch_steps", (sz[0] + 2, sz[1] + 2, 1.0), (cx, cy, z0), plain, coll=coll))
        # pediment (triangular prism)
        hw, ph = wid / 2, 3.2
        if along_x:
            v = [(-hw, -depth / 2, 0), (hw, -depth / 2, 0), (0, -depth / 2, ph), (-hw, depth / 2, 0), (hw, depth / 2, 0), (0, depth / 2, ph)]
        else:
            v = [(-depth / 2, -hw, 0), (-depth / 2, hw, 0), (-depth / 2, 0, ph), (depth / 2, -hw, 0), (depth / 2, hw, 0), (depth / 2, 0, ph)]
        me = C.mesh_from("pediment", v, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)])
        parts.append(new_obj("ch_pediment", me, plain, (cx, cy, z0 + H + 0.4), coll=coll))
    # drum, colonnade, dome, lantern, flagpole (58 m to the tip)
    zb = z0 + H + 3
    parts.append(cyl("ch_drum_base", 11.2, 3.0, (x0, y0, zb), plain, seg=32, coll=coll))
    parts.append(cyl("ch_drum", 8.6, 11.0, (x0, y0, zb + 3), stone, seg=32, coll=coll))
    for k in range(24):
        a = k * math.pi / 12
        parts.append(cyl("ch_dcol", 0.42, 8.2, (x0 + math.cos(a) * 10.0, y0 + math.sin(a) * 10.0, zb + 3), plain, seg=8, coll=coll))
    parts.append(cyl("ch_ring", 10.9, 0.9, (x0, y0, zb + 11.2), plain, seg=32, coll=coll))
    parts.append(cyl("ch_attic", 8.9, 3.4, (x0, y0, zb + 12.1), plain, seg=32, coll=coll))
    dome = new_obj("ch_dome", C.m_sphere(32, 16, hemi=True), dome_m, (x0, y0, zb + 15.5), scale=(8.9, 8.9, 12.4), coll=coll)
    parts.append(dome)
    parts.append(cyl("ch_lantern", 1.9, 5.0, (x0, y0, zb + 27.2), plain, seg=12, coll=coll))
    parts.append(new_obj("ch_cap", C.m_sphere(12, 8, hemi=True), dome_m, (x0, y0, zb + 32.2), scale=(2.1, 2.1, 2.6), coll=coll))
    parts.append(cyl("ch_pole", 0.09, 9.0, (x0, y0, zb + 34.6), pbr("Pole", (0.7, 0.7, 0.7), 0.3, 1.0), seg=6, coll=coll))
    flag = box("ch_flag", (2.6, 0.04, 1.5), (x0 + 1.4, y0, zb + 41.6), pbr("Flag", (0.5, 0.05, 0.06), 0.8), coll=coll)
    parts.append(box("ch_roof_ew", (84, 19, 0.8), (x0, y0, z0 + H + 0.9), roof, coll=coll))
    parts.append(box("ch_roof_ns", (19, 68, 0.8), (x0, y0, z0 + H + 0.9), roof, coll=coll))
    return stone, flag


# ----------------------------------------------------------------------------
# Eads Bridge
# ----------------------------------------------------------------------------
def _tube_between(a, b, r, mat, coll, seg=8):
    a, b = Vector(a), Vector(b)
    d = b - a
    o = new_obj("tube", C.m_cyl(seg), mat, a, scale=(r, r, d.length), coll=coll)
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return o


def eads_bridge(y=EADS_Y, coll=None, west_end=-240.0, lamps=0.0, simple=False):
    """1874 steel-arch bridge: three ribbed spans (502, 520, 502 ft), road deck over rail deck.

    Returns the rail-deck height so the MetroLink train can be placed on it.
    """
    stone = C.ground_mat("EadsStone", (0.42, 0.37, 0.30), (0.27, 0.24, 0.20), scale=0.4, rough=0.9, bump=0.5)
    steel = pbr("EadsSteel", (0.11, 0.10, 0.095), 0.55, 0.6)
    deckm = pbr("EadsDeck", (0.16, 0.16, 0.165), 0.8)
    road_z, rail_z = 2.0, -4.6
    width = 14.0
    spans = [502 * FT, 520 * FT, 502 * FT]
    piers = [SHORE_W - 6.0]
    for s in spans:
        piers.append(piers[-1] + s + 9.0)        # 9 m pier thickness between spans
    objs = []
    east_end = piers[-1] + 330.0
    # decks
    objs.append(box("eads_road", (east_end - west_end, width + 2.0, 0.8), ((east_end + west_end) / 2, y, road_z - 0.8), deckm, coll=coll))
    objs.append(box("eads_rail", (piers[-1] - piers[0] + 30, width - 2.0, 0.5), ((piers[-1] + piers[0]) / 2, y, rail_z - 0.5), deckm, coll=coll))
    for sy in (1, -1):   # parapets and rail-deck edge girders
        objs.append(box("eads_parapet", (east_end - west_end, 0.25, 1.1), ((east_end + west_end) / 2, y + sy * (width / 2 + 0.9), road_z), steel, coll=coll))
        objs.append(box("eads_girder", (piers[-1] - piers[0], 0.3, 1.2), ((piers[-1] + piers[0]) / 2, y + sy * (width / 2 - 0.6), road_z - 2.0), steel, coll=coll))
    # piers and abutments with pointed cutwaters
    for i, px in enumerate(piers):
        big = i in (0, len(piers) - 1)
        w = 14.0 if big else 9.0
        objs.append(box("eads_pier", (w, width + 8.0, road_z - WATER_Z + 6.0), (px + (0 if not big else (-3 if i == 0 else 3)), y, WATER_Z - 6.0), stone, coll=coll))
        if not big:
            for sy in (1, -1):
                c = new_obj("eads_cutwater", C.m_cyl(3), stone, (px, y + sy * (width / 2 + 4.0), WATER_Z - 6.0),
                            (0, 0, math.pi / 2 * sy + math.pi / 6), (w / 2 * 1.15, w / 2 * 1.15, 14.0), coll=coll)
                objs.append(c)
    # ribbed arches: four ribs per span, each a pair of tubes braced together
    rise = 14.3
    for i, s in enumerate(spans):
        x0 = piers[i] + (7.0 if i == 0 else 4.5)
        x1 = piers[i + 1] - (7.0 if i == len(spans) - 1 else 4.5)
        seg = 10 if simple else 24
        for ry in ((-5.6, -1.9, 1.9, 5.6) if not simple else (-5.6, 5.6)):
            prev = None
            for k in range(seg + 1):
                u = k / seg
                xx = x0 + (x1 - x0) * u
                zz_low = rail_z - 4.6 - rise * (2 * u - 1) ** 2
                lo, hi = (xx, y + ry, zz_low), (xx, y + ry, zz_low + 3.7)
                if prev:
                    objs.append(_tube_between(prev[0], lo, 0.24, steel, coll))
                    objs.append(_tube_between(prev[1], hi, 0.24, steel, coll))
                    if not simple:
                        objs.append(_tube_between(prev[0], hi, 0.07, steel, coll, seg=4))
                if not simple or k % 2 == 0:
                    objs.append(_tube_between(lo, hi, 0.07, steel, coll, seg=4))
                    # spandrel columns up to the rail deck
                    if zz_low + 3.7 < rail_z - 1.0:
                        objs.append(_tube_between(hi, (xx, y + ry, rail_z - 0.5), 0.12, steel, coll, seg=4))
                prev = (lo, hi)
        # posts between rail deck and road deck (the open upper gallery)
        n = int((x1 - x0) / 7.5)
        for k in range(n + 1):
            xx = x0 + (x1 - x0) * k / n
            for sy in (1, -1):
                objs.append(box("eads_post", (0.28, 0.28, road_z - rail_z - 0.8), (xx, y + sy * (width / 2 - 0.6), rail_z), steel, coll=coll))
    # west approach: stone arcade over Laclede's Landing; east approach: trestle
    for k in range(int((piers[0] - 8 - west_end) / 16.0)):
        xx = west_end + 8 + k * 16.0
        objs.append(box("eads_arcade", (5.0, width + 2.0, road_z + 22), (xx, y, -22.0), stone, coll=coll))
    objs.append(box("eads_arcade_top", (piers[0] - west_end, width + 2.0, 3.2), ((piers[0] + west_end) / 2, y, road_z - 4.0), stone, coll=coll))
    for k in range(12):
        xx = piers[-1] + 20 + k * 26.0
        objs.append(box("eads_trestle", (2.0, width, road_z - WATER_Z + 2), (xx, y, WATER_Z - 2), steel, coll=coll))
    # road lamps
    for k in range(int((piers[-1] - west_end) / 30.0)):
        for sy in (1, -1):
            C.street_lamp((west_end + 15 + k * 30.0, y + sy * (width / 2 + 0.6), road_z), 5.0, power=lamps, coll=coll)
    eads = C.join(objs, "EadsBridge")
    return {"rail_z": rail_z + 0.05, "road_z": road_z, "x0": piers[0] - 40.0, "x1": east_end, "y": y, "obj": eads}


def girder_bridge(y, coll=None, name="PoplarBridge", truss=False):
    """Poplar Street (girder) or MLK (truss) bridge, simplified."""
    conc = pbr("BridgeConc", (0.42, 0.41, 0.39), 0.85)
    steel = pbr("BridgeSteel", (0.14, 0.2, 0.22) if truss else (0.25, 0.3, 0.28), 0.6, 0.4)
    objs = [box(name, (SHORE_E - SHORE_W + 700, 30 if not truss else 16, 4.0 if not truss else 1.0),
                ((SHORE_E + SHORE_W) / 2, y, 2.0 if not truss else 4.0), steel if not truss else conc, coll=coll)]
    n = 5 if not truss else 4
    for k in range(n):
        xx = SHORE_W + (SHORE_E - SHORE_W) * (k + 0.5) / n if not truss else SHORE_W + 20 + (SHORE_E - SHORE_W - 40) * k / (n - 1)
        objs.append(box(name + "_pier", (5, 22 if not truss else 14, 40), (xx, y, WATER_Z - 12), conc, coll=coll))
    if truss:
        x0, x1 = SHORE_W + 20, SHORE_E - 20
        m = 36
        for sy in (7.5, -7.5):
            prev = None
            for k in range(m + 1):
                u = k / m
                xx = x0 + (x1 - x0) * u
                hump = 16 + 20 * max(0.0, math.cos(u * 3 * math.pi * 2 - math.pi)) ** 2 if 0.16 < u < 0.84 else 12
                top = (xx, y + sy, 5 + hump)
                bot = (xx, y + sy, 5)
                objs.append(_tube_between(bot, top, 0.3, steel, coll, seg=4))
                if prev:
                    objs.append(_tube_between(prev[1], top, 0.35, steel, coll, seg=4))
                    objs.append(_tube_between(prev[0], top, 0.22, steel, coll, seg=4))
                prev = (bot, top)
    return C.join(objs, name)


# ----------------------------------------------------------------------------
# Downtown skyline (massing at real positions and heights; facades procedural)
# ----------------------------------------------------------------------------
def _tower(name, x, y, w, d, h, mat, coll, rot=0.0, z=0.0):
    return box(name, (w, d, h), (x, y, z), mat, rot=rot, coll=coll)


def downtown(coll=None, lit=0.0, detail=True):
    """Major downtown buildings. Returns facade materials so shots can light windows."""
    F = C.facade_mat
    mats = {
        "granite": F("FGranite", (0.50, 0.38, 0.33), (0.03, 0.04, 0.05), bay=2.4, floor=3.9, win_w=0.5, win_h=0.55, lit=lit, seed=1),
        "darkglass": F("FDarkGlass", (0.03, 0.035, 0.04), (0.02, 0.03, 0.04), bay=1.6, floor=3.9, win_w=0.9, win_h=0.72, lit=lit, wall_rough=0.3, seed=2, metal_glass=0.6),
        "pale": F("FPale", (0.66, 0.64, 0.58), (0.03, 0.04, 0.06), bay=2.0, floor=3.9, win_w=0.45, win_h=0.6, lit=lit, seed=3),
        "blueglass": F("FBlueGlass", (0.16, 0.22, 0.27), (0.03, 0.07, 0.11), bay=1.5, floor=3.9, win_w=0.88, win_h=0.8, lit=lit, wall_rough=0.25, seed=4, metal_glass=0.7),
        "tan": F("FTan", (0.56, 0.47, 0.36), (0.03, 0.035, 0.04), bay=3.0, floor=3.6, win_w=0.62, win_h=0.5, lit=lit, seed=5),
        "brick": F("FBrick", (0.32, 0.11, 0.07), (0.03, 0.035, 0.04), bay=2.6, floor=3.8, win_w=0.5, win_h=0.58, lit=lit, brick=True, seed=6),
        "cream": F("FCream", (0.72, 0.66, 0.54), (0.03, 0.035, 0.04), bay=2.2, floor=3.8, win_w=0.5, win_h=0.58, lit=lit, seed=7),
        "white": F("FWhite", (0.78, 0.77, 0.74), (0.03, 0.05, 0.07), bay=1.8, floor=3.7, win_w=0.7, win_h=0.5, lit=lit, seed=8),
        "limestone": F("FLime", (0.62, 0.58, 0.50), (0.03, 0.035, 0.04), bay=2.8, floor=4.2, win_w=0.42, win_h=0.62, lit=lit, seed=9),
    }
    copper = pbr("CopperRoof", (0.20, 0.36, 0.32), 0.5)
    darkroof = pbr("DarkRoof", (0.05, 0.05, 0.055), 0.7)
    T = lambda *a, **k: _tower(*a, coll=coll, **k)   # noqa: E731
    # --- named towers (x west of the Arch, y north) ---
    # One Metropolitan Square, 593 ft: granite shaft with a stepped, peaked crown
    T("MetSquare", -505, 205, 46, 46, 150, mats["granite"])
    T("MetSquare_s1", -505, 205, 36, 36, 14, mats["granite"], z=150)
    T("MetSquare_s2", -505, 205, 26, 26, 8, mats["granite"], z=164)
    new_obj("MetSquare_cap", C.m_cyl(4, 0.02, smooth=False), copper, (-505, 205, 172), (0, 0, math.pi / 4), (19, 19, 9), coll=coll)
    # AT&T Center, 588 ft pale slab; One AT&T (1926) stepped tower beside it
    T("ATTCenter", -865, 85, 52, 42, 179, mats["pale"])
    T("OneATT", -950, 150, 44, 40, 80, mats["limestone"])
    T("OneATT_2", -950, 150, 30, 28, 28, mats["limestone"], z=80)
    T("OneATT_3", -950, 150, 16, 16, 13, mats["limestone"], z=108)
    # Thomas F. Eagleton Courthouse, 557 ft with its domed crown
    T("Eagleton", -925, -135, 50, 44, 140, mats["cream"])
    T("Eagleton_2", -925, -135, 34, 30, 16, mats["cream"], z=140)
    new_obj("Eagleton_dome", C.m_sphere(24, 12, hemi=True), pbr("EagletonDome", (0.55, 0.56, 0.55), 0.3, 0.8),
            (-925, -135, 156), scale=(13, 13, 13), coll=coll)
    # One US Bank Plaza 484 ft, 600 Washington 375 ft, Laclede Gas 400 ft, Bank of America 384 ft
    T("USBank", -655, 385, 40, 40, 148, mats["darkglass"])
    T("SixHundredWash", -565, 475, 44, 38, 114, mats["blueglass"])
    T("LacledeGas", -690, 255, 34, 34, 122, mats["darkglass"])
    T("BofA", -745, -95, 42, 42, 117, mats["blueglass"])
    T("Equitable", -475, -105, 36, 30, 88, mats["darkglass"])
    T("PeabodyPlaza", -655, -40, 44, 34, 68, mats["pale"])
    T("Deloitte", -570, 105, 38, 38, 84, mats["blueglass"])
    T("RailwayExchange", -610, 300, 60, 60, 84, mats["cream"])
    T("Marriott", -830, 420, 40, 34, 78, mats["tan"])
    T("Wainwright", -655, 95, 38, 34, 41, mats["brick"])
    T("ChemicalBldg", -745, 245, 30, 30, 71, mats["brick"])
    T("Arcade", -785, 300, 40, 50, 70, mats["cream"])
    T("Paul Brown", -830, 250, 36, 40, 60, mats["brick"])
    T("OneFinancial", -485, 400, 44, 60, 52, mats["blueglass"])
    T("StLouisPlace", -655, 180, 36, 40, 98, mats["granite"])
    T("OneCardinalWay", -565, -255, 30, 44, 96, mats["blueglass"])
    T("Hilton_Ballpark", -565, -170, 36, 30, 84, mats["tan"])
    # Hyatt Regency at the Arch (two slabs right behind the Old Courthouse block)
    T("Hyatt_N", -385, 135, 30, 52, 62, mats["tan"])
    T("Hyatt_S", -385, 95, 24, 30, 44, mats["tan"])
    T("GatewayTower", -335, -115, 34, 34, 80, mats["pale"])
    T("Drury_Plaza", -385, -110, 40, 46, 38, mats["limestone"])
    # Mansion House trio along 4th Street
    for i, yy in enumerate((255, 345, 435)):
        T("MansionHouse%d" % i, -350, yy, 22, 58, 84, mats["white"])
    # Millennium Hotel: the round tower south of the grounds
    cyl("Millennium", 18, 100, (-385, -235, 0), mats["white"], seg=28, coll=coll)
    cyl("Millennium_top", 19.5, 6, (-385, -235, 100), darkroof, seg=28, coll=coll)
    T("Millennium_low", -385, -300, 30, 40, 36, mats["white"])
    # Civil Courts Building on the Arch axis: column ring and stepped pyramid
    T("CivilCourts", -1015, 0, 44, 44, 78, mats["limestone"])
    T("CivilCourts_col", -1015, 0, 36, 36, 16, mats["limestone"], z=78)
    for k in range(7):
        T("CivilCourts_pyr%d" % k, -1015, 0, 36 - k * 4.6, 36 - k * 4.6, 2.6, pbr("CourtsPyramid", (0.6, 0.6, 0.57), 0.5), z=94 + k * 2.6)
    # Busch Stadium: brick bowl open to the north-east
    if detail:
        bowl = mats["brick"]
        steel = pbr("StadiumSteel", (0.16, 0.2, 0.17), 0.5, 0.5)
        cx, cy, R = -625, -390, 118
        for k in range(40):
            a = math.radians(35 + k * 290 / 40)
            if 200 < math.degrees(a) % 360 < 250:
                continue
            xx, yy = cx + math.cos(a) * R, cy + math.sin(a) * R
            T("Busch_%d" % k, xx, yy, 30, 20, 34, bowl, rot=a + math.pi / 2)
            T("Busch_deck%d" % k, cx + math.cos(a) * (R - 20), cy + math.sin(a) * (R - 20), 30, 24, 3, steel, rot=a + math.pi / 2, z=24)
        box("Busch_field", (150, 150, 0.3), (cx, cy, 0.05), pbr("Field", (0.05, 0.22, 0.05), 0.9), coll=coll)
        for a in (0.6, 2.2, 3.6, 5.2):
            T("Busch_light", cx + math.cos(a) * (R + 6), cy + math.sin(a) * (R + 6), 2, 2, 52, steel)
            T("Busch_lightbank", cx + math.cos(a) * (R + 4), cy + math.sin(a) * (R + 4), 14, 2, 7,
              C.emissive("StadiumLights%g" % lit, (1, 0.97, 0.9), 0.5 + 25 * lit), z=50, rot=a + math.pi / 2)
    # Laclede's Landing warehouses between Eads and MLK, Lumiere Place tower beyond
    rnd = random.Random(5)
    for i in range(4):
        for j in range(3):
            T("Landing%d%d" % (i, j), -230 + i * 78 + 20, EADS_Y + 50 + j * 85, 58, 62, rnd.uniform(18, 30), mats["brick"])
    T("Lumiere", -270, MLK_Y + 150, 36, 60, 82, mats["blueglass"])
    T("FourSeasons", -330, MLK_Y + 70, 30, 44, 70, mats["pale"])
    # --- generic infill on the street grid so the skyline has depth ---
    xs = [-475, -565, -655, -745, -835, -925, -1015, -1105, -1195, -1285]
    ys = [-490, -400, -300, -205, 205, 300, 395, 490, 585, 680, 775]
    named = [(-505, 205), (-865, 85), (-950, 150), (-925, -135), (-655, 385), (-565, 475), (-690, 255), (-745, -95),
             (-475, -105), (-655, -40), (-570, 105), (-610, 300), (-830, 420), (-655, 95), (-745, 245), (-785, 300),
             (-830, 250), (-485, 400), (-655, 180), (-565, -255), (-565, -170), (-1015, 0), (-625, -390)]
    keys = ["brick", "cream", "tan", "pale", "limestone", "granite", "blueglass", "darkglass"]
    for x in xs:
        for yv in ys + [-110, -15, 110]:
            if any(abs(x - nx) < 70 and abs(yv - ny) < 70 for nx, ny in named):
                continue
            if abs(yv) < 60 and x > -1000:        # keep the Gateway Mall axis open
                continue
            if (x + 625) ** 2 + (yv + 390) ** 2 < 150 ** 2:
                continue
            h = rnd.choice([18, 24, 30, 36, 44, 52, 60, 70]) * (1.0 if x > -1100 else 0.6)
            w, d = rnd.uniform(40, 62), rnd.uniform(40, 62)
            T("Infill", x + rnd.uniform(-6, 6), yv + rnd.uniform(-6, 6), w, d, h, mats[rnd.choice(keys)])
    return mats

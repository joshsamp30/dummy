"""Shared helpers for the Local Howl "St. Louis, rebuilt in 3D" film.

Everything is procedural: geometry, materials, characters and motion are
built from Python so each render worker can rebuild the exact same scene.
Units are metres. X = east (toward the river), Y = north, Z = up.
"""
import math
import os
import random

import bpy
import bmesh
from mathutils import Matrix, Vector

FT = 0.3048
FPS = 24
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

# Local Howl palette (sampled from the logo and the brand wolf imagery).
NAVY = (0.006, 0.010, 0.030)
PAL = {
    "navy": (0.012, 0.020, 0.060),
    "blue": (0.020, 0.090, 0.550),
    "pink": (0.860, 0.300, 0.340),
    "blush": (0.900, 0.560, 0.520),
    "teal": (0.130, 0.480, 0.420),
    "mint": (0.420, 0.720, 0.600),
    "yellow": (0.850, 0.560, 0.080),
    "cream": (0.870, 0.790, 0.640),
    "tan": (0.640, 0.480, 0.290),
    "red": (0.620, 0.060, 0.040),
    "white": (0.850, 0.850, 0.830),
    "char": (0.030, 0.030, 0.035),
}


# ----------------------------------------------------------------------------
# scene / render setup
# ----------------------------------------------------------------------------
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mesh_cache.clear()
    _mat_cache.clear()
    return bpy.context.scene


def setup_render(scene, width=3840, height=2160, samples=96, gpu=False):
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    c = scene.cycles
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.max_bounces = 6
    c.diffuse_bounces = 2
    c.glossy_bounces = 4
    c.transmission_bounces = 4
    c.volume_bounces = 0
    c.transparent_max_bounces = 6
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = 6.0
    c.sample_clamp_direct = 0.0
    c.use_denoising = True
    for d in ("OPTIX", "OPENIMAGEDENOISE") if gpu else ("OPENIMAGEDENOISE",):
        try:
            c.denoiser = d
            break
        except TypeError:
            continue
    try:
        c.use_light_tree = True
    except Exception:
        pass
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        try:
            scene.view_settings.view_transform = "Filmic"
        except TypeError:
            pass
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 96
    scene.render.use_persistent_data = True
    if gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                n = 0
                for dev in prefs.devices:
                    dev.use = dev.type == kind
                    n += dev.use
                if n:
                    c.device = "GPU"
                    print("cycles device:", kind, "x", n)
                    break
            except Exception as e:  # noqa
                print("device", kind, "unavailable", e)
    return scene


# ----------------------------------------------------------------------------
# node helper
# ----------------------------------------------------------------------------
class NB:
    """Tiny node-graph builder so shaders read like expressions."""

    def __init__(self, tree):
        self.t = tree
        self.n = tree.nodes
        self.l = tree.links

    def new(self, kind, **props):
        node = self.n.new(kind)
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def set(self, sock, val):
        if isinstance(val, bpy.types.NodeSocket):
            self.l.new(val, sock)
        elif val is not None:
            if isinstance(val, (tuple, list)) and len(val) == 3 and sock.type == "RGBA":
                val = (*val, 1.0)
            sock.default_value = val

    def math(self, op, a, b=None, c=None, clamp=False):
        if op == "SMOOTHSTEP":      # smoothstep(x, edge0, edge1) via Map Range
            n = self.new("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
            self.set(n.inputs[0], a)
            self.set(n.inputs[1], b)
            self.set(n.inputs[2], c)
            return n.outputs[0]
        n = self.new("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        self.set(n.inputs[1], b)
        self.set(n.inputs[2], c)
        return n.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        n = self.new("ShaderNodeVectorMath", operation=op)
        self.set(n.inputs[0], a)
        self.set(n.inputs[1], b)
        if scale is not None:
            self.set(n.inputs[3], scale)
        return n.outputs["Value"] if op in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else n.outputs[0]

    def sep(self, v):
        n = self.new("ShaderNodeSeparateXYZ")
        self.set(n.inputs[0], v)
        return n.outputs

    def comb(self, x, y, z):
        n = self.new("ShaderNodeCombineXYZ")
        self.set(n.inputs[0], x)
        self.set(n.inputs[1], y)
        self.set(n.inputs[2], z)
        return n.outputs[0]

    def mix(self, fac, a, b, kind="RGBA", blend="MIX"):
        n = self.new("ShaderNodeMix", data_type=kind)
        if kind == "RGBA":
            n.blend_type = blend
            self.set(n.inputs[0], fac)
            self.set(n.inputs[6], a)
            self.set(n.inputs[7], b)
            return n.outputs[2]
        self.set(n.inputs[0], fac)
        self.set(n.inputs[2], a)
        self.set(n.inputs[3], b)
        return n.outputs[0]

    def noise(self, vec=None, scale=5.0, detail=2.0, rough=0.5, w=None, dims="3D"):
        n = self.new("ShaderNodeTexNoise", noise_dimensions=dims)
        if vec is not None:
            self.set(n.inputs["Vector"], vec)
        if w is not None:
            self.set(n.inputs["W"], w)
        self.set(n.inputs["Scale"], scale)
        self.set(n.inputs["Detail"], detail)
        self.set(n.inputs["Roughness"], rough)
        return n.outputs

    def white(self, vec):
        n = self.new("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        self.set(n.inputs["Vector"], vec)
        return n.outputs

    def ramp(self, fac, stops):
        n = self.new("ShaderNodeValToRGB")
        cr = n.color_ramp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, col) in zip(cr.elements, stops):
            e.position = p
            e.color = (*col, 1.0) if len(col) == 3 else col
        self.set(n.inputs[0], fac)
        return n.outputs[0]

    def bump(self, height, strength=0.3, distance=0.05, normal=None):
        n = self.new("ShaderNodeBump")
        self.set(n.inputs["Strength"], strength)
        self.set(n.inputs["Distance"], distance)
        self.set(n.inputs["Height"], height)
        if normal is not None:
            self.set(n.inputs["Normal"], normal)
        return n.outputs[0]


_mat_cache = {}


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    nb = NB(nt)
    out = nb.new("ShaderNodeOutputMaterial")
    return m, nb, out


def pbr(name, color, rough=0.6, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0,
        transmission=0.0, ior=1.45, coat=0.0, spec=None):
    """Cached principled material."""
    key = (name, tuple(color), rough, metal, emit, emit_strength, alpha, transmission, coat)
    if key in _mat_cache:
        return _mat_cache[key]
    m, nb, out = new_mat(name)
    b = nb.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color[:3], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["IOR"].default_value = ior
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["Coat Weight"].default_value = coat
    if spec is not None:
        b.inputs["Specular IOR Level"].default_value = spec
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit[:3], 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    nb.l.new(b.outputs[0], out.inputs[0])
    _mat_cache[key] = m
    return m


def emissive(name, color, strength):
    key = ("EMIT", name, tuple(color), strength)
    if key in _mat_cache:
        return _mat_cache[key]
    m, nb, out = new_mat(name)
    e = nb.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color[:3], 1)
    e.inputs[1].default_value = strength
    nb.l.new(e.outputs[0], out.inputs[0])
    _mat_cache[key] = m
    return m


# ----------------------------------------------------------------------------
# mesh helpers
# ----------------------------------------------------------------------------
_mesh_cache = {}


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def new_obj(name, mesh, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), parent=None, coll=None):
    o = bpy.data.objects.new(name, mesh)
    o.location = loc
    o.rotation_euler = rot
    o.scale = scale if not isinstance(scale, (int, float)) else (scale,) * 3
    if parent is not None:
        o.parent = parent
    if mat is not None and mesh is not None:
        mats = mat if isinstance(mat, (list, tuple)) else [mat]
        while len(mesh.materials) < len(mats):
            mesh.materials.append(None)
        for i, m in enumerate(mats):
            o.material_slots[i].link = "OBJECT"
            o.material_slots[i].material = m
    link(o, coll)
    return o


def empty(name, loc=(0, 0, 0), parent=None, coll=None):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    if parent is not None:
        o.parent = parent
    link(o, coll)
    return o


def bm_to_mesh(bm, name, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return me


def mesh_from(name, verts, faces, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return me


def cached(key, fn):
    if key not in _mesh_cache:
        _mesh_cache[key] = fn()
    return _mesh_cache[key]


def m_box(bevel=0.0):
    """Unit cube centred on origin (1 m per side)."""
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        if bevel > 0:
            bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect="EDGES")
        return bm_to_mesh(bm, "box%g" % bevel, smooth=False)
    return cached(("box", bevel), mk)


def m_box0():
    """Unit cube with its base on z=0."""
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.5))
        return bm_to_mesh(bm, "box0")
    return cached("box0", mk)


def m_cyl(seg=24, r2=1.0, base0=True, smooth=True):
    """Unit cylinder/frustum: radius 1 at base, r2 at top, height 1."""
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=1.0, radius2=max(r2, 1e-4), depth=1.0)
        if base0:
            bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.5))
        me = bm_to_mesh(bm, "cyl", smooth=False)
        if smooth:
            for p in me.polygons:
                p.use_smooth = len(p.vertices) == 4
        return me
    return cached(("cyl", seg, r2, base0, smooth), mk)


def m_sphere(seg=16, rings=10, hemi=False):
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
        if hemi:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True)
        return bm_to_mesh(bm, "sph", smooth=True)
    return cached(("sph", seg, rings, hemi), mk)


def m_capsule(r=0.5, length=1.0, seg=10):
    """Capsule along -Z from origin (pivot at the top): limbs hang from joints."""
    def mk():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=6, radius=r)
        for v in bm.verts:
            if v.co.z < -1e-6:
                v.co.z -= length
        return bm_to_mesh(bm, "cap", smooth=True)
    return cached(("cap", r, length, seg), mk)


def m_plane():
    def mk():
        return mesh_from("plane", [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)], [(0, 1, 2, 3)])
    return cached("plane", mk)


def m_torus(R=1.0, r=0.1, seg=24, sub=8):
    def mk():
        verts, faces = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            for j in range(sub):
                b = 2 * math.pi * j / sub
                x = (R + r * math.cos(b)) * math.cos(a)
                z = (R + r * math.cos(b)) * math.sin(a)
                verts.append((x, r * math.sin(b), z))
        for i in range(seg):
            for j in range(sub):
                a, b = i * sub + j, i * sub + (j + 1) % sub
                c, d = ((i + 1) % seg) * sub + (j + 1) % sub, ((i + 1) % seg) * sub + j
                faces.append((a, b, c, d))
        return mesh_from("torus", verts, faces, smooth=True)
    return cached(("torus", R, r, seg, sub), mk)


def box(name, size, loc, mat, rot=0.0, parent=None, coll=None, base0=True, bevel=0.0):
    """Axis box of `size` (x, y, z) whose base sits at loc.z (if base0).

    Plain boxes get real-size meshes (object scale 1) so object-space shader
    coordinates are in metres; bevelled ones scale a shared unit mesh.
    """
    if bevel:
        lz = loc[2] + (size[2] / 2 if base0 else 0)
        return new_obj(name, m_box(bevel), mat, (loc[0], loc[1], lz), (0, 0, rot), size, parent, coll)
    key = ("rbox", round(size[0], 3), round(size[1], 3), round(size[2], 3), base0)

    def mk():
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= size[0]
            v.co.y *= size[1]
            v.co.z = (v.co.z + (0.5 if base0 else 0.0)) * size[2]
        return bm_to_mesh(bm, "rbox")
    return new_obj(name, cached(key, mk), mat, loc, (0, 0, rot), (1, 1, 1), parent, coll)


def cyl(name, r, h, loc, mat, r2=1.0, seg=24, parent=None, coll=None, rot=(0, 0, 0)):
    """Real-size cylinder / frustum standing on loc."""
    key = ("rcyl", round(r, 3), round(h, 3), r2, seg)

    def mk():
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=max(r * r2, 1e-4), depth=h)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
        me = bm_to_mesh(bm, "rcyl")
        for p in me.polygons:
            p.use_smooth = len(p.vertices) == 4
        return me
    return new_obj(name, cached(key, mk), mat, loc, rot, (1, 1, 1), parent, coll)


def join(objs, name=None):
    """Join objects into one mesh object (keeps material slots)."""
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) == 1:
        if name:
            objs[0].name = name
        return objs[0]
    ctx = bpy.context
    for o in ctx.scene.objects:
        o.select_set(False)
    # make meshes single-user and bake object-linked materials into data
    for o in objs:
        mats = [s.material for s in o.material_slots]
        o.data = o.data.copy()
        for i, m in enumerate(mats):
            o.material_slots[i].link = "DATA"
            o.material_slots[i].material = m
        o.select_set(True)
    with ctx.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    if name:
        objs[0].name = name
    return objs[0]


def polygon_plane(name, pts, z, mat, coll=None):
    """Flat n-gon from 2D points."""
    me = mesh_from(name, [(x, y, 0) for x, y in pts], [tuple(range(len(pts)))])
    return new_obj(name, me, mat, (0, 0, z), coll=coll)


def strip_mesh(name, centre_pts, width, z, mat, coll=None):
    """Ribbon (path / road) following 2D centre points."""
    verts, faces = [], []
    n = len(centre_pts)
    for i, (x, y) in enumerate(centre_pts):
        x0, y0 = centre_pts[max(i - 1, 0)]
        x1, y1 = centre_pts[min(i + 1, n - 1)]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln * width / 2, dx / ln * width / 2
        verts += [(x + nx, y + ny, 0), (x - nx, y - ny, 0)]
    for i in range(n - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    return new_obj(name, mesh_from(name, verts, faces), mat, (0, 0, z), coll=coll)


# ----------------------------------------------------------------------------
# sky, sun, haze
# ----------------------------------------------------------------------------
def make_world(scene, horizon, mid, zenith, strength=1.0, cloud=0.45, cloud_col=(1, 0.8, 0.7),
               cloud_dark=(0.3, 0.3, 0.4), ground=(0.05, 0.05, 0.05), sun_dir=None, sun_glow=None,
               glow_power=40.0, glow_strength=3.0, cloud_scale=1.6, seed=0.0, stars=0.0):
    """Art-directed gradient sky with a procedural cloud deck and sun glow."""
    w = bpy.data.worlds.new("Sky")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    nb = NB(nt)
    out = nb.new("ShaderNodeOutputWorld")
    tc = nb.new("ShaderNodeTexCoord")
    d = nb.vmath("NORMALIZE", tc.outputs["Generated"])
    x, y, z = nb.sep(d)
    zc = nb.math("MAXIMUM", z, 0.0)
    grad = nb.math("POWER", zc, 0.45)
    col = nb.ramp(grad, [(0.0, horizon), (0.28, mid), (1.0, zenith)])
    # cloud deck projected on a plane overhead
    inv = nb.math("DIVIDE", 1.0, nb.math("ADD", zc, 0.12))
    cu = nb.math("MULTIPLY", x, inv)
    cv = nb.math("MULTIPLY", y, inv)
    cvec = nb.comb(cu, nb.math("MULTIPLY", cv, 2.2), seed)
    n1 = nb.noise(cvec, scale=cloud_scale, detail=6.0, rough=0.58)[0]
    cmask = nb.math("SMOOTHSTEP", n1, 1.0 - cloud, 1.0 - cloud + 0.22)
    cmask = nb.math("MULTIPLY", cmask, nb.math("SMOOTHSTEP", z, 0.01, 0.12))
    shade = nb.noise(cvec, scale=cloud_scale * 2.3, detail=3.0)[0]
    ccol = nb.mix(shade, cloud_dark, cloud_col)
    col = nb.mix(nb.math("MULTIPLY", cmask, 0.85), col, ccol)
    if stars > 0:
        sn = nb.noise(d, scale=380.0, detail=0.0)[0]
        st = nb.math("MULTIPLY", nb.math("SMOOTHSTEP", sn, 0.80, 0.84), stars)
        st = nb.math("MULTIPLY", st, nb.math("SUBTRACT", 1.0, cmask))
        col = nb.mix(st, col, (1, 1, 1), blend="ADD")
    if sun_dir is not None and sun_glow is not None:
        sd = Vector(sun_dir).normalized()
        dot = nb.math("MAXIMUM", nb.vmath("DOT_PRODUCT", d, tuple(sd)), 0.0)
        g = nb.math("MULTIPLY", nb.math("POWER", dot, glow_power), glow_strength)
        g2 = nb.math("MULTIPLY", nb.math("POWER", dot, 4.0), glow_strength * 0.12)
        col = nb.mix(nb.math("ADD", g, g2), col, sun_glow, blend="ADD")
    # below the horizon
    below = nb.math("SMOOTHSTEP", z, -0.06, 0.0)
    col = nb.mix(below, ground, col)
    bg = nb.new("ShaderNodeBackground")
    nb.l.new(col, bg.inputs[0])
    bg.inputs[1].default_value = strength
    nb.l.new(bg.outputs[0], out.inputs[0])
    scene.world = w
    return w, bg


def make_sun(scene, direction, color=(1, 0.9, 0.8), strength=3.0, angle=1.0):
    """Sun lamp shining FROM `direction` (vector pointing at the sun)."""
    ld = bpy.data.lights.new("Sun", "SUN")
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(angle)
    o = bpy.data.objects.new("Sun", ld)
    o.rotation_euler = Vector(direction).normalized().to_track_quat("Z", "Y").to_euler()
    link(o)
    return o


def haze_box(name, lo, hi, density=0.0008, color=(0.8, 0.8, 0.85), aniso=0.3, noise_scale=None,
             height_fade=None):
    """Volume box for aerial perspective / river mist."""
    m, nb, out = new_mat(name)
    vs = nb.new("ShaderNodeVolumeScatter")
    vs.inputs["Color"].default_value = (*color, 1)
    vs.inputs["Anisotropy"].default_value = aniso
    dens = density
    if noise_scale or height_fade:
        tc = nb.new("ShaderNodeTexCoord")
        pos = nb.new("ShaderNodeNewGeometry").outputs["Position"]
        dsock = None
        if noise_scale:
            nz = nb.noise(pos, scale=noise_scale, detail=3.0, w=0.0, dims="4D")
            m["_w_node"] = nz[0].node.name
            dsock = nb.math("SMOOTHSTEP", nz[0], 0.35, 0.75)
        if height_fade:
            z0, z1 = height_fade
            hz = nb.math("SMOOTHSTEP", nb.sep(pos)[2], z1, z0)
            dsock = hz if dsock is None else nb.math("MULTIPLY", dsock, hz)
        dens = nb.math("MULTIPLY", dsock, density)
    nb.set(vs.inputs["Density"], dens)
    nb.l.new(vs.outputs[0], out.inputs["Volume"])
    size = [hi[i] - lo[i] for i in range(3)]
    o = new_obj(name, m_box(), m, [(hi[i] + lo[i]) / 2 for i in range(3)], scale=size)
    return o


# ----------------------------------------------------------------------------
# shared procedural materials
# ----------------------------------------------------------------------------
def water_mat(name="Water", color=(0.045, 0.040, 0.028), rough=0.04, scale=0.07, strength=0.5,
              flow=(1.0, 0.0), tint=None):
    """River / pond water: mirror-like with animated ripples (drive the W input)."""
    m, nb, out = new_mat(name)
    b = nb.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = 1.33
    b.inputs["Specular IOR Level"].default_value = 1.0
    pos = nb.new("ShaderNodeNewGeometry").outputs["Position"]
    drift = nb.new("ShaderNodeValue")
    drift.label = "time"
    drift.outputs[0].default_value = 0.0
    off = nb.comb(nb.math("MULTIPLY", drift.outputs[0], flow[0]),
                  nb.math("MULTIPLY", drift.outputs[0], flow[1]), 0.0)
    p = nb.vmath("ADD", pos, off)
    w = nb.math("MULTIPLY", drift.outputs[0], 0.35)
    n1 = nb.noise(p, scale=scale, detail=4.0, rough=0.6, w=w, dims="4D")[0]
    n2 = nb.noise(p, scale=scale * 7.0, detail=2.0, rough=0.5, w=nb.math("MULTIPLY", w, 2.0), dims="4D")[0]
    h = nb.math("ADD", n1, nb.math("MULTIPLY", n2, 0.25))
    nrm = nb.bump(h, strength=strength, distance=1.0)
    nb.l.new(nrm, b.inputs["Normal"])
    nb.l.new(b.outputs[0], out.inputs[0])
    m["_time_node"] = drift.name
    return m


def set_time(mat, t):
    """Advance a material's 'time' value (water ripples, mist drift)."""
    name = mat.get("_time_node")
    if name:
        mat.node_tree.nodes[name].outputs[0].default_value = t
    wn = mat.get("_w_node")
    if wn:
        mat.node_tree.nodes[wn].inputs["W"].default_value = t


def steel_mat(name="ArchSteel"):
    """Stainless steel skin of the Arch: brushed, panelised, near-mirror."""
    m, nb, out = new_mat(name)
    b = nb.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.78, 0.78, 0.79, 1)
    b.inputs["Metallic"].default_value = 1.0
    uv = nb.new("ShaderNodeTexCoord").outputs["UV"]
    u, v, _ = nb.sep(uv)
    # plate seams: UV v runs along the leg (1 unit = 1 m), u across the face
    pv = nb.math("FRACT", nb.math("DIVIDE", v, 1.8))
    seam_v = nb.math("SMOOTHSTEP", nb.math("ABSOLUTE", nb.math("SUBTRACT", pv, 0.5)), 0.485, 0.5)
    pu = nb.math("FRACT", nb.math("MULTIPLY", u, 0.57))
    seam_u = nb.math("SMOOTHSTEP", nb.math("ABSOLUTE", nb.math("SUBTRACT", pu, 0.5)), 0.492, 0.5)
    seam = nb.math("MAXIMUM", seam_v, seam_u)
    cell = nb.comb(nb.math("FLOOR", nb.math("MULTIPLY", u, 0.57)), nb.math("FLOOR", nb.math("DIVIDE", v, 1.8)), 0.0)
    rnd = nb.white(cell)[0]
    rough = nb.math("ADD", 0.07, nb.math("MULTIPLY", rnd, 0.07))
    rough = nb.math("ADD", rough, nb.math("MULTIPLY", seam, 0.25))
    nb.l.new(rough, b.inputs["Roughness"])
    b.inputs["Anisotropic"].default_value = 0.35
    # slight per-plate warp ("oil canning") so reflections break like the real skin
    wob = nb.noise(nb.comb(nb.math("MULTIPLY", u, 0.57), nb.math("DIVIDE", v, 1.8), 0.0), scale=1.0, detail=1.0)[0]
    hgt = nb.math("ADD", nb.math("MULTIPLY", wob, 0.6), nb.math("MULTIPLY", seam, -1.0))
    nb.l.new(nb.bump(hgt, strength=0.12, distance=0.02), b.inputs["Normal"])
    nb.l.new(b.outputs[0], out.inputs[0])
    return m


def facade_mat(name, wall=(0.5, 0.5, 0.5), glass=(0.05, 0.07, 0.09), bay=3.0, floor=3.8,
               win_w=0.7, win_h=0.6, lit=0.0, lit_col=(1.0, 0.72, 0.38), lit_strength=6.0,
               wall_rough=0.75, glass_rough=0.06, brick=False, seed=0.0, base=0.0, metal_glass=0.0):
    """Procedural window-grid facade in object space. `lit` = fraction of lit windows.

    The lit fraction is exposed through a Value node so shots can switch the
    city's windows on over time.
    """
    m, nb, out = new_mat(name)
    geo = nb.new("ShaderNodeNewGeometry")
    tc = nb.new("ShaderNodeTexCoord")
    ox, oy, oz = nb.sep(tc.outputs["Object"])
    # object-space normal picks the horizontal axis that runs along this wall
    nrm = nb.new("ShaderNodeVectorTransform", vector_type="NORMAL", convert_from="WORLD", convert_to="OBJECT")
    nb.l.new(geo.outputs["Normal"], nrm.inputs[0])
    nx, ny, nz = nb.sep(nrm.outputs[0])
    use_y = nb.math("GREATER_THAN", nb.math("ABSOLUTE", nx), nb.math("ABSOLUTE", ny))
    hx, hy, hz = ox, oy, oz       # boxes carry real-size meshes, so object space is metres
    u = nb.mix(use_y, hx, hy, kind="FLOAT")
    uc = nb.math("DIVIDE", u, bay)
    vc = nb.math("DIVIDE", nb.math("SUBTRACT", hz, base), floor)
    fu = nb.math("FRACT", uc)
    fv = nb.math("FRACT", vc)
    mu = nb.math("LESS_THAN", nb.math("ABSOLUTE", nb.math("SUBTRACT", fu, 0.5)), win_w / 2)
    mv = nb.math("LESS_THAN", nb.math("ABSOLUTE", nb.math("SUBTRACT", fv, 0.52)), win_h / 2)
    wall_side = nb.math("LESS_THAN", nb.math("ABSOLUTE", nz), 0.5)
    above = nb.math("GREATER_THAN", vc, 0.0)
    win = nb.math("MULTIPLY", nb.math("MULTIPLY", mu, mv), nb.math("MULTIPLY", wall_side, above))
    cell = nb.comb(nb.math("FLOOR", uc), nb.math("FLOOR", vc), nb.math("ADD", use_y, seed))
    rnd = nb.white(cell)
    litv = nb.new("ShaderNodeValue")
    litv.outputs[0].default_value = lit
    m["_lit_node"] = litv.name
    is_lit = nb.math("MULTIPLY", win, nb.math("LESS_THAN", rnd[0], litv.outputs[0]))
    b = nb.new("ShaderNodeBsdfPrincipled")
    wcol = wall
    wall_n = None
    if brick:
        bt = nb.new("ShaderNodeTexBrick")
        bvec = nb.comb(u, hz, 0.0)
        nb.l.new(bvec, bt.inputs["Vector"])
        bt.inputs["Scale"].default_value = 4.0
        bt.inputs["Color1"].default_value = (*wall, 1)
        bt.inputs["Color2"].default_value = (wall[0] * 0.75, wall[1] * 0.7, wall[2] * 0.7, 1)
        bt.inputs["Mortar"].default_value = (wall[0] * 1.5 + 0.1, wall[1] * 1.5 + 0.1, wall[2] * 1.5 + 0.1, 1)
        bt.inputs["Mortar Size"].default_value = 0.012
        bt.inputs["Brick Width"].default_value = 0.6
        bt.inputs["Row Height"].default_value = 0.2
        wcol = bt.outputs["Color"]
        wall_n = nb.bump(bt.outputs["Fac"], strength=0.4, distance=-0.01)
    else:
        grime = nb.noise(tc.outputs["Object"], scale=3.0, detail=3.0)[0]
        wcol = nb.mix(nb.math("MULTIPLY", grime, 0.25), wall, tuple(c * 0.7 for c in wall))
    gcol = nb.mix(nb.math("MULTIPLY", rnd[0], 0.5), glass, tuple(min(1, c * 1.8 + 0.01) for c in glass))
    col = nb.mix(win, wcol, gcol)
    nb.l.new(col, b.inputs["Base Color"])
    nb.l.new(nb.mix(win, wall_rough, glass_rough, kind="FLOAT"), b.inputs["Roughness"])
    nb.l.new(nb.math("MULTIPLY", win, metal_glass), b.inputs["Metallic"])
    if wall_n is not None:
        nrm_mix = nb.new("ShaderNodeMix", data_type="VECTOR")
        nb.l.new(win, nrm_mix.inputs[0])
        nb.l.new(wall_n, nrm_mix.inputs[4])
        nb.l.new(geo.outputs["Normal"], nrm_mix.inputs[5])
        nb.l.new(nrm_mix.outputs[1], b.inputs["Normal"])
    warm = nb.mix(rnd[1].node.outputs["Color"], lit_col, (lit_col[0], lit_col[1] * 1.15, min(1, lit_col[2] * 2.2)))
    nb.l.new(warm, b.inputs["Emission Color"])
    es = nb.math("MULTIPLY", is_lit, nb.math("MULTIPLY", lit_strength, nb.math("ADD", 0.35, rnd[0])))
    nb.l.new(es, b.inputs["Emission Strength"])
    nb.l.new(b.outputs[0], out.inputs[0])
    return m


def set_lit(mat, frac):
    n = mat.get("_lit_node")
    if n:
        mat.node_tree.nodes[n].outputs[0].default_value = frac


def ground_mat(name, c1, c2, scale=0.05, rough=0.9, bump=0.2, detail=4.0):
    m, nb, out = new_mat(name)
    b = nb.new("ShaderNodeBsdfPrincipled")
    pos = nb.new("ShaderNodeNewGeometry").outputs["Position"]
    n1 = nb.noise(pos, scale=scale, detail=detail)[0]
    n2 = nb.noise(pos, scale=scale * 40, detail=2.0)[0]
    f = nb.math("ADD", nb.math("MULTIPLY", n1, 0.7), nb.math("MULTIPLY", n2, 0.3))
    nb.l.new(nb.mix(f, c1, c2), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if bump:
        nb.l.new(nb.bump(n2, strength=bump, distance=0.03), b.inputs["Normal"])
    nb.l.new(b.outputs[0], out.inputs[0])
    return m


def image_mat(name, path, emit=0.0, rough=0.5, alpha=True):
    """Image-textured material (used for the Local Howl logo decals)."""
    m, nb, out = new_mat(name)
    img = bpy.data.images.load(path, check_existing=True)
    tex = nb.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "CLIP"
    b = nb.new("ShaderNodeBsdfPrincipled")
    nb.l.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if alpha:
        nb.l.new(tex.outputs["Alpha"], b.inputs["Alpha"])
    if emit:
        nb.l.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    nb.l.new(b.outputs[0], out.inputs[0])
    return m


def decal(name, path, width, loc, rot=(math.pi / 2, 0, 0), emit=0.0, parent=None, coll=None, aspect=None):
    """Upright image plane. Default faces -Y."""
    mat = image_mat("decal_" + os.path.basename(path) + ("_e%g" % emit), path, emit=emit)
    img = mat.node_tree.nodes[[n.name for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"][0]].image
    asp = aspect or (img.size[1] / max(img.size[0], 1))
    me = cached(("uvplane",), _uv_plane)
    return new_obj(name, me, mat, loc, rot, (width, width * asp, 1), parent, coll)


def _uv_plane():
    me = mesh_from("uvplane", [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, co in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = co
    return me


# ----------------------------------------------------------------------------
# trees, lamps
# ----------------------------------------------------------------------------
def _foliage_mesh(seed):
    def mk():
        rnd = random.Random(seed)
        bm = bmesh.new()
        for i in range(6):
            r = rnd.uniform(0.55, 0.95)
            mat = Matrix.Translation((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(-0.3, 0.55)))
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r, matrix=mat)
        for v in bm.verts:
            v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.09
        return bm_to_mesh(bm, "foliage%d" % seed, smooth=True)
    return cached(("foliage", seed), mk)


def leaf_mat(name, c1, c2):
    key = ("leaf", name)
    if key in _mat_cache:
        return _mat_cache[key]
    m, nb, out = new_mat(name)
    b = nb.new("ShaderNodeBsdfPrincipled")
    oi = nb.new("ShaderNodeObjectInfo")
    pos = nb.new("ShaderNodeNewGeometry").outputs["Position"]
    n = nb.noise(pos, scale=1.6, detail=3.0)[0]
    f = nb.math("ADD", nb.math("MULTIPLY", oi.outputs["Random"], 0.6), nb.math("MULTIPLY", n, 0.4))
    nb.l.new(nb.mix(f, c1, c2), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    b.inputs["Subsurface Weight"].default_value = 0.0
    nb.l.new(nb.bump(nb.noise(pos, scale=9.0, detail=2.0)[0], strength=0.6, distance=0.2), b.inputs["Normal"])
    nb.l.new(b.outputs[0], out.inputs[0])
    _mat_cache[key] = m
    return m


def tree(loc, height=10.0, spread=None, rnd=random, coll=None, leaf=None, trunk=None):
    leaf = leaf or leaf_mat("Leaf", (0.035, 0.11, 0.02), (0.11, 0.22, 0.035))
    trunk = trunk or pbr("Trunk", (0.09, 0.07, 0.05), 0.9)
    spread = spread or height * 0.42
    th = height * 0.42
    cyl("trunk", height * 0.022 + 0.05, th + 0.5, loc, trunk, r2=0.6, seg=6, coll=coll)
    new_obj("foliage", _foliage_mesh(rnd.randrange(5)), leaf,
            (loc[0], loc[1], loc[2] + th + spread * 0.55), (0, 0, rnd.uniform(0, 6.28)),
            (spread, spread, spread * rnd.uniform(0.8, 1.05)), coll=coll)


def street_lamp(loc, height=4.2, color=(1.0, 0.72, 0.42), power=0.0, coll=None, globe=True, arm=0.0, rot=0.0):
    """Lamp post. Emissive globe only (no point light) so hundreds stay cheap."""
    iron = pbr("LampIron", (0.02, 0.02, 0.022), 0.5, 0.6)
    cyl("lamp_post", 0.07, height, loc, iron, r2=0.6, seg=8, coll=coll)
    hx, hy = loc[0] + math.cos(rot) * arm, loc[1] + math.sin(rot) * arm
    if arm:
        box("lamp_arm", (arm, 0.06, 0.06), (loc[0] + math.cos(rot) * arm / 2, loc[1] + math.sin(rot) * arm / 2,
                                           loc[2] + height), iron, rot=rot, coll=coll)
    if globe:
        g = emissive("LampGlobe%g" % power, color, power) if power > 0 else pbr("LampGlobeOff", (0.9, 0.9, 0.85), 0.2)
        new_obj("lamp_globe", m_sphere(10, 6), g, (hx, hy, loc[2] + height + (0.2 if not arm else -0.12)),
                scale=(0.2, 0.2, 0.24), coll=coll)


# ----------------------------------------------------------------------------
# path utilities for moving things
# ----------------------------------------------------------------------------
class Path:
    """Polyline with arc-length lookup. Optionally closed (loops forever)."""

    def __init__(self, pts, closed=False):
        self.pts = [Vector((p[0], p[1], p[2] if len(p) > 2 else 0.0)) for p in pts]
        if closed:
            self.pts.append(self.pts[0].copy())
        self.closed = closed
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + (b - a).length)
        self.length = self.cum[-1]

    def at(self, s):
        """Return (position, heading angle) at arc length s."""
        if self.closed:
            s %= self.length
        else:
            s = min(max(s, 0.0), self.length - 1e-6)
        lo, hi = 0, len(self.cum) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.cum[mid] <= s:
                lo = mid
            else:
                hi = mid
        a, b = self.pts[lo], self.pts[lo + 1]
        seg = (self.cum[lo + 1] - self.cum[lo]) or 1.0
        t = (s - self.cum[lo]) / seg
        p = a.lerp(b, t)
        d = b - a
        return p, math.atan2(d.y, d.x)


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def smoother(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)


def lerp(a, b, t):
    return a + (b - a) * t


def look_at(cam, pos, target, roll=0.0):
    cam.location = pos
    d = Vector(target) - Vector(pos)
    q = d.to_track_quat("-Z", "Y")
    cam.rotation_euler = q.to_euler()
    if roll:
        cam.rotation_euler.rotate_axis("Z", roll)


def make_camera(scene, lens=35.0, clip=(0.5, 20000.0), sensor=36.0):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.sensor_width = sensor
    cd.clip_start, cd.clip_end = clip
    cam = bpy.data.objects.new("Cam", cd)
    link(cam)
    scene.camera = cam
    return cam

"""Render driver.

  python3 render.py --shot 1 --frames 0:288 --res 3840x2160 --samples 96 --gpu --out /workspace/stl/out/s1

Each worker rebuilds the scene from code (deterministic), then renders its
slice of frames. `--part i/n` takes every n-th frame starting at i so several
GPUs can share one shot without talking to each other.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from stl import common as C  # noqa: E402


def get_shot(n, scene):
    if n in (1, 2, 5):
        from stl import riverfront as R
        return {1: R.shot1, 2: R.shot2, 5: R.shot5}[n](scene)
    if n == 3:
        from stl import washington as W
        return W.shot3(scene)
    if n == 4:
        from stl import loop as LP
        return LP.shot4(scene)
    raise SystemExit("unknown shot %r" % n)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", type=int, required=True)
    ap.add_argument("--frames", default="0:1")          # start:stop[:step] in shot frames
    ap.add_argument("--part", default="0/1")
    ap.add_argument("--res", default="3840x2160")
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--out", default="out")
    ap.add_argument("--save-blend", default="")
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args(argv)

    t0 = time.time()
    scene = C.reset()
    w, h = (int(v) for v in a.res.lower().split("x"))
    C.setup_render(scene, w, h, a.samples, gpu=a.gpu)
    if a.png:
        scene.render.image_settings.file_format = "PNG"
    frame_fn, duration = get_shot(a.shot, scene)
    total = int(round(duration * C.FPS))
    parts = a.frames.split(":")
    start, stop = int(parts[0]), min(int(parts[1]), total)
    step = int(parts[2]) if len(parts) > 2 else 1
    pi, pn = (int(v) for v in a.part.split("/"))
    frames = [f for k, f in enumerate(range(start, stop, step)) if k % pn == pi]
    print("BUILD %.1fs shot %d objects %d frames %d" % (time.time() - t0, a.shot, len(scene.objects), len(frames)), flush=True)
    os.makedirs(a.out, exist_ok=True)
    if a.save_blend:
        frame_fn(0.0)
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save_blend), compress=True)
        print("SAVED", a.save_blend, flush=True)
    ext = "png" if a.png else "jpg"
    for f in frames:
        path = os.path.join(a.out, "s%d_%04d.%s" % (a.shot, f, ext))
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            continue
        t1 = time.time()
        scene.frame_set(f)
        frame_fn(f / C.FPS)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("FRAME %d %.1fs" % (f, time.time() - t1), flush=True)
    print("DONE %.1fs" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()

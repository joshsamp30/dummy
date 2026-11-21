# St. Louis, rebuilt in 3D

A Local Howl showpiece. Five scenes, 90 seconds, wolves instead of people.

## How it was made

Hybrid pipeline. Two stages.

1. **Blender layout (this folder).** Every scene is built in Blender from Python: the Gateway Arch on its
   published weighted-catenary equation (630 ft by 630 ft, 54 ft to 17 ft triangular section), the Old
   Courthouse, the downtown skyline at approximate real positions and heights, the Eads Bridge spans
   (502, 520, 502 ft), the riverfront, Washington Avenue and two Delmar Loop blocks. Crowds, cars, a
   MetroLink train and a riverboat are simulated. Cameras are scripted.
2. **Photoreal pass (Higgsfield).** Start and end frames of each Blender shot are converted to photoreal
   4K keyframes (Nano Banana Pro), using Local Howl's own wolf-people images as character references.
   Seedance 2.5 then generates the motion between the keyframes at 4K.

The Blender frames lock geometry, layout and camera. The AI pass supplies materials, light and the pack.

## Layout

| Path | What |
| --- | --- |
| `stl/common.py` | Materials, sky, water, steel, facade shader, helpers |
| `stl/landmarks.py` | Gateway Arch, Old Courthouse, Eads Bridge, downtown |
| `stl/actors.py` | Wolf-people, pups, wolves on leads, cyclists, cars, train, riverboat, traffic sim |
| `stl/riverfront.py` | Scenes 1, 2 and 5 |
| `stl/washington.py` | Scene 3 |
| `stl/loop.py` | Scene 4 (Blueberry Hill block, Pageant and Moonrise block) |
| `render.py` | Render driver: `python3 render.py --shot 1 --frames 0:288 --res 1280x720 --samples 32 --out out` |
| `edit/assemble.sh` | Final cut: dissolves, closing title, logo end card |
| `edit/verticals.sh` | Three 15 second 9:16 cuts |
| `assets/` | Local Howl logo (from the supplied PNG), Poppins |

Needs `pip install bpy==5.3.0` and `ffmpeg`. Add `--gpu` on a box with NVIDIA cards.

## Known limits

- No reference photos were supplied. Layouts come from published dimensions and street grids. Facade
  detail is generated, so individual buildings are plausible rather than survey-accurate.
- Infill storefronts on Washington Avenue and the Loop are generic. Only the named landmarks are real.
- Blueberry Hill and the Pageant sit about 520 m apart. The Loop scene plays as two moves with a
  dissolve instead of moving either one.

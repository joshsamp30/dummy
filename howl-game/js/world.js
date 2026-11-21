// Scene construction: the town, client storefronts, wolves, vans and job props.
import * as THREE from '../vendor/three.module.min.js';
import { GLTFLoader } from '../vendor/GLTFLoader.js';
import { STORES, COLORS } from './config.js';

export const BOUNDS = 97;
export const ROADS = [-60, 0, 60];
const BLOCKS = [[-100, -66], [-54, -6], [6, 54], [66, 100]];
export const colliders = []; // {x,z,hw,hd} boxes and {x,z,r} circles

const lam = (color, extra = {}) => new THREE.MeshLambertMaterial({ color, ...extra });
const basic = (color, extra = {}) => new THREE.MeshBasicMaterial({ color, ...extra });
const FONT = '"Poppins", system-ui, sans-serif';

// Wolf model generated with Higgsfield (image to 3D). Box wolves show until it loads, or if it fails.
let wolfProto = null; const wolfWaiters = [];
new GLTFLoader().load('assets/wolf.glb', (gltf) => {
  const m = gltf.scene, box = new THREE.Box3().setFromObject(m), size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
  const k = 3.7 / Math.max(size.x, size.y, size.z);
  m.position.set(-c.x * k, -box.min.y * k, -c.z * k); m.scale.setScalar(k);
  wolfProto = new THREE.Group(); wolfProto.add(m);
  wolfWaiters.splice(0).forEach((fn) => fn());
}, undefined, () => {});
const TINT = [0xffffff, 0xd9deea, 0xb9c0d2, 0xf2dfc2];

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}

export function labelSprite(text, { color = '#fff', bg = null, size = 44, scale = 1 } = {}) {
  const pad = 18;
  const m = document.createElement('canvas').getContext('2d');
  m.font = `700 ${size}px ${FONT}`;
  const w = Math.ceil(m.measureText(text).width) + pad * 2, h = size + pad * 1.4;
  const tex = canvasTex(w, h, (g) => {
    if (bg) { g.fillStyle = bg; g.beginPath(); g.roundRect(0, 0, w, h, h / 2); g.fill(); }
    g.font = `700 ${size}px ${FONT}`; g.textAlign = 'center'; g.textBaseline = 'middle';
    if (!bg) { g.lineWidth = 8; g.strokeStyle = 'rgba(8,12,28,.85)'; g.strokeText(text, w / 2, h / 2 + 2); }
    g.fillStyle = color; g.fillText(text, w / 2, h / 2 + 2);
  });
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  s.scale.set((w / h) * scale, scale, 1); s.renderOrder = 10;
  return s;
}

function starShape(outer = 0.5, inner = 0.22) {
  const s = new THREE.Shape();
  for (let i = 0; i < 10; i++) {
    const r = i % 2 ? inner : outer, a = (i / 10) * Math.PI * 2 + Math.PI / 2;
    i ? s.lineTo(Math.cos(a) * r, Math.sin(a) * r) : s.moveTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  return s;
}
const STAR_GEO = new THREE.ExtrudeGeometry(starShape(), { depth: 0.16, bevelEnabled: false }); STAR_GEO.center();
const STAR_MAT = basic(0xfff078);
export function makeStar(scale = 1) {
  const m = new THREE.Mesh(STAR_GEO, STAR_MAT); m.rotation.x = -Math.PI / 2; m.scale.setScalar(scale);
  return m;
}

function pinShape() {
  const s = new THREE.Shape();
  s.moveTo(0, 0);
  s.bezierCurveTo(-0.5, 0.8, -1.2, 1.4, -1.2, 2.3);
  s.absarc(0, 2.3, 1.2, Math.PI, 0, true);
  s.bezierCurveTo(1.2, 1.4, 0.5, 0.8, 0, 0);
  return s;
}
const PIN_GEO = new THREE.ExtrudeGeometry(pinShape(), { depth: 0.5, bevelEnabled: true, bevelSize: 0.08, bevelThickness: 0.08, bevelSegments: 2 });
PIN_GEO.translate(0, 0, -0.25);

function tree(scene, x, z, solid = true) {
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.35, 1.6, 6), lam(0x5b4630)); trunk.position.y = 0.8;
  const top = new THREE.Mesh(new THREE.IcosahedronGeometry(1.6, 0), lam(0x2f8f7a, { flatShading: true })); top.position.y = 2.7; top.scale.y = 1.2;
  g.add(trunk, top); g.position.set(x, 0, z); scene.add(g);
  if (solid) colliders.push({ x, z, r: 0.6 });
}

function arch(scene) {
  const pts = [];
  for (let i = 0; i <= 40; i++) {
    const t = -1 + (i / 40) * 2;
    pts.push(new THREE.Vector3(34 * t, 68 * (1 - (Math.cosh(3 * t) - 1) / (Math.cosh(3) - 1)), 0));
  }
  const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 60, 2, 3, false), lam(0xcfd8ea, { emissive: 0x39466b, flatShading: true }));
  m.position.set(0, 0, -128); scene.add(m);
}

function skyline(scene) {
  const tex = canvasTex(64, 128, (g, w, h) => {
    g.fillStyle = '#141c36'; g.fillRect(0, 0, w, h);
    for (let y = 6; y < h; y += 10) for (let x = 5; x < w; x += 10) {
      if (Math.random() < 0.45) { g.fillStyle = Math.random() < 0.7 ? '#ffd98a' : '#9cc1ff'; g.fillRect(x, y, 5, 6); }
    }
  });
  const mat = basic(0xffffff, { map: tex });
  let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 30; i++) {
    const w = 9 + rnd() * 10, h = 14 + rnd() * 34;
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, w), mat);
    b.position.set(-150 + rnd() * 300, h / 2, -140 - rnd() * 40); scene.add(b);
  }
}

const WALLS = [0xf0e6d1, 0xadddcb, 0xf3c5bf, 0xd1b893, 0xc9d3ee, 0xe4e4df];

function building(scene, x0, x1, z0, z1, h, color) {
  const cx = (x0 + x1) / 2, cz = (z0 + z1) / 2, hw = (x1 - x0) / 2, hd = (z1 - z0) / 2;
  const g = new THREE.Group(); g.position.set(cx, 0, cz);
  const body = new THREE.Mesh(new THREE.BoxGeometry(hw * 2, h, hd * 2), lam(color)); body.position.y = h / 2; g.add(body);
  const roof = new THREE.Mesh(new THREE.BoxGeometry(hw * 2 + 0.5, 0.4, hd * 2 + 0.5), lam(0x1d2745)); roof.position.y = h + 0.2; g.add(roof);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(hw * 2 - 2, 2.2), basic(0xffe2a0)); glass.position.set(0, 1.6, hd + 0.02); g.add(glass);
  scene.add(g);
  colliders.push({ x: cx, z: cz, hw, hd });
  return { g, x: cx, z: cz, hw, hd, h };
}

function storefront(scene, b, def, face) {
  const signTex = canvasTex(512, 128, (c, w, h) => {
    c.fillStyle = '#101010'; c.fillRect(0, 0, w, h);
    c.fillStyle = '#fff'; c.textAlign = 'center'; c.textBaseline = 'middle';
    c.font = `700 46px ${FONT}`; c.fillText(def.name, w / 2, 50, w - 30);
    c.fillStyle = '#fff078'; c.font = `600 26px ${FONT}`; c.fillText(def.cat.toUpperCase(), w / 2, 100);
  });
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(13, 3.25), basic(0xffffff, { map: signTex }));
  sign.position.set(0, b.h + 1.8, 0); sign.rotation.x = -0.8; b.g.add(sign);
  const awning = new THREE.Mesh(new THREE.BoxGeometry(b.hw * 2 - 1, 0.3, 1.8), lam(0xff5fa8));
  awning.position.set(0, 3.2, face * (b.hd + 0.9)); awning.rotation.x = face * 0.25; b.g.add(awning);
  const pin = new THREE.Mesh(PIN_GEO, lam(0x8892b0, { emissive: 0x222a44 }));
  pin.scale.setScalar(1.3); pin.position.set(0, b.h + 5, 0); b.g.add(pin);
  const store = { def, x: b.x, z: b.z, face, pin, tagY: b.h + 9.5, g: b.g, tag: null, rank: 0,
    zone: { x: b.x, z: b.z + face * (b.hd + 7) } };
  store.setRank = (rank) => {
    store.rank = rank;
    if (store.tag) { b.g.remove(store.tag); store.tag.material.map.dispose(); store.tag.material.dispose(); }
    const inPack = rank <= 3;
    store.tag = labelSprite(inPack ? `MAP PACK #${rank}` : `RANK #${rank}`, { color: '#101010', bg: inPack ? '#fff078' : '#faf9f5', size: 40, scale: inPack ? 2.2 : 1.6 });
    store.tag.position.set(0, store.tagY, 0); b.g.add(store.tag);
    const col = inPack ? 0xfff078 : 0x8892b0;
    pin.material.color.setHex(col); pin.material.emissive.setHex(inPack ? 0xa89a30 : 0x222a44);
  };
  return store;
}

export function buildWorld(scene) {
  scene.background = new THREE.Color(0x0f172a);
  scene.fog = new THREE.Fog(0x0f172a, 90, 230);
  scene.add(new THREE.HemisphereLight(0xc4d2ff, 0x2a2a4d, 2.2));
  const moonLight = new THREE.DirectionalLight(0xdfe7ff, 1.6); moonLight.position.set(20, 40, 10); scene.add(moonLight);

  const flat = (w, d, color, x, z, y) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), lam(color)); m.rotation.x = -Math.PI / 2; m.position.set(x, y, z); scene.add(m); return m; };
  flat(600, 600, 0x161d33, 0, 0, 0);
  flat(204, 204, 0x39446a, 0, 0, 0.01); // pavement under everything
  for (const r of ROADS) { flat(204, 12, 0x222b47, 0, r, 0.02); flat(12, 204, 0x222b47, r, 0, 0.02); }
  const dashMat = basic(0xfff078);
  for (const r of ROADS) for (let t = -96; t <= 96; t += 8) {
    if (ROADS.some((o) => Math.abs(t - o) < 8)) continue;
    const a = new THREE.Mesh(new THREE.PlaneGeometry(3.5, 0.35), dashMat); a.rotation.x = -Math.PI / 2; a.position.set(t, 0.03, r); scene.add(a);
    const b = new THREE.Mesh(new THREE.PlaneGeometry(0.35, 3.5), dashMat); b.rotation.x = -Math.PI / 2; b.position.set(r, 0.03, t); scene.add(b);
  }

  // Blocks. Each block is four low buildings. Two corner blocks are parks.
  let seed = 11; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const candidates = []; let hqB = null;
  BLOCKS.forEach(([x0, x1], bi) => BLOCKS.forEach(([z0, z1], bj) => {
    if ((bi === 0 && bj === 3) || (bi === 3 && bj === 0)) {
      flat(x1 - x0 - 4, z1 - z0 - 4, 0x1f5a4e, (x0 + x1) / 2, (z0 + z1) / 2, 0.03);
      for (let i = 0; i < 9; i++) tree(scene, x0 + 5 + rnd() * (x1 - x0 - 10), z0 + 5 + rnd() * (z1 - z0 - 10));
      return;
    }
    const mx = (x0 + x1) / 2, mz = (z0 + z1) / 2;
    [[x0 + 4, mx - 1.5], [mx + 1.5, x1 - 4]].forEach(([ax, bx], qi) => [[z0 + 4, mz - 1.5], [mz + 1.5, z1 - 4]].forEach(([az, bz], qj) => {
      const inner = (bi === 1 || bi === 2) && (bj === 1 || bj === 2);
      const b = building(scene, ax, bx, az, bz, inner ? 5.5 : 4 + rnd() * 5, WALLS[Math.floor(rnd() * WALLS.length)]);
      if (!inner) return;
      const face = qj === 0 ? -1 : 1;
      if (bi === 1 && bj === 1 && qi === 1 && qj === 1) hqB = { b, face }; else candidates.push({ b, face });
    }));
  }));
  // Spread nine clients over the fifteen inner buildings.
  const stores = [0, 2, 3, 5, 6, 8, 10, 12, 14].map((ci, i) => storefront(scene, candidates[ci].b, STORES[i], candidates[ci].face));

  // Local Howl HQ.
  const hb = hqB.b; hb.g.children[0].material.color.setHex(0xfaf9f5);
  const logoTex = new THREE.TextureLoader().load('assets/logo_navy.png'); logoTex.colorSpace = THREE.SRGBColorSpace;
  const roofLogo = new THREE.Mesh(new THREE.PlaneGeometry(13, 5.4), basic(0xffffff, { map: logoTex, transparent: true }));
  roofLogo.rotation.x = -Math.PI / 2; roofLogo.position.set(0, hb.h + 0.5, 0); hb.g.add(roofLogo);
  const roofPad = new THREE.Mesh(new THREE.PlaneGeometry(hb.hw * 2 - 1, hb.hd * 2 - 1), basic(0xfaf9f5)); roofPad.rotation.x = -Math.PI / 2; roofPad.position.y = hb.h + 0.45; hb.g.add(roofPad);
  const hqTag = labelSprite('LOCAL HOWL HQ', { color: '#fff', bg: '#092aff', size: 40, scale: 1.8 }); hqTag.position.set(0, hb.h + 6, 0); hb.g.add(hqTag);
  const hq = { x: hb.x, z: hb.z, zone: { x: hb.x, z: hb.z + hqB.face * (hb.hd + 7) } };

  for (const r of ROADS) for (let t = -90; t <= 90; t += 30) {
    if (ROADS.some((o) => Math.abs(t - o) < 10)) continue;
    tree(scene, t, r - 8.2, true); tree(scene, r + 8.2, t + 4, true);
  }
  arch(scene); skyline(scene);
  const moon = new THREE.Mesh(new THREE.CircleGeometry(12, 40), basic(0xfff4d6, { fog: false })); moon.position.set(-60, 90, -190); scene.add(moon);
  return { stores, hq };
}

// ---------- characters and vehicles ----------
const FUR = [0xf4f6fb, 0xc3cbdc, 0x9aa3b8, 0xe6d3b3];
export function makeWolf(name, ringColor, furIdx = 0, tagColor = '#fff') {
  const g = new THREE.Group();
  const fur = lam(FUR[furIdx % FUR.length]), dark = lam(0x2a3048);
  const body = new THREE.Group(); g.add(body);
  const boxy = new THREE.Group(); body.add(boxy);
  const add = (geo, mat, x, y, z) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); boxy.add(m); return m; };
  add(new THREE.BoxGeometry(0.95, 0.85, 1.9), fur, 0, 1.05, 0);
  add(new THREE.BoxGeometry(0.85, 0.8, 0.8), fur, 0, 1.6, 1.1);
  add(new THREE.BoxGeometry(0.42, 0.36, 0.55), fur, 0, 1.45, 1.7);
  add(new THREE.BoxGeometry(0.2, 0.16, 0.12), dark, 0, 1.56, 2.0);
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(1.4, 16), basic(0x000000, { transparent: true, opacity: 0.3 }));
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.05; g.add(shadow);
  const ring = new THREE.Mesh(new THREE.RingGeometry(1.45, 1.85, 28), basic(ringColor));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.07; g.add(ring);
  let tag = null;
  if (name) { tag = labelSprite(name, { color: tagColor, size: 36, scale: 1.05 }); tag.position.y = 4.7; g.add(tag); }
  const out = { g, body, ring, tag };
  const useModel = () => {
    const model = wolfProto.clone(true);
    model.traverse((o) => {
      if (!o.isMesh) return;
      o.material = o.material.clone(); o.material.color.setHex(TINT[furIdx % TINT.length]);
      o.material.metalness = 0; o.material.roughness = 1;
      if (o.material.map) { o.material.emissive.setHex(0x55586a); o.material.emissiveMap = o.material.map; }
    });
    body.remove(boxy); body.add(model);
  };
  if (wolfProto) useModel(); else wolfWaiters.push(useModel);
  return out;
}

let vanLogo = null;
export function makeVan(isMine) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(2.6, 2.1, 5.2), lam(0xfaf9f5)); body.position.y = 1.5; g.add(body);
  const stripe = new THREE.Mesh(new THREE.BoxGeometry(2.66, 0.45, 5.26), lam(isMine ? 0xff5fa8 : 0x4d6bff)); stripe.position.y = 1.0; g.add(stripe);
  const glass = new THREE.Mesh(new THREE.BoxGeometry(2.3, 0.8, 0.2), lam(0x1d2745)); glass.position.set(0, 2.0, 2.55); g.add(glass);
  const lights = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.25, 0.1), basic(0xfff4c0)); lights.position.set(0, 0.95, 2.62); g.add(lights);
  for (const [x, z] of [[-1.3, 1.6], [1.3, 1.6], [-1.3, -1.6], [1.3, -1.6]]) {
    const w = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 0.4, 10), lam(0x101010)); w.rotation.z = Math.PI / 2; w.position.set(x, 0.55, z); g.add(w);
  }
  vanLogo = vanLogo || new THREE.TextureLoader().load('assets/pin_navy.png'); vanLogo.colorSpace = THREE.SRGBColorSpace;
  const logo = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 2.25), basic(0xffffff, { map: vanLogo, transparent: true }));
  logo.rotation.x = -Math.PI / 2; logo.position.set(0, 2.57, -0.6); g.add(logo);
  const shadow = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 6), basic(0x000000, { transparent: true, opacity: 0.3 })); shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.05; g.add(shadow);
  return g;
}

const CAR_COLORS = [0x6cd3a8, 0xc9a2ff, 0xffb86b, 0x8fb4ff, 0xe4e4df, 0xff8a8a];
export function makeCar(i) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(2.1, 0.9, 4.2), lam(CAR_COLORS[i % CAR_COLORS.length])); body.position.y = 0.8; g.add(body);
  const cab = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.75, 2.1), lam(0x1d2745)); cab.position.set(0, 1.6, -0.2); g.add(cab);
  const lights = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.2, 0.1), basic(0xfff4c0)); lights.position.set(0, 0.85, 2.12); g.add(lights);
  return g;
}

export function makeBug(label) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.IcosahedronGeometry(1.0, 0), lam(0xff3b3b, { emissive: 0x7a0f0f, flatShading: true })); body.position.y = 1.1; g.add(body);
  for (let i = 0; i < 6; i++) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.14, 1.3), lam(0x101010)); const a = (i / 6) * Math.PI * 2;
    leg.position.set(Math.sin(a) * 1.0, 0.5, Math.cos(a) * 1.0); leg.rotation.y = a; g.add(leg);
  }
  const tag = labelSprite(label, { color: '#fff', bg: '#e02424', size: 34, scale: 1.0 }); tag.position.y = 3.1; g.add(tag);
  return { g, body };
}

export function makeDrone() {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.OctahedronGeometry(1.0, 0), lam(0x101010, { emissive: 0x4a0d2c, flatShading: true })); body.position.y = 2.4; g.add(body);
  const eye = new THREE.Mesh(new THREE.SphereGeometry(0.35, 8, 6), basic(0xff2d6f)); eye.position.set(0, 2.4, 0.8); g.add(eye);
  const halo = new THREE.Mesh(new THREE.RingGeometry(1.2, 1.45, 20), basic(0xff2d6f, { side: THREE.DoubleSide })); halo.rotation.x = -Math.PI / 2; halo.position.y = 2.4; g.add(halo);
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.9, 12), basic(0x000000, { transparent: true, opacity: 0.3 })); shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.05; g.add(shadow);
  const tag = labelSprite('SPAM BOT', { color: '#fff', bg: '#101010', size: 30, scale: 0.9 }); tag.position.y = 4.4; g.add(tag);
  return { g, body, halo };
}

export function makeBeacon(color, label, css) {
  const g = new THREE.Group();
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 34, 20, 1, true), basic(color, { transparent: true, opacity: 0.2, side: THREE.DoubleSide, depthWrite: false })); beam.position.y = 17; g.add(beam);
  const ring = new THREE.Mesh(new THREE.RingGeometry(4.2, 5, 36), basic(color)); ring.rotation.x = -Math.PI / 2; ring.position.y = 0.08; g.add(ring);
  if (label) { const tag = labelSprite(label, { color: '#101010', bg: css, size: 42, scale: 2.0 }); tag.position.y = 6.5; g.add(tag); }
  return { g, ring };
}

export function makePage() {
  const g = new THREE.Group();
  const sheet = new THREE.Mesh(new THREE.BoxGeometry(1.5, 1.9, 0.12), basic(0xfaf9f5)); g.add(sheet);
  for (let i = 0; i < 4; i++) { const l = new THREE.Mesh(new THREE.BoxGeometry(1.0 - (i === 3 ? 0.4 : 0), 0.12, 0.14), basic(i ? 0x8892b0 : 0x092aff)); l.position.set(i === 3 ? -0.2 : 0, 0.55 - i * 0.35, 0); g.add(l); }
  return g;
}

export function makeArrow() {
  const m = new THREE.Mesh(new THREE.ConeGeometry(0.7, 1.8, 3), basic(COLORS.me));
  m.rotation.x = Math.PI / 2; const g = new THREE.Group(); g.add(m); m.position.z = 3.6; m.position.y = 0.4; m.scale.y = 1; m.scale.z = 0.35;
  return g;
}

export function makeRing(color) {
  const m = new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 48), basic(color, { transparent: true, side: THREE.DoubleSide }));
  m.rotation.x = -Math.PI / 2; m.position.y = 0.3;
  return m;
}

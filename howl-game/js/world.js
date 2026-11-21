// Scene construction: the block, storefronts, wolves, stars, effects.
import * as THREE from '../vendor/three.module.min.js';
import { TEAMS, STORES, PADS } from './config.js';

export const BOUNDS = { x: 48, z: 38 };
export const STORE_HW = 6, STORE_HD = 4, STORE_H = 6;
export const colliders = []; // {x,z,hw,hd,store?} boxes and {x,z,r} circles

const lam = (color, extra = {}) => new THREE.MeshLambertMaterial({ color, ...extra });
const FONT = '"Poppins", system-ui, sans-serif';

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
const STAR_GEO = new THREE.ExtrudeGeometry(starShape(), { depth: 0.16, bevelEnabled: false });
STAR_GEO.center();
const STAR_MATS = [new THREE.MeshBasicMaterial({ color: 0x8fb4ff }), new THREE.MeshBasicMaterial({ color: 0xff9db0 })];

export function makeStar(team) {
  const m = new THREE.Mesh(STAR_GEO, STAR_MATS[team]);
  m.rotation.x = -Math.PI / 2;
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

function tree(scene, x, z) {
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.35, 1.6, 6), lam(0x5b4630));
  trunk.position.y = 0.8;
  const top = new THREE.Mesh(new THREE.IcosahedronGeometry(1.5, 0), lam(0x2f8f7a, { flatShading: true }));
  top.position.y = 2.6; top.scale.y = 1.2;
  g.add(trunk, top); g.position.set(x, 0, z); scene.add(g);
  colliders.push({ x, z, r: 0.6 });
}

function arch(scene) {
  const pts = [];
  for (let i = 0; i <= 40; i++) {
    const t = -1 + (i / 40) * 2;
    pts.push(new THREE.Vector3(26 * t, 52 * (1 - (Math.cosh(3 * t) - 1) / (Math.cosh(3) - 1)), 0));
  }
  const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 60, 1.5, 3, false),
    lam(0xcfd8ea, { emissive: 0x39466b, flatShading: true }));
  m.position.set(0, 0, -62); scene.add(m);
}

function skyline(scene) {
  const tex = canvasTex(64, 128, (g, w, h) => {
    g.fillStyle = '#141c36'; g.fillRect(0, 0, w, h);
    for (let y = 6; y < h; y += 10) for (let x = 5; x < w; x += 10) {
      if (Math.random() < 0.45) { g.fillStyle = Math.random() < 0.7 ? '#ffd98a' : '#9cc1ff'; g.fillRect(x, y, 5, 6); }
    }
  });
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  const mat = new THREE.MeshBasicMaterial({ map: tex });
  let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 26; i++) {
    const w = 7 + rnd() * 8, h = 10 + rnd() * 26;
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, w), mat);
    const side = i % 2 ? 1 : -1;
    b.position.set(side * (30 + rnd() * 70), h / 2, -74 - rnd() * 30);
    scene.add(b);
  }
}

function storefront(scene, def, i) {
  const face = def.z < 0 ? 1 : -1; // direction of the street
  const g = new THREE.Group(); g.position.set(def.x, 0, def.z);
  const wallColors = [0xf0e6d1, 0xadddcb, 0xf3c5bf, 0xd1b893];
  const body = new THREE.Mesh(new THREE.BoxGeometry(STORE_HW * 2, STORE_H, STORE_HD * 2), lam(wallColors[i % 4]));
  body.position.y = STORE_H / 2; g.add(body);
  const roof = new THREE.Mesh(new THREE.BoxGeometry(STORE_HW * 2 + 0.6, 0.5, STORE_HD * 2 + 0.6), lam(0x1d2745));
  roof.position.y = STORE_H + 0.25; g.add(roof);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(STORE_HW * 2 - 2, 2.6), new THREE.MeshBasicMaterial({ color: 0xffe2a0 }));
  glass.position.set(0, 1.7, face * (STORE_HD + 0.02)); if (face < 0) glass.rotation.y = Math.PI; g.add(glass);
  const awning = new THREE.Mesh(new THREE.BoxGeometry(STORE_HW * 2 - 1, 0.3, 1.8), lam(0x8892b0));
  awning.position.set(0, 3.3, face * (STORE_HD + 0.9)); awning.rotation.x = face * 0.25; g.add(awning);
  const signTex = canvasTex(512, 128, (c, w, h) => {
    c.fillStyle = '#0f172a'; c.fillRect(0, 0, w, h);
    c.fillStyle = '#fff'; c.textAlign = 'center'; c.textBaseline = 'middle';
    c.font = `700 46px ${FONT}`; c.fillText(def.name, w / 2, 50, w - 30);
    c.fillStyle = '#edc550'; c.font = `600 26px ${FONT}`; c.fillText(def.cat.toUpperCase(), w / 2, 100);
  });
  // The sign lies back on the roof edge so the top-down camera can read it.
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(10, 2.5), new THREE.MeshBasicMaterial({ map: signTex }));
  sign.position.set(0, STORE_H + 1.4, face * (STORE_HD - 1.2)); sign.rotation.x = -0.75; g.add(sign);

  // Ranking meter on the pavement in front of the door.
  const barBg = new THREE.Mesh(new THREE.PlaneGeometry(10.4, 1.1), new THREE.MeshBasicMaterial({ color: 0x0b1020 }));
  barBg.rotation.x = -Math.PI / 2; barBg.position.set(0, 0.06, face * (STORE_HD + 3.2)); g.add(barBg);
  const bar = new THREE.Mesh(new THREE.PlaneGeometry(10, 0.7), new THREE.MeshBasicMaterial({ color: 0x8892b0 }));
  bar.rotation.x = -Math.PI / 2; bar.position.set(0, 0.08, face * (STORE_HD + 3.2)); bar.scale.x = 0.001; g.add(bar);

  const pin = new THREE.Mesh(PIN_GEO, lam(0x8892b0, { emissive: 0x222a44 }));
  pin.position.set(0, STORE_H + 3.2, 0); pin.rotation.x = -0.5; g.add(pin);

  const badges = [1, 2, 3].map((n) => {
    const s = labelSprite('MAP PACK #' + n, { color: '#0f172a', bg: '#edc550', size: 40, scale: 1.5 });
    s.position.set(0, STORE_H + 8.2, 0); s.visible = false; g.add(s); return s;
  });

  const spam = new THREE.Group();
  const spamPin = new THREE.Mesh(PIN_GEO, new THREE.MeshBasicMaterial({ color: 0xff2d2d }));
  spamPin.scale.setScalar(1.5); spamPin.rotation.x = -0.5; spam.add(spamPin);
  const spamLabel = labelSprite('SPAM LISTING', { color: '#fff', bg: '#d81e1e', size: 40, scale: 1.6 });
  spamLabel.position.y = 6.6; spam.add(spamLabel);
  spam.position.set(0, 1.5, face * (STORE_HD + 1.2)); spam.visible = false; g.add(spam);

  scene.add(g);
  colliders.push({ x: def.x, z: def.z, hw: STORE_HW, hd: STORE_HD, store: i });
  return { def, face, bar, pin, badges, spam, body, front: { x: def.x, z: def.z + face * (STORE_HD + 7) } };
}

export function buildWorld(scene) {
  scene.background = new THREE.Color(0x0f172a);
  scene.fog = new THREE.Fog(0x0f172a, 70, 170);
  scene.add(new THREE.HemisphereLight(0xc4d2ff, 0x2a2a4d, 2.2));
  const moonLight = new THREE.DirectionalLight(0xdfe7ff, 1.6); moonLight.position.set(20, 40, 10); scene.add(moonLight);

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), lam(0x161d33));
  ground.rotation.x = -Math.PI / 2; scene.add(ground);
  const street = new THREE.Mesh(new THREE.PlaneGeometry(BOUNDS.x * 2 + 4, BOUNDS.z * 2 + 4), lam(0x222b47));
  street.rotation.x = -Math.PI / 2; street.position.y = 0.01; scene.add(street);
  for (const z of [-24, 24]) {
    const walk = new THREE.Mesh(new THREE.PlaneGeometry(BOUNDS.x * 2 + 4, 7), lam(0x39446a));
    walk.rotation.x = -Math.PI / 2; walk.position.set(0, 0.02, z); scene.add(walk);
  }
  for (let x = -44; x <= 44; x += 8) {
    if (Math.abs(x) < 9) continue;
    const dash = new THREE.Mesh(new THREE.PlaneGeometry(3.5, 0.35), new THREE.MeshBasicMaterial({ color: 0xedc550 }));
    dash.rotation.x = -Math.PI / 2; dash.position.set(x, 0.03, 0); scene.add(dash);
  }
  const plaza = new THREE.Mesh(new THREE.CircleGeometry(8, 40), lam(0xf0e6d1));
  plaza.rotation.x = -Math.PI / 2; plaza.position.y = 0.04; scene.add(plaza);

  // Centre statue: the Local Howl pin.
  const plinth = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.8, 1, 24), lam(0x1d2745));
  plinth.position.y = 0.5; scene.add(plinth);
  const statue = new THREE.Group();
  const bigPin = new THREE.Mesh(PIN_GEO, lam(0xffffff, { emissive: 0x555c77 }));
  statue.add(bigPin);
  const logoTex = new THREE.TextureLoader().load('assets/pin_navy.png'); logoTex.colorSpace = THREE.SRGBColorSpace;
  for (const s of [1, -1]) {
    const face = new THREE.Mesh(new THREE.PlaneGeometry(2.0, 2.5), new THREE.MeshBasicMaterial({ map: logoTex, transparent: true }));
    face.position.set(0, 1.95, s * 0.36); if (s < 0) face.rotation.y = Math.PI; statue.add(face);
  }
  statue.position.y = 1.1; statue.scale.setScalar(1.6); scene.add(statue);
  colliders.push({ x: 0, z: 0, r: 2.9 });

  // Dens.
  TEAMS.forEach((t, i) => {
    const x = i ? 43 : -43;
    const pad = new THREE.Mesh(new THREE.CircleGeometry(5, 32), new THREE.MeshBasicMaterial({ color: t.color, transparent: true, opacity: 0.28 }));
    pad.rotation.x = -Math.PI / 2; pad.position.set(x, 0.05, 0); scene.add(pad);
    const lbl = labelSprite(t.name.toUpperCase() + ' DEN', { color: t.css, size: 40, scale: 1.4 });
    lbl.position.set(x, 3, 0); scene.add(lbl);
  });

  // Cover.
  for (const [x, z] of [[-15, -9], [15, -9], [-15, 9], [15, 9]]) {
    const p = new THREE.Mesh(new THREE.BoxGeometry(3, 1.4, 3), lam(0x4a5682)); p.position.set(x, 0.7, z); scene.add(p);
    const bush = new THREE.Mesh(new THREE.IcosahedronGeometry(1.3, 0), lam(0x65b8ad, { flatShading: true })); bush.position.set(x, 1.9, z); scene.add(bush);
    colliders.push({ x, z, hw: 1.5, hd: 1.5 });
  }
  for (const [x, z] of [[-34, -12], [34, -12], [-34, 12], [34, 12], [-20, -22], [20, -22], [-20, 22], [20, 22], [0, -23], [0, 23]]) tree(scene, x, z);

  arch(scene); skyline(scene);
  const moon = new THREE.Mesh(new THREE.CircleGeometry(9, 40), new THREE.MeshBasicMaterial({ color: 0xfff4d6, fog: false }));
  moon.position.set(-38, 62, -120); scene.add(moon);

  const stores = STORES.map((d, i) => storefront(scene, d, i));

  const pads = PADS.map((p) => {
    const ring = new THREE.Mesh(new THREE.RingGeometry(1.2, 1.5, 24), new THREE.MeshBasicMaterial({ color: 0x8892b0 }));
    ring.rotation.x = -Math.PI / 2; ring.position.set(p.x, 0.06, p.z); scene.add(ring);
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.8, 0), new THREE.MeshBasicMaterial({ color: 0xffffff }));
    gem.position.set(p.x, 1.5, p.z); gem.visible = false; scene.add(gem);
    return { ...p, ring, gem, label: null, type: 0 };
  });
  return { stores, pads, statue };
}

const FUR = [0xf4f6fb, 0xc3cbdc, 0x9aa3b8, 0xe6d3b3];
export function makeWolf(name, team, isMe, furIdx = 0) {
  const g = new THREE.Group();
  const fur = lam(FUR[furIdx % FUR.length]), dark = lam(0x2a3048), tc = lam(TEAMS[team].color, { emissive: TEAMS[team].color, emissiveIntensity: 0.35 });
  const body = new THREE.Group(); g.add(body);
  const add = (geo, mat, x, y, z) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); body.add(m); return m; };
  add(new THREE.BoxGeometry(0.95, 0.85, 1.9), fur, 0, 1.05, 0);
  add(new THREE.BoxGeometry(0.85, 0.8, 0.8), fur, 0, 1.6, 1.1);
  add(new THREE.BoxGeometry(0.42, 0.36, 0.55), fur, 0, 1.45, 1.7);
  add(new THREE.BoxGeometry(0.2, 0.16, 0.12), dark, 0, 1.56, 2.0);
  for (const s of [-1, 1]) { const e = add(new THREE.ConeGeometry(0.2, 0.45, 4), fur, s * 0.28, 2.2, 1.0); e.rotation.y = Math.PI / 4; }
  add(new THREE.BoxGeometry(1.0, 0.3, 0.45), tc, 0, 1.3, 0.72);
  const tail = add(new THREE.BoxGeometry(0.3, 0.3, 1.0), fur, 0, 1.35, -1.3); tail.rotation.x = 0.6;
  const legs = [[-0.32, 0.65], [0.32, 0.65], [-0.32, -0.65], [0.32, -0.65]].map(([x, z]) => add(new THREE.BoxGeometry(0.26, 0.7, 0.26), fur, x, 0.35, z));
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(1.1, 16), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.3 }));
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.05; g.add(shadow);
  const ring = new THREE.Mesh(new THREE.RingGeometry(1.25, 1.5, 28), new THREE.MeshBasicMaterial({ color: isMe ? 0xedc550 : TEAMS[team].color, transparent: true, opacity: isMe ? 1 : 0.7 }));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.07; g.add(ring);
  const shield = new THREE.Mesh(new THREE.SphereGeometry(1.9, 14, 10), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.22 }));
  shield.position.y = 1.1; shield.visible = false; g.add(shield);
  const tag = labelSprite(isMe ? name + ' (you)' : name, { color: isMe ? '#edc550' : TEAMS[team].css, size: 36, scale: 0.95 });
  tag.position.y = 3.5; g.add(tag);
  return { g, body, legs, tail, shield, tag };
}

export function makeHowlRing(team) {
  const m = new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 48), new THREE.MeshBasicMaterial({ color: TEAMS[team].color, transparent: true, side: THREE.DoubleSide }));
  m.rotation.x = -Math.PI / 2; m.position.y = 0.3;
  return m;
}

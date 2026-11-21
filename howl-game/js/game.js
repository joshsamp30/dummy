// Local Howl: Map Pack Showdown. An open-town shift, built around one player.
// Every client runs its own shift. The network only shares where players are and their lead count.
import * as THREE from '../vendor/three.module.min.js';
import { CONFIG, COLORS, JOBS, ISSUES, FACTS } from './config.js';
import { buildWorld, makeWolf, makeVan, makeCar, makeBug, makeDrone, makeBeacon, makePage, makeArrow, makeRing, makeStar, colliders, BOUNDS, ROADS } from './world.js';

const FOOT = 10.5, VAN_MAX = 27, R_FOOT = 0.8, R_VAN = 2.0;
const ZONE = 5.5, RANGE = 13, HOWL_R = 14, HOWL_CD = 10000;
const now = () => performance.now();
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const dist = (ax, az, bx, bz) => Math.hypot(ax - bx, az - bz);
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const rand = (a, b) => a + Math.random() * (b - a);

function collide(e, R) {
  let hit = false;
  for (const c of colliders) {
    if (c.r) {
      const d = dist(e.x, e.z, c.x, c.z), min = c.r + R;
      if (d < min && d > 1e-4) { e.x = c.x + ((e.x - c.x) / d) * min; e.z = c.z + ((e.z - c.z) / d) * min; hit = true; }
    } else {
      if (Math.abs(e.x - c.x) > c.hw + R || Math.abs(e.z - c.z) > c.hd + R) continue;
      const nx = clamp(e.x, c.x - c.hw, c.x + c.hw), nz = clamp(e.z, c.z - c.hd, c.z + c.hd);
      const dx = e.x - nx, dz = e.z - nz, d = Math.hypot(dx, dz);
      if (d < R) {
        hit = true;
        if (d > 1e-4) { e.x = nx + (dx / d) * R; e.z = nz + (dz / d) * R; }
        else if (c.hw - Math.abs(e.x - c.x) < c.hd - Math.abs(e.z - c.z)) e.x = c.x + Math.sign(e.x - c.x || 1) * (c.hw + R);
        else e.z = c.z + Math.sign(e.z - c.z || 1) * (c.hd + R);
      }
    }
  }
  if (Math.abs(e.x) > BOUNDS) { e.x = clamp(e.x, -BOUNDS, BOUNDS); hit = true; }
  if (Math.abs(e.z) > BOUNDS) { e.z = clamp(e.z, -BOUNDS, BOUNDS); hit = true; }
  return hit;
}

// A random point on the street grid. lateral 0 is the centre line, about 7.5 is the pavement.
function roadPoint(nx, nz, minD, maxD, lateral = 4) {
  for (let i = 0; i < 60; i++) {
    const r = pick(ROADS), t = rand(-92, 92), off = rand(-lateral, lateral) || 0;
    const p = Math.random() < 0.5 ? { x: t, z: r + off } : { x: r + off, z: t };
    const d = dist(p.x, p.z, nx, nz);
    if (d >= minD && d <= maxD) return p;
  }
  return { x: clamp(nx + minD, -90, 90), z: pick(ROADS) };
}
const sidewalkPoint = (nx, nz, minD, maxD) => {
  for (let i = 0; i < 60; i++) {
    const r = pick(ROADS), t = rand(-92, 92), off = pick([-7.6, 7.6]);
    if (ROADS.some((o) => Math.abs(t - o) < 9)) continue;
    const p = Math.random() < 0.5 ? { x: t, z: r + off } : { x: r + off, z: t };
    const d = dist(p.x, p.z, nx, nz);
    if (d >= minD && d <= maxD) return p;
  }
  return roadPoint(nx, nz, minD, maxD);
};

export class Game {
  constructor(canvas, net, me, ui, input, sfx) {
    this.net = net; this.me = me; this.ui = ui; this.input = input; this.sfx = sfx;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, matchMedia('(pointer:coarse)').matches ? 1.5 : 2));
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(50, 1, 0.5, 500);
    this.world = buildWorld(this.scene);
    this.remotes = new Map(); this.playing = false; this.attract = 0; this.last = now();
    this.bugs = []; this.drones = []; this.bolts = []; this.fx = []; this.customers = []; this.cars = [];
    this.offers = {}; this.mission = null; this.pending = [];
    this.S = { phase: 'idle', tl: CONFIG.SHIFT_SECONDS, leads: 0, jobs: { fix: 0, reviews: 0, page: 0 }, heat: 0, heatT: 0, stolen: 0 };
    this.p = { x: 0, z: 0, r: 0, inVan: false, stun: 0, walk: 0, moving: false };
    this.van = { x: 0, z: 0, r: 0, vx: 0, vz: 0, mesh: makeVan(true) };
    this.scene.add(this.van.mesh);
    this.wolf = null; // created on start, once the player has a name
    this.arrow = makeArrow(); this.arrow.visible = false; this.scene.add(this.arrow);
    this.page = makePage(); this.page.visible = false; this.scene.add(this.page);
    this.fireAt = 0; this.howlAt = 0; this.sendAt = 0; this.secAt = 0; this.callAt = 0; this.droneAt = 0; this.action = '';
    this.tmp = new THREE.Vector3(); this.cam = { x: 0, z: 0, s: 1 };
    this.initTraffic(); this.placeAtHQ();
    net.onMsg = (m) => this.onMsg(m);
    net.onRoster = (r) => this.onRoster(r);
    addEventListener('resize', () => this.resize()); this.resize();
    this.renderer.setAnimationLoop(() => this.frame());
  }

  resize() {
    const w = innerWidth, h = innerHeight;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    this.camScale = w < h ? 1.65 : 1;
  }

  // ---------- other players ----------
  onRoster(roster) {
    const ids = new Set(roster.map((m) => m.id));
    for (const m of roster) {
      if (m.id === this.me.id || this.remotes.has(m.id)) continue;
      const wolf = makeWolf(m.name, COLORS.other, m.fur || 0, '#9fb0ff'), van = makeVan(false);
      wolf.g.visible = false; van.visible = false; this.scene.add(wolf.g, van);
      this.remotes.set(m.id, { name: m.name, x: 0, z: 0, r: 0, tx: 0, tz: 0, tr: 0, inVan: false, leads: 0, seen: false, wolf, van });
    }
    for (const [id, r] of this.remotes) if (!ids.has(id)) { this.scene.remove(r.wolf.g, r.van); this.remotes.delete(id); }
    this.ui.setRoster(roster.length, this.net.kind);
  }
  onMsg(m) {
    if (m.t === 'p') {
      const r = this.remotes.get(m.id); if (!r) return;
      if (!r.seen) { r.x = m.x; r.z = m.z; r.seen = true; }
      r.tx = m.x; r.tz = m.z; r.tr = m.r; r.inVan = !!m.v; r.leads = m.l;
    } else if (m.t === 'w') this.ring(m.x, m.z, COLORS.other, HOWL_R, 0.6);
  }
  board() {
    const rows = [{ name: this.me.name, leads: Math.round(this.S.leads), me: true }];
    for (const r of this.remotes.values()) if (r.seen) rows.push({ name: r.name, leads: r.leads });
    return rows.sort((a, b) => b.leads - a.leads);
  }

  // ---------- shift ----------
  placeAtHQ() {
    const z = this.world.hq.zone;
    Object.assign(this.p, { x: z.x, z: z.z, r: 0, inVan: false, stun: 0 });
    Object.assign(this.van, { x: z.x + 5.5, z: z.z + 1, r: Math.PI / 2, vx: 0, vz: 0 });
  }
  start() {
    if (!this.wolf) { this.wolf = makeWolf(this.me.name, COLORS.me, this.me.fur, '#fff078'); this.scene.add(this.wolf.g); }
    this.playing = true; this.startShift();
  }
  startShift() {
    this.clearJob(); for (const d of this.drones) this.scene.remove(d.mesh.g); this.drones = [];
    for (const k in this.offers) this.dropOffer(k);
    this.S = { phase: 'shift', tl: CONFIG.SHIFT_SECONDS, leads: 0, jobs: { fix: 0, reviews: 0, page: 0 }, heat: 0, heatT: 0, stolen: 0 };
    this.world.stores.forEach((s) => s.setRank(9 + Math.floor(Math.random() * 7)));
    this.placeAtHQ(); this.pending = []; this.howlAt = 0; this.secAt = now() + 1000;
    for (const k of Object.keys(JOBS)) this.spawnOffer(k);
    this.ui.hideResults(); this.ui.banner('Shift started. Pick a job.', 2200);
  }
  endShift() {
    this.S.phase = 'done'; this.clearJob();
    for (const d of this.drones) this.scene.remove(d.mesh.g); this.drones = [];
    this.sfx.capture(); this.ui.results(this.S, this.packCount(), this.board());
  }
  packCount() { return this.world.stores.filter((s) => s.rank <= 3).length; }

  // ---------- job offers ----------
  spawnOffer(type) {
    const busy = new Set(Object.values(this.offers).map((o) => o.store)); if (this.mission) busy.add(this.mission.store);
    const me = this.pos();
    let free = this.world.stores.filter((s) => !busy.has(s) && dist(s.zone.x, s.zone.z, me.x, me.z) > 24);
    if (!free.length) free = this.world.stores.filter((s) => !busy.has(s));
    const climbing = free.filter((s) => s.rank > 3).sort((a, b) => a.rank - b.rank);
    const store = climbing.length && Math.random() < 0.7 ? climbing[0] : pick(climbing.length ? climbing : free);
    const job = JOBS[type], beacon = makeBeacon(job.color, job.label, job.css);
    beacon.g.position.set(store.zone.x, 0, store.zone.z); this.scene.add(beacon.g);
    this.offers[type] = { type, store, beacon };
  }
  dropOffer(type) { const o = this.offers[type]; if (!o) return; this.scene.remove(o.beacon.g); delete this.offers[type]; }

  startJob(o) {
    const job = JOBS[o.type], z = o.store.zone;
    const m = this.mission = { type: o.type, store: o.store, job, tl: job.seconds, need: job.need, got: 0, stage: 0, hold: 0, beacon: null };
    this.dropOffer(o.type);
    if (o.type === 'fix') {
      for (let i = 0; i < m.need; i++) {
        const label = ISSUES[(i + Math.floor(Math.random() * 3)) % ISSUES.length], mesh = makeBug(label);
        const b = { x: z.x + rand(-9, 9), z: z.z + rand(-4, 4), hp: 3, a: rand(0, 6.28), turnAt: 0, mesh, bug: true }; collide(b, 1);
        this.scene.add(mesh.g); this.bugs.push(b);
      }
    } else if (o.type === 'reviews') {
      for (let i = 0; i < m.need; i++) {
        const pt = sidewalkPoint(z.x, z.z, 14, 62), mesh = makeWolf('★ ASK ME', COLORS.customer, i + 1, '#ff9dc8');
        mesh.g.position.set(pt.x, 0, pt.z); mesh.body.rotation.y = rand(0, 6.28); this.scene.add(mesh.g);
        this.customers.push({ x: pt.x, z: pt.z, mesh });
      }
    } else {
      m.pageName = pick(job.pages); this.setBeacon(this.world.hq.zone, 'PICK UP ' + m.pageName.toUpperCase());
    }
    this.sfx.pickup();
    this.ui.brief(o.store.def.name, pick(job.brief), job.label, job.css);
  }
  setBeacon(pt, label) {
    const m = this.mission; if (m.beacon) this.scene.remove(m.beacon.g);
    m.beacon = makeBeacon(m.job.color, label, m.job.css); m.beacon.g.position.set(pt.x, 0, pt.z); this.scene.add(m.beacon.g); m.point = pt;
  }
  clearJob() {
    for (const b of this.bugs) this.scene.remove(b.mesh.g); this.bugs = [];
    for (const c of this.customers) this.scene.remove(c.mesh.g); this.customers = [];
    if (this.mission && this.mission.beacon) this.scene.remove(this.mission.beacon.g);
    this.page.visible = false; this.mission = null;
  }
  finishJob(won) {
    const m = this.mission, S = this.S, type = m.type;
    if (won) {
      const reward = 100 + Math.round(m.tl * 2), before = m.store.rank, was = this.packCount();
      S.leads += reward; S.jobs[type]++;
      m.store.setRank(Math.max(1, before - 3 - Math.floor(Math.random() * 3)));
      S.heat = Math.min(3, S.heat + 1); S.heatT = 24; this.droneAt = now() + 2500;
      this.sfx.capture(); this.ring(m.store.zone.x, m.store.zone.z, m.job.color, 12, 0.7);
      this.ui.banner(`Job done. +${reward} leads`, 2400);
      this.ui.feed(`${m.store.def.name}: rank #${before} to #${m.store.rank}`, m.job.css);
      if (this.packCount() > was) { this.ui.feed(`${m.store.def.name} is in the Map Pack. +3 leads a second.`, '#fff078'); this.ui.fact(FACTS.pack); }
      else this.ui.fact(pick(m.job.facts));
      if (S.heat === 1 && S.jobs.fix + S.jobs.reviews + S.jobs.page === 1) this.pending.push({ at: now() + 6500, fn: () => this.ui.fact(FACTS.heat) });
    } else {
      this.sfx.hurt(); this.ui.banner('Out of time. Client still invisible.', 2400);
    }
    this.clearJob();
    this.pending.push({ at: now() + 2500, fn: () => { if (this.S.phase === 'shift' && !this.offers[type]) this.spawnOffer(type); } });
  }

  target() {
    const p = this.pos(), m = this.mission;
    let best = null, bd = Infinity;
    const consider = (o) => { const d = dist(p.x, p.z, o.x, o.z); if (d < bd) { bd = d; best = o; } };
    if (!m) Object.values(this.offers).forEach((o) => consider(o.store.zone));
    else if (m.type === 'fix') this.bugs.forEach(consider);
    else if (m.type === 'reviews') this.customers.forEach(consider);
    else consider(m.stage === 0 ? this.world.hq.zone : m.store.zone);
    return best && { x: best.x, z: best.z, d: bd };
  }
  pos() { return this.p.inVan ? this.van : this.p; }

  // ---------- effects ----------
  ring(x, z, color, grow, dur) { const mesh = makeRing(color); mesh.position.x = x; mesh.position.z = z; this.scene.add(mesh); this.fx.push({ mesh, t: 0, dur, grow }); }
  starUp(x, z) { const mesh = makeStar(1.8); mesh.position.set(x, 2, z); this.scene.add(mesh); this.fx.push({ mesh, t: 0, dur: 0.9, rise: 7 }); }

  kill(e) {
    this.ring(e.x, e.z, 0xff5252, 3, 0.3); this.scene.remove(e.mesh.g); this.sfx.hit();
    if (e.bug) { this.bugs.splice(this.bugs.indexOf(e), 1); if (this.mission) this.mission.got++; }
    else this.drones.splice(this.drones.indexOf(e), 1);
  }

  // ---------- traffic ----------
  initTraffic() {
    let i = 0;
    for (const r of ROADS) for (const dir of [1, -1]) for (const axis of ['x', 'z']) {
      const lane = axis === 'x' ? r + 3 * dir : r - 3 * dir;
      const c = { axis, dir, lane, t: rand(-100, 100), speed: rand(8, 12), mesh: makeCar(i++), x: 0, z: 0 };
      c.mesh.rotation.y = axis === 'x' ? (dir > 0 ? Math.PI / 2 : -Math.PI / 2) : (dir > 0 ? 0 : Math.PI);
      this.scene.add(c.mesh); this.cars.push(c);
    }
  }
  updateTraffic(dt) {
    const blockers = [this.p.inVan ? null : this.p, this.van].filter(Boolean);
    for (const c of this.cars) {
      let go = true;
      for (const b of blockers) {
        const along = ((c.axis === 'x' ? b.x : b.z) - c.t) * c.dir, side = Math.abs((c.axis === 'x' ? b.z : b.x) - c.lane);
        if (side < 2.8 && along > 0 && along < 9) go = false;
      }
      if (go) c.t += c.dir * c.speed * dt;
      if (c.t > 106) c.t = -106; if (c.t < -106) c.t = 106;
      c.x = c.axis === 'x' ? c.t : c.lane; c.z = c.axis === 'x' ? c.lane : c.t;
      c.mesh.position.set(c.x, 0, c.z);
    }
  }
  pushFromCars(e, R) {
    for (const c of this.cars) {
      const d = dist(e.x, e.z, c.x, c.z), min = R + 1.9;
      if (d < min && d > 1e-4) { e.x = c.x + ((e.x - c.x) / d) * min; e.z = c.z + ((e.z - c.z) / d) * min; }
    }
  }

  // ---------- one simulation step ----------
  tick(dt) {
    const S = this.S, p = this.p, van = this.van, inp = this.input, t = now();
    S.tl -= dt; if (S.tl <= 0) { S.tl = 0; this.endShift(); return; }
    for (let i = this.pending.length - 1; i >= 0; i--) if (t >= this.pending[i].at) this.pending.splice(i, 1)[0].fn();

    // context action: van in, van out, or call the van
    const nearVan = dist(p.x, p.z, van.x, van.z) < 7.5;
    this.action = p.inVan ? 'EXIT VAN' : nearVan ? 'DRIVE' : 'CALL VAN';
    if (inp.act) {
      inp.act = false;
      if (p.inVan) {
        p.inVan = false; van.vx = van.vz = 0;
        p.x = van.x + Math.cos(van.r) * 3.4; p.z = van.z - Math.sin(van.r) * 3.4; collide(p, R_FOOT);
      } else if (nearVan) { p.inVan = true; this.sfx.pickup(); }
      else if (t >= this.callAt) {
        this.callAt = t + 3000;
        const pt = roadPoint(p.x, p.z, 5, 13, 3); Object.assign(van, { x: pt.x, z: pt.z, vx: 0, vz: 0 });
        this.ring(pt.x, pt.z, COLORS.me, 5, 0.5); this.sfx.pickup(); this.ui.banner('Van delivered.', 1200);
      }
    }

    // movement
    let mx = inp.move.x, mz = inp.move.y; const ml = Math.hypot(mx, mz), mag = Math.min(1, ml);
    if (ml > 0.001) { mx /= ml; mz /= ml; }
    if (p.inVan) {
      const k = Math.min(1, dt * (mag > 0.1 ? 2.4 : 3));
      van.vx += (mx * mag * VAN_MAX - van.vx) * k; van.vz += (mz * mag * VAN_MAX - van.vz) * k;
      van.x += van.vx * dt; van.z += van.vz * dt;
      if (collide(van, R_VAN)) { van.vx *= 0.6; van.vz *= 0.6; }
      this.pushFromCars(van, R_VAN);
      if (Math.hypot(van.vx, van.vz) > 1.5) { let dr = Math.atan2(van.vx, van.vz) - van.r; dr = Math.atan2(Math.sin(dr), Math.cos(dr)); van.r += dr * Math.min(1, dt * 9); }
      p.x = van.x; p.z = van.z; p.moving = false;
    } else {
      p.moving = mag > 0.12 && t >= p.stun;
      if (p.moving) { p.x += mx * mag * FOOT * dt; p.z += mz * mag * FOOT * dt; p.r = Math.atan2(mx, mz); p.walk += dt * 14; }
      collide(p, R_FOOT); this.pushFromCars(p, R_FOOT);
    }
    const me = this.pos(), speed = p.inVan ? Math.hypot(van.vx, van.vz) : 0;

    // job offers and the active job
    const m = this.mission;
    if (!m) { for (const o of Object.values(this.offers)) if (dist(me.x, me.z, o.store.zone.x, o.store.zone.z) < ZONE) { this.startJob(o); break; } }
    else {
      m.tl -= dt;
      if (m.type === 'reviews') {
        for (let i = this.customers.length - 1; i >= 0; i--) {
          const c = this.customers[i];
          if (dist(me.x, me.z, c.x, c.z) < (p.inVan ? 5 : 3.4)) {
            this.starUp(c.x, c.z); this.scene.remove(c.mesh.g); this.customers.splice(i, 1); m.got++; this.sfx.capture();
            this.ui.feed(pick(['★★★★★ "Showed up on time."', '★★★★★ "Fixed it first visit."', '★★★★★ "Would call again."', '★★★★★ "Fair price. Great work."']), '#fff078');
          }
        }
      } else if (m.type === 'page') {
        const near = dist(me.x, me.z, m.point.x, m.point.z) < ZONE;
        if (m.stage === 0 && near) { m.stage = 1; this.sfx.pickup(); this.setBeacon(m.store.zone, 'PUBLISH HERE'); this.ui.banner(m.pageName + ' picked up. Deliver it.', 1800); }
        else if (m.stage === 1) { m.hold = near ? m.hold + dt : 0; if (m.hold >= 1.2) m.got = 1; }
        this.page.visible = m.stage === 1;
      }
      if (m.got >= m.need) this.finishJob(true); else if (m.tl <= 0) this.finishJob(false);
    }

    // heat: spam bots hunt the player
    if (S.heat > 0) {
      S.heatT -= dt; if (S.heatT <= 0) { S.heat--; S.heatT = 24; }
      if (t >= this.droneAt && this.drones.length < S.heat * 2) {
        this.droneAt = t + 6000; const pt = roadPoint(me.x, me.z, 30, 48), mesh = makeDrone();
        this.scene.add(mesh.g); this.drones.push({ x: pt.x, z: pt.z, hp: 2, mesh });
      }
    }
    for (let i = this.drones.length - 1; i >= 0; i--) {
      const d = this.drones[i], dd = dist(d.x, d.z, me.x, me.z), sp = 7.5 + S.heat * 0.6;
      if (dd > 0.1) { d.x += ((me.x - d.x) / dd) * sp * dt; d.z += ((me.z - d.z) / dd) * sp * dt; }
      if (dd < (p.inVan ? 2.8 : 1.7)) {
        if (p.inVan && speed > 9) { this.kill(d); continue; }
        const take = Math.min(25, Math.floor(S.leads)); S.leads -= take; S.stolen += take; if (!p.inVan) p.stun = t + 700;
        this.sfx.hurt(); this.ui.flash(); this.ui.feed(`Spam bot stole ${take} leads`, '#ff2d6f'); this.kill(d);
      }
    }
    for (let i = this.bugs.length - 1; i >= 0; i--) {
      const b = this.bugs[i], z = this.mission.store.zone;
      if (t >= b.turnAt) { b.turnAt = t + rand(500, 1400); b.a = dist(b.x, b.z, z.x, z.z) > 14 ? Math.atan2(z.x - b.x, z.z - b.z) : dist(b.x, b.z, me.x, me.z) < 9 ? Math.atan2(b.x - me.x, b.z - me.z) + rand(-0.6, 0.6) : rand(0, 6.28); }
      b.x += Math.sin(b.a) * 5.2 * dt; b.z += Math.cos(b.a) * 5.2 * dt; if (collide(b, 1)) b.turnAt = 0;
      if (p.inVan && speed > 9 && dist(b.x, b.z, me.x, me.z) < 3) this.kill(b);
    }

    // auto aim and auto fire
    let foe = null, fd = RANGE;
    for (const e of this.bugs) { const d = dist(e.x, e.z, me.x, me.z); if (d < fd) { fd = d; foe = e; } }
    for (const e of this.drones) { const d = dist(e.x, e.z, me.x, me.z); if (d < fd) { fd = d; foe = e; } }
    if (foe && t >= p.stun) {
      if (!p.inVan && !p.moving) p.r = Math.atan2(foe.x - p.x, foe.z - p.z);
      if (t >= this.fireAt) {
        this.fireAt = t + (p.inVan ? 480 : 290);
        const mesh = makeStar(0.9); mesh.position.set(me.x, 1.6, me.z); this.scene.add(mesh);
        this.bolts.push({ x: me.x, z: me.z, foe, life: 0.8, mesh }); this.sfx.shoot();
      }
    }
    for (let i = this.bolts.length - 1; i >= 0; i--) {
      const b = this.bolts[i], f = b.foe, alive = this.bugs.includes(f) || this.drones.includes(f);
      const d = dist(b.x, b.z, f.x, f.z); b.life -= dt;
      if (alive && d > 1.3) { b.x += ((f.x - b.x) / d) * 52 * dt; b.z += ((f.z - b.z) / d) * 52 * dt; b.mesh.position.set(b.x, 1.6, b.z); b.mesh.rotation.z += dt * 14; }
      if (!alive || d <= 1.3 || b.life <= 0) {
        if (alive && d <= 2.2 && --f.hp <= 0) this.kill(f);
        this.scene.remove(b.mesh); this.bolts.splice(i, 1);
      }
    }

    // howl
    if (inp.howl) {
      inp.howl = false;
      if (t >= this.howlAt) {
        this.howlAt = t + HOWL_CD; this.ring(me.x, me.z, COLORS.me, HOWL_R, 0.6); this.sfx.howl(1);
        for (const e of [...this.bugs, ...this.drones]) if (dist(e.x, e.z, me.x, me.z) < HOWL_R) this.kill(e);
        this.net.send({ t: 'w', x: +me.x.toFixed(1), z: +me.z.toFixed(1) });
      }
    }

    // Map Pack clients pay every second
    if (t >= this.secAt) { this.secAt = t + 1000; S.leads += 3 * this.packCount(); }

    if (t >= this.sendAt) {
      this.sendAt = t + 120;
      this.net.send({ t: 'p', id: this.me.id, x: +me.x.toFixed(2), z: +me.z.toFixed(2), r: +(p.inVan ? van.r : p.r).toFixed(2), v: p.inVan ? 1 : 0, l: Math.round(S.leads) });
    }
  }

  // ---------- frame ----------
  frame() {
    const t = now(), dt = Math.min(0.05, (t - this.last) / 1000); this.last = t;
    const p = this.p, van = this.van;
    this.updateTraffic(dt);
    if (this.playing && this.S.phase === 'shift') this.tick(dt);

    if (this.wolf) {
      const w = this.wolf; w.g.visible = !p.inVan; w.g.position.set(p.x, 0, p.z); w.body.rotation.y = p.r;
      w.body.position.y = p.moving ? Math.abs(Math.sin(p.walk * 0.8)) * 0.35 : 0;
      w.body.rotation.z = t < p.stun ? Math.sin(t / 40) * 0.25 : 0;
    }
    van.mesh.position.set(van.x, 0, van.z); van.mesh.rotation.y = van.r;
    for (const r of this.remotes.values()) {
      const k = Math.min(1, dt * 10); r.x += (r.tx - r.x) * k; r.z += (r.tz - r.z) * k;
      let dr = r.tr - r.r; dr = Math.atan2(Math.sin(dr), Math.cos(dr)); r.r += dr * k;
      r.wolf.g.visible = r.seen && !r.inVan; r.van.visible = r.seen && r.inVan;
      r.wolf.g.position.set(r.x, 0, r.z); r.wolf.body.rotation.y = r.r; r.van.position.set(r.x, 0, r.z); r.van.rotation.y = r.r;
    }
    for (const b of this.bugs) { b.mesh.g.position.set(b.x, 0, b.z); b.mesh.g.rotation.y = b.a; b.mesh.body.position.y = 1.1 + Math.abs(Math.sin(t / 90 + b.x)) * 0.3; }
    for (const d of this.drones) { d.mesh.g.position.set(d.x, Math.sin(t / 250 + d.x) * 0.3, d.z); d.mesh.halo.rotation.z = t / 200; d.mesh.body.rotation.y = t / 300; }
    for (const c of this.customers) c.mesh.body.position.y = Math.abs(Math.sin(t / 220 + c.x)) * 0.5;
    for (const o of Object.values(this.offers)) o.beacon.ring.rotation.z = t / 600;
    for (const s of this.world.stores) { s.pin.rotation.y = t / 900 + s.x; }
    const me = this.pos();
    if (this.page.visible) { this.page.position.set(me.x, p.inVan ? 4.6 : 4.2, me.z); this.page.rotation.y = t / 400; }

    const tg = this.playing && this.S.phase === 'shift' ? this.target() : null;
    this.arrow.visible = !!tg && tg.d > 7;
    if (tg) { this.arrow.position.set(me.x, 0.2, me.z); this.arrow.rotation.y = Math.atan2(tg.x - me.x, tg.z - me.z); this.arrow.scale.setScalar(p.inVan ? 1.5 : 1); }

    for (let i = this.fx.length - 1; i >= 0; i--) {
      const f = this.fx[i]; f.t += dt; const k = f.t / f.dur;
      if (f.rise) { f.mesh.position.y = 2 + k * f.rise; f.mesh.rotation.z += dt * 8; }
      else { f.mesh.scale.setScalar(1 + k * f.grow); f.mesh.material.opacity = 1 - k; }
      if (k >= 1) { this.scene.remove(f.mesh); this.fx.splice(i, 1); }
    }

    // camera
    if (this.playing) {
      const c = this.cam, lead = p.inVan ? 0.35 : 0;
      c.s += ((p.inVan ? 1.3 : 1) * this.camScale - c.s) * Math.min(1, dt * 3);
      c.x += (me.x + van.vx * lead - c.x) * Math.min(1, dt * 5); c.z += (me.z + van.vz * lead - c.z) * Math.min(1, dt * 5);
      this.camera.position.set(c.x, 42 * c.s, c.z + 24 * c.s); this.camera.lookAt(c.x, 0, c.z - 3);
    } else {
      this.attract += dt * 0.1;
      this.camera.position.set(Math.sin(this.attract) * 46, 46, 74 + Math.cos(this.attract) * 8); this.camera.lookAt(0, 4, -30);
    }
    this.renderer.render(this.scene, this.camera);
    if (this.playing) this.ui.hud(this, tg, clamp((this.howlAt - t) / HOWL_CD, 0, 1));
  }
}

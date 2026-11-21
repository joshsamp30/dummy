// Map Pack Showdown: simulation, netcode and rendering.
// Model: each client owns its own wolf and its own shots. One client is host (earliest joiner)
// and owns shared state: listings, site issues, page pickups, bots, the clock and the score.
import * as THREE from '../vendor/three.module.min.js';
import { CONFIG, TEAMS, STORES, PICKUPS, PAGE_LEADS, ISSUES, FACTS, BOT_NAMES } from './config.js';
import { buildWorld, makeWolf, makeStar, makeHowlRing, colliders, BOUNDS } from './world.js';

const SPEED = 11, BOT_SPEED = 8.5, RADIUS = 0.8;
const FIRE_MS = 240, BOT_FIRE_MS = 750, STAR_SPEED = 38, STAR_LIFE = 1.25;
const HIT_POW = 3, OWN_AT = 30, HOWL_R = 13, HOWL_CD = 12000, HOWL_BOOST = 15;
const MAX_HP = 3, RESPAWN_MS = 3000, SPAM_HP = 6;
const now = () => performance.now();
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const dist = (ax, az, bx, bz) => Math.hypot(ax - bx, az - bz);
const pick = (a) => a[Math.floor(Math.random() * a.length)];

export const ownerOf = (v) => (v >= OWN_AT ? 0 : v <= -OWN_AT ? 1 : -1);
export function mapPack(vals) {
  return vals.map((v, i) => ({ i, v, owner: ownerOf(v) })).filter((s) => s.owner >= 0)
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v) || a.i - b.i).slice(0, 3);
}

function collide(e) {
  for (const c of colliders) {
    if (c.r) {
      const d = dist(e.x, e.z, c.x, c.z), min = c.r + RADIUS;
      if (d < min && d > 1e-4) { e.x = c.x + ((e.x - c.x) / d) * min; e.z = c.z + ((e.z - c.z) / d) * min; }
    } else {
      const nx = clamp(e.x, c.x - c.hw, c.x + c.hw), nz = clamp(e.z, c.z - c.hd, c.z + c.hd);
      const dx = e.x - nx, dz = e.z - nz, d = Math.hypot(dx, dz);
      if (d < RADIUS) {
        if (d > 1e-4) { e.x = nx + (dx / d) * RADIUS; e.z = nz + (dz / d) * RADIUS; }
        else if (c.hw - Math.abs(e.x - c.x) < c.hd - Math.abs(e.z - c.z)) e.x = c.x + Math.sign(e.x - c.x || 1) * (c.hw + RADIUS);
        else e.z = c.z + Math.sign(e.z - c.z || 1) * (c.hd + RADIUS);
      }
    }
  }
  e.x = clamp(e.x, -BOUNDS.x, BOUNDS.x); e.z = clamp(e.z, -BOUNDS.z, BOUNDS.z);
}

function pointHit(x, z) {
  if (Math.abs(x) > BOUNDS.x + 2 || Math.abs(z) > BOUNDS.z + 2) return { wall: true };
  for (const c of colliders) {
    if (c.r) { if (dist(x, z, c.x, c.z) < c.r) return c; }
    else if (Math.abs(x - c.x) < c.hw + 0.3 && Math.abs(z - c.z) < c.hd + 0.3) return c;
  }
  return null;
}

export class Game {
  constructor(canvas, net, me, ui, input, sfx) {
    this.net = net; this.me = me; this.ui = ui; this.input = input; this.sfx = sfx;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, matchMedia('(pointer:coarse)').matches ? 1.5 : 2));
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(50, 1, 0.5, 400);
    this.world = buildWorld(this.scene);
    this.wolves = new Map(); this.stars = []; this.fx = [];
    this.roster = []; this.isHost = false; this.playing = false;
    this.G = { ph: 'wait', tl: 0, v: STORES.map(() => 0), spam: null, pads: [0, 0, 0, 0], sc: [0, 0], round: 0 };
    this.H = null; // host-only timers
    this.my = null; this.stats = this.freshStats(); this.buffs = { photos: 0, cats: 0, shield: 0 };
    this.howlAt = 0; this.fireAt = 0; this.sendAt = 0; this.factAt = 0; this.proxFactShown = false;
    this.ray = new THREE.Raycaster(); this.plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0); this.tmp = new THREE.Vector3();
    this.attract = 0; this.last = now();
    net.onMsg = (m) => this.handle(m, true);
    net.onRoster = (r) => this.onRoster(r);
    addEventListener('resize', () => this.resize()); this.resize();
    this.renderer.setAnimationLoop(() => this.frame());
  }

  freshStats() { return { reviews: 0, captures: 0, fixes: 0, pages: 0 }; }

  resize() {
    const w = innerWidth, h = innerHeight;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    this.camScale = w < h ? 1.25 : 1;
  }

  // ---------- roster and wolves ----------
  onRoster(roster) {
    this.roster = roster;
    const humans = roster.filter((m) => m.team >= 0);
    const ids = new Set(humans.map((m) => m.id));
    for (const m of humans) if (!this.wolves.has(m.id)) this.addWolf(m.id, m.name, m.team, false, m.fur || 0);
    for (const [id, w] of this.wolves) if (!w.bot && !ids.has(id)) this.removeWolf(id);
    const host = [...humans].sort((a, b) => a.j - b.j || (a.id < b.id ? -1 : 1))[0];
    const wasHost = this.isHost;
    this.isHost = !!host && host.id === this.me.id;
    if (this.isHost && !wasHost) this.becomeHost();
    this.ui.setRoster(humans, this.net.kind);
  }

  addWolf(id, name, team, bot, fur) {
    const isMe = id === this.me.id;
    const mesh = makeWolf(name, team, isMe, fur);
    const sx = (team ? 43 : -43) + (Math.random() * 4 - 2), sz = Math.random() * 6 - 3;
    const w = { id, name, team, bot, x: sx, z: sz, r: team ? -Math.PI / 2 : Math.PI / 2, tx: sx, tz: sz, tr: 0,
      hp: MAX_HP, dead: false, stun: 0, shield: false, moving: false, mesh, walk: 0, ai: null };
    this.scene.add(mesh.g); this.wolves.set(id, w);
    if (isMe) this.my = w;
    return w;
  }
  removeWolf(id) { const w = this.wolves.get(id); if (!w) return; this.scene.remove(w.mesh.g); this.wolves.delete(id); }

  spawn(w) {
    w.x = (w.team ? 43 : -43) + (Math.random() * 4 - 2); w.z = Math.random() * 6 - 3;
    w.hp = MAX_HP; w.dead = false; w.stun = 0; w.tx = w.x; w.tz = w.z;
  }

  // ---------- messaging ----------
  emit(m) { this.handle(m, false); this.net.send(m); }

  handle(m, remote) {
    switch (m.t) {
      case 'p': { // player state
        const w = this.wolves.get(m.id); if (!w || w === this.my) break;
        w.tx = m.x; w.tz = m.z; w.tr = m.r; w.hp = m.hp; w.dead = !!(m.f & 1); w.shield = !!(m.f & 4); w.moving = !!(m.f & 8);
        w.stun = m.f & 2 ? now() + 300 : 0;
        break;
      }
      case 's': if (remote) this.addStar(m.x, m.z, m.a, m.team, m.id, false); break;
      case 'h': this.onHit(m); break;
      case 'w': this.onHowl(m); break;
      case 'g': if (this.isHost) this.grantPad(m.pad, m.id); break;
      case 'gv': this.onGrant(m); break;
      case 'e': this.onEvent(m); break;
      case 'k': this.ui.feed(`${this.nameOf(m.by)} sent ${this.nameOf(m.id)} back to the den`); break;
      case 'st': if (!this.isHost) this.onSnapshot(m); break;
    }
  }
  nameOf(id) { const w = this.wolves.get(id); return w ? w.name : 'A wolf'; }

  // ---------- shooting ----------
  addStar(x, z, a, team, shooter, mine, pow = HIT_POW) {
    const mesh = makeStar(team); mesh.position.set(x, 1.4, z); this.scene.add(mesh);
    this.stars.push({ x, z, dx: Math.sin(a), dz: Math.cos(a), life: STAR_LIFE, team, shooter, mine, pow, mesh, ox: x, oz: z });
  }

  shoot(w, a, pow) {
    const x = w.x + Math.sin(a) * 1.6, z = w.z + Math.cos(a) * 1.6;
    this.addStar(x, z, a, w.team, w.id, true, pow);
    this.net.send({ t: 's', id: w.id, x: +x.toFixed(2), z: +z.toFixed(2), a: +a.toFixed(3), team: w.team });
  }

  updateStars(dt) {
    for (let i = this.stars.length - 1; i >= 0; i--) {
      const s = this.stars[i];
      s.x += s.dx * STAR_SPEED * dt; s.z += s.dz * STAR_SPEED * dt; s.life -= dt;
      s.mesh.position.set(s.x, 1.4, s.z); s.mesh.rotation.z += dt * 12;
      let gone = s.life <= 0;
      const c = !gone && pointHit(s.x, s.z);
      if (c) {
        gone = true;
        if (c.store !== undefined) {
          this.burst(s.x, s.z, s.team);
          if (s.mine) {
            const near = dist(s.ox, s.oz, c.x, c.z) < 15;
            this.emit({ t: 'h', k: 's', i: c.store, team: s.team, pow: s.pow * (near ? 1.5 : 1), id: s.shooter });
            if (s.shooter === this.me.id) {
              this.stats.reviews++; this.sfx.hit();
              if (near && !this.proxFactShown) { this.proxFactShown = true; this.fact(FACTS.proximity, true); }
            }
          }
        }
      }
      if (!gone) {
        for (const w of this.wolves.values()) {
          if (w.team === s.team || w.dead || dist(s.x, s.z, w.x, w.z) > 1.25) continue;
          gone = true; this.burst(s.x, s.z, s.team);
          if (s.mine) this.emit({ t: 'h', k: 'w', to: w.id, id: s.shooter });
          break;
        }
      }
      if (gone) { this.scene.remove(s.mesh); this.stars.splice(i, 1); }
    }
  }

  onHit(m) {
    if (m.k === 's') { if (this.isHost) this.hostStoreHit(m.i, m.team, m.pow, m.id); return; }
    const w = this.wolves.get(m.to); if (!w) return;
    if (w === this.my) this.damage(w, m.id);
    else if (w.bot && this.isHost) this.damage(w, m.id);
  }

  damage(w, by) {
    if (w.dead || w.shield || this.G.ph !== 'play') return;
    w.hp--;
    if (w === this.my) { this.sfx.hurt(); this.ui.flash(); }
    if (w.hp <= 0) {
      w.dead = true; w.respawnAt = now() + RESPAWN_MS;
      this.emit({ t: 'k', id: w.id, by });
    }
  }

  // ---------- howl ----------
  howl(w) {
    this.emit({ t: 'w', id: w.id, x: +w.x.toFixed(1), z: +w.z.toFixed(1), team: w.team });
  }
  onHowl(m) {
    const ring = makeHowlRing(m.team); ring.position.x = m.x; ring.position.z = m.z; this.scene.add(ring);
    this.fx.push({ mesh: ring, t: 0, dur: 0.6, grow: HOWL_R });
    this.sfx.howl(m.id === this.me.id ? 1 : 0.4);
    const stunIf = (w) => { if (w.team !== m.team && !w.dead && !w.shield && dist(w.x, w.z, m.x, m.z) < HOWL_R) w.stun = now() + 1600; };
    if (this.my) stunIf(this.my);
    if (this.isHost) {
      for (const w of this.wolves.values()) if (w.bot) stunIf(w);
      this.world.stores.forEach((s, i) => { if (dist(s.front.x, s.front.z, m.x, m.z) < HOWL_R + 2) this.hostStoreHit(i, m.team, HOWL_BOOST, m.id, true); });
    }
  }

  // ---------- pickups ----------
  onGrant(m) {
    const p = PICKUPS[m.type], w = this.wolves.get(m.id);
    if (w) this.burst(w.x, w.z, w.team);
    if (m.id !== this.me.id) return;
    const t = now() + 8000;
    if (p.key === 'photos') this.buffs.photos = t;
    if (p.key === 'cats') this.buffs.cats = t;
    if (p.key === 'reply') { this.my.hp = MAX_HP; this.buffs.shield = now() + 6000; }
    this.stats.pages++; this.sfx.pickup(); this.ui.buff(p.label, p.buff); this.fact(p.fact, true);
  }

  // ---------- events and facts ----------
  onEvent(m) {
    if (m.k === 'cap') {
      const s = STORES[m.i];
      this.ui.feed(`${this.nameOf(m.by)} ranked ${s.name} for ${TEAMS[m.team].name}`, TEAMS[m.team].css);
      if (m.by === this.me.id) { this.stats.captures++; this.sfx.capture(); this.fact(pick(FACTS.capture)); }
    } else if (m.k === 'spam') {
      this.ui.feed(`${ISSUES[m.kind].label} at ${STORES[m.i].name}. Shoot it to fix it.`, '#ff6b6b'); this.fact(ISSUES[m.kind].fact);
    } else if (m.k === 'report') {
      this.ui.feed(`${this.nameOf(m.by)} fixed the site issue. +15 leads for ${TEAMS[m.team].name}`, TEAMS[m.team].css);
      if (m.by === this.me.id) { this.stats.fixes++; this.sfx.capture(); this.fact(FACTS.fixed, true); }
    }
  }
  fact(text, force) {
    if (!force && now() < this.factAt) return;
    this.factAt = now() + 7000; this.ui.fact(text);
  }

  burst(x, z, team) {
    const m = makeHowlRing(team); m.position.set(x, 1.4, z); m.rotation.x = 0; m.lookAt(this.camera.position); this.scene.add(m);
    this.fx.push({ mesh: m, t: 0, dur: 0.25, grow: 1.6 });
  }

  // ---------- host ----------
  becomeHost() {
    const G = this.G;
    this.H = { spamAt: now() + 12000, padAt: G.pads.map(() => now() + 4000), secAt: now() + 1000, snapAt: 0, phaseEnd: 0, prevOwner: G.v.map(ownerOf) };
    if (G.ph === 'wait') this.hostPhase('count', 5);
    else this.H.phaseEnd = now() + G.tl * 1000;
  }
  hostPhase(ph, secs) {
    const G = this.G, H = this.H;
    G.ph = ph; G.tl = secs; H.phaseEnd = now() + secs * 1000;
    if (ph === 'count') {
      G.round++; G.v = STORES.map(() => 0); G.sc = [0, 0]; G.spam = null; G.pads = G.pads.map(() => 0);
      H.prevOwner = G.v.map(() => -1); H.spamAt = now() + 15000; H.padAt = G.pads.map(() => now() + 9000);
      for (const w of this.wolves.values()) if (w.bot) { this.spawn(w); w.ai = null; }
      this.onRound();
    }
    this.snapshot();
  }
  hostStoreHit(i, team, pow, by, isHowl) {
    const G = this.G; if (G.ph !== 'play') return;
    if (G.spam && G.spam.i === i) {
      if (isHowl) return;
      if (--G.spam.hp <= 0) { G.spam = null; G.sc[team] += 15; this.H.spamAt = now() + 9000; this.emit({ t: 'e', k: 'report', team, by }); }
      return;
    }
    G.v[i] = clamp(G.v[i] + (team ? -pow : pow), -100, 100);
    const o = ownerOf(G.v[i]);
    if (o !== this.H.prevOwner[i]) { this.H.prevOwner[i] = o; if (o >= 0) this.emit({ t: 'e', k: 'cap', i, team: o, by }); }
  }
  grantPad(pad, id) {
    const G = this.G, type = G.pads[pad]; if (!type || G.ph !== 'play') return;
    G.pads[pad] = 0; this.H.padAt[pad] = now() + 14000;
    const w = this.wolves.get(id);
    if (w) G.sc[w.team] += PAGE_LEADS;
    if (PICKUPS[type].key === 'nap' && w) G.v = G.v.map((v) => (ownerOf(v) === w.team ? clamp(v + (w.team ? -12 : 12), -100, 100) : v));
    this.emit({ t: 'gv', id, pad, type });
  }
  snapshot() {
    const G = this.G;
    const bots = []; for (const w of this.wolves.values()) if (w.bot) bots.push([w.id, +w.x.toFixed(1), +w.z.toFixed(1), +w.r.toFixed(2), w.hp, w.team, (w.dead ? 1 : 0) | (now() < w.stun ? 2 : 0) | (w.moving ? 8 : 0), w.name]);
    this.net.send({ t: 'st', ph: G.ph, tl: +G.tl.toFixed(1), v: G.v.map(Math.round), spam: G.spam, pads: G.pads, sc: G.sc, round: G.round, bots });
  }
  onSnapshot(m) {
    const G = this.G, newRound = m.round !== G.round;
    Object.assign(G, { ph: m.ph, tl: m.tl, v: m.v, spam: m.spam, pads: m.pads, sc: m.sc, round: m.round });
    if (newRound) this.onRound();
    const seen = new Set();
    for (const [id, x, z, r, hp, team, f, name] of m.bots) {
      seen.add(id);
      const w = this.wolves.get(id) || this.addWolf(id, name, team, true, id.charCodeAt(id.length - 1));
      w.tx = x; w.tz = z; w.tr = r; w.hp = hp; w.dead = !!(f & 1); w.stun = f & 2 ? now() + 300 : 0; w.moving = !!(f & 8);
    }
    for (const [id, w] of this.wolves) if (w.bot && !seen.has(id)) this.removeWolf(id);
  }
  onRound() {
    this.stats = this.freshStats(); this.buffs = { photos: 0, cats: 0, shield: 0 }; this.howlAt = 0; this.shownEnd = false;
    if (this.my) this.spawn(this.my);
    this.ui.hideResults();
  }

  hostTick(dt) {
    const G = this.G, H = this.H, t = now();
    G.tl = Math.max(0, (H.phaseEnd - t) / 1000);
    if (t >= H.phaseEnd) {
      if (G.ph === 'count') this.hostPhase('play', CONFIG.ROUND_SECONDS);
      else if (G.ph === 'play') this.hostPhase('end', 14);
      else this.hostPhase('count', 5);
    }
    this.botRoster();
    if (G.ph === 'play') {
      if (t >= H.secAt) {
        H.secAt = t + 1000;
        const pack = new Set(mapPack(G.v).map((s) => s.i));
        G.v.forEach((v, i) => {
          const o = ownerOf(v); if (o < 0) return;
          if (G.spam && G.spam.i === i) { G.v[i] = v - Math.sign(v) * 4; return; }
          G.sc[o] += pack.has(i) ? 3 : 1;
        });
      }
      if (!G.spam && t >= H.spamAt) {
        const i = Math.floor(Math.random() * STORES.length);
        const kind = Math.floor(Math.random() * ISSUES.length);
        G.spam = { i, hp: SPAM_HP, kind }; this.emit({ t: 'e', k: 'spam', i, kind });
      }
      G.pads.forEach((p, i) => { if (!p && t >= H.padAt[i]) G.pads[i] = 1 + Math.floor(Math.random() * 4); });
    }
    for (const w of this.wolves.values()) {
      if (!w.bot) continue;
      if (w.dead) { if (t >= (w.respawnAt || 0)) this.spawn(w); continue; }
      if (G.ph === 'play') this.botThink(w, dt);
    }
    if (t >= H.snapAt) { H.snapAt = t + 160; this.snapshot(); }
  }

  botRoster() {
    for (let team = 0; team < 2; team++) {
      const humans = this.roster.filter((m) => m.team === team).length;
      const bots = [...this.wolves.values()].filter((w) => w.bot && w.team === team);
      const want = Math.max(0, CONFIG.PACK_SIZE - humans);
      for (let i = bots.length; i < want; i++) {
        const used = new Set([...this.wolves.values()].map((w) => w.name));
        const name = BOT_NAMES.find((n) => !used.has(n)) || 'Wolf';
        const w = this.addWolf('bot' + team + Math.random().toString(36).slice(2, 6), name, team, true, i + team + 1);
        w.respawnAt = 0;
      }
      for (let i = want; i < bots.length; i++) this.removeWolf(bots[i].id);
    }
  }

  botThink(w, dt) {
    const t = now(), G = this.G;
    w.moving = false;
    if (t < w.stun) return;
    const ai = w.ai || (w.ai = { target: -1, retarget: 0, fireAt: t + 600 + Math.random() * 600, howlAt: t + 6000 + Math.random() * 8000, off: 0 });
    const sign = w.team ? -1 : 1;
    if (t >= ai.retarget) {
      let best = Infinity;
      this.world.stores.forEach((s, i) => {
        const v = G.v[i] * sign;
        let score = dist(w.x, w.z, s.front.x, s.front.z) + (v >= OWN_AT ? 45 + v * 0.4 : 0) + Math.random() * 18;
        if (G.spam && G.spam.i === i) score -= 20;
        if (score < best) { best = score; ai.target = i; }
      });
      ai.retarget = t + 4000 + Math.random() * 3500; ai.off = Math.random() * 8 - 4;
    }
    const s = this.world.stores[ai.target];
    const gx = s.front.x + ai.off, gz = s.front.z, d = dist(w.x, w.z, gx, gz);
    if (d > 1.2) {
      const px = w.x, pz = w.z;
      w.x += ((gx - w.x) / d) * BOT_SPEED * dt; w.z += ((gz - w.z) / d) * BOT_SPEED * dt; collide(w);
      if (dist(px, pz, w.x, w.z) < BOT_SPEED * dt * 0.3) { w.x += (Math.random() - 0.5) * 0.8; w.z += (Math.random() - 0.5) * 0.8; collide(w); }
      w.moving = true;
    }
    let foe = null, fd = 13;
    for (const o of this.wolves.values()) { if (o.team === w.team || o.dead) continue; const dd = dist(w.x, w.z, o.x, o.z); if (dd < fd) { fd = dd; foe = o; } }
    const atFoe = foe && (ai.foeBias ?? (ai.foeBias = Math.random())) < 0.45;
    const ax = atFoe ? foe.x : s.def.x, az = atFoe ? foe.z : s.def.z;
    w.r = Math.atan2(ax - w.x, az - w.z);
    if (t >= ai.fireAt && (atFoe || d < 14)) {
      ai.fireAt = t + BOT_FIRE_MS + Math.random() * 250; ai.foeBias = Math.random();
      this.shoot(w, w.r + (Math.random() - 0.5) * 0.14, HIT_POW);
    }
    if (t >= ai.howlAt && ((foe && fd < 8) || (d < 3 && G.v[ai.target] * sign < OWN_AT))) { ai.howlAt = t + 15000; this.howl(w); }
  }

  // ---------- local player ----------
  playerTick(dt) {
    const w = this.my, t = now(), inp = this.input, G = this.G;
    if (!w) return;
    w.shield = t < this.buffs.shield;
    if (w.dead) { if (t >= w.respawnAt) this.spawn(w); }
    else if (G.ph === 'play' || G.ph === 'count') {
      const stunned = t < w.stun;
      let mx = inp.move.x, mz = inp.move.y; const ml = Math.hypot(mx, mz);
      w.moving = ml > 0.1 && !stunned && G.ph === 'play';
      if (w.moving) { const k = Math.min(1, ml) / ml; w.x += mx * k * SPEED * dt; w.z += mz * k * SPEED * dt; collide(w); }
      if (inp.pointer) { // desktop: aim at the cursor on the ground
        this.ray.setFromCamera(inp.pointer, this.camera);
        if (this.ray.ray.intersectPlane(this.plane, this.tmp)) w.r = Math.atan2(this.tmp.x - w.x, this.tmp.z - w.z);
      } else if (Math.hypot(inp.aim.x, inp.aim.y) > 0.2) w.r = Math.atan2(inp.aim.x, inp.aim.y);
      else if (w.moving) w.r = Math.atan2(mx, mz);
      if (G.ph === 'play' && !stunned) {
        if (inp.fire && t >= this.fireAt) {
          this.fireAt = t + (t < this.buffs.cats ? FIRE_MS / 2 : FIRE_MS);
          this.shoot(w, w.r, HIT_POW * (t < this.buffs.photos ? 2 : 1)); this.sfx.shoot();
        }
        if (inp.howl && t >= this.howlAt) { this.howlAt = t + HOWL_CD; this.howl(w); this.fact(FACTS.howl); }
        this.world.pads.forEach((p, i) => { if (G.pads[i] && dist(w.x, w.z, p.x, p.z) < 2 && t >= (p.askAt || 0)) { p.askAt = t + 600; this.emit({ t: 'g', pad: i, id: w.id }); } });
      }
    }
    inp.howl = false;
    if (t >= this.sendAt) {
      this.sendAt = t + 110;
      this.net.send({ t: 'p', id: w.id, x: +w.x.toFixed(2), z: +w.z.toFixed(2), r: +w.r.toFixed(2), hp: w.hp,
        f: (w.dead ? 1 : 0) | (t < w.stun ? 2 : 0) | (w.shield ? 4 : 0) | (w.moving ? 8 : 0) });
    }
  }

  // ---------- frame ----------
  frame() {
    const t = now(), dt = Math.min(0.05, (t - this.last) / 1000); this.last = t;
    const G = this.G;
    if (this.playing) {
      this.playerTick(dt);
      if (this.isHost) this.hostTick(dt); else if (G.ph !== 'wait') G.tl = Math.max(0, G.tl - dt);
    }
    this.updateStars(dt);

    for (const w of this.wolves.values()) {
      if (w !== this.my && !(w.bot && this.isHost)) {
        const k = Math.min(1, dt * 12);
        w.x += (w.tx - w.x) * k; w.z += (w.tz - w.z) * k;
        let dr = w.tr - w.r; dr = Math.atan2(Math.sin(dr), Math.cos(dr)); w.r += dr * k;
      }
      const m = w.mesh; m.g.visible = !w.dead; m.g.position.set(w.x, 0, w.z); m.body.rotation.y = w.r;
      if (w.moving) w.walk += dt * 14;
      m.legs.forEach((l, i) => { l.rotation.x = w.moving ? Math.sin(w.walk + (i % 3 ? Math.PI : 0)) * 0.7 : 0; });
      if (m.tail) m.tail.rotation.y = Math.sin(t / 180 + w.x) * 0.4;
      if (m.model) { m.body.position.y = w.moving ? Math.abs(Math.sin(w.walk * 0.8)) * 0.35 : 0; m.body.rotation.x = w.moving ? Math.sin(w.walk * 1.6) * 0.06 : 0; }
      m.body.rotation.z = t < w.stun ? Math.sin(t / 40) * 0.25 : 0;
      m.shield.visible = w.shield;
    }

    const pack = mapPack(G.v);
    this.world.stores.forEach((s, i) => {
      const v = G.v[i], o = ownerOf(v), col = o < 0 ? 0x8892b0 : TEAMS[o].color;
      s.bar.scale.x = Math.max(0.001, Math.abs(v) / 100); s.bar.material.color.setHex(v === 0 ? 0x8892b0 : TEAMS[v > 0 ? 0 : 1].color);
      s.pin.material.color.setHex(col); s.pin.material.emissive.setHex(o < 0 ? 0x222a44 : col); s.pin.material.emissiveIntensity = 0.5;
      s.pin.rotation.y = t / 900 + i; s.pin.position.y = 9.2 + Math.sin(t / 500 + i) * 0.25;
      const rank = pack.findIndex((p) => p.i === i);
      s.badges.forEach((b, n) => { b.visible = n === rank; });
      const spam = G.spam && G.spam.i === i;
      s.spam.visible = !!spam; if (spam) { s.issueLabels.forEach((l, n) => { l.visible = n === G.spam.kind; }); s.spam.rotation.y = t / 300; s.spam.scale.setScalar(0.6 + 0.4 * (G.spam.hp / SPAM_HP)); }
    });
    this.world.pads.forEach((p, i) => {
      const type = G.pads[i];
      if (type !== p.type) {
        p.type = type; p.gem.visible = !!type; for (const k in p.labels) p.labels[k].visible = +k === type;
        if (type) { p.gem.material.color.setHex(PICKUPS[type].color); p.ring.material.color.setHex(PICKUPS[type].color); } else p.ring.material.color.setHex(0x8892b0);
      }
      p.gem.rotation.y = t / 400; p.gem.position.y = 1.5 + Math.sin(t / 300 + i) * 0.2;
    });
    this.world.statue.rotation.y = t / 4000;

    for (let i = this.fx.length - 1; i >= 0; i--) {
      const f = this.fx[i]; f.t += dt; const k = f.t / f.dur;
      f.mesh.scale.setScalar(1 + k * f.grow); f.mesh.material.opacity = 1 - k;
      if (k >= 1) { this.scene.remove(f.mesh); this.fx.splice(i, 1); }
    }

    // camera
    if (this.playing && this.my) {
      const s = this.camScale, w = this.my;
      this.tmp.set(clamp(w.x, -34, 34), 40 * s, clamp(w.z, -26, 26) + 25 * s);
      this.camera.position.lerp(this.tmp, Math.min(1, dt * 6));
      this.camera.lookAt(this.camera.position.x, 0, this.camera.position.z - 25 * s - 3);
    } else {
      this.attract += dt * 0.12;
      this.camera.position.set(Math.sin(this.attract) * 34, 30, 56 + Math.cos(this.attract) * 6);
      this.camera.lookAt(0, 8, -22);
    }
    this.renderer.render(this.scene, this.camera);

    if (this.playing) {
      this.ui.hud(G, pack, this.my, { howl: clamp((this.howlAt - t) / HOWL_CD, 0, 1), photos: t < this.buffs.photos, cats: t < this.buffs.cats, shield: t < this.buffs.shield });
      if (G.ph === 'end' && !this.shownEnd) { this.shownEnd = true; this.sfx.capture(); this.ui.results(G, this.my, this.stats); }
    }
  }

  start() { this.playing = true; }
}

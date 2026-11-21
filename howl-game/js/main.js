// Bootstrap: email gate, menu, input, HUD, sound.
import { CONFIG, TEAMS, STORES } from './config.js';
import { createNet, saveLead } from './net.js';
import { Game } from './game.js';

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };

// ---------- sound ----------
const sfx = (() => {
  let ac;
  const tone = (f0, f1, dur, type = 'sine', vol = 0.12) => {
    if (!ac) return;
    const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime;
    o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g).connect(ac.destination); o.start(t); o.stop(t + dur);
  };
  return {
    unlock() { try { ac = ac || new (window.AudioContext || window.webkitAudioContext)(); ac.resume(); } catch {} },
    shoot: () => tone(900, 500, 0.08, 'triangle', 0.06),
    hit: () => tone(1200, 1600, 0.06, 'sine', 0.05),
    hurt: () => tone(200, 80, 0.2, 'sawtooth', 0.1),
    pickup: () => { tone(600, 1200, 0.15); setTimeout(() => tone(900, 1800, 0.15), 90); },
    capture: () => { tone(520, 520, 0.12); setTimeout(() => tone(780, 780, 0.2), 110); },
    howl: (v = 1) => tone(280, 620, 0.7, 'sine', 0.14 * v),
  };
})();

// ---------- input ----------
const input = { move: { x: 0, y: 0 }, aim: { x: 0, y: 0 }, fire: false, howl: false, pointer: null };
function setupInput(canvas) {
  const keys = new Set();
  const sync = () => {
    input.move.x = (keys.has('d') || keys.has('arrowright') ? 1 : 0) - (keys.has('a') || keys.has('arrowleft') ? 1 : 0);
    input.move.y = (keys.has('s') || keys.has('arrowdown') ? 1 : 0) - (keys.has('w') || keys.has('arrowup') ? 1 : 0);
  };
  addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key.toLowerCase();
    if (k === ' ' || k === 'e') { input.howl = true; e.preventDefault(); }
    keys.add(k); sync();
  });
  addEventListener('keyup', (e) => { keys.delete(e.key.toLowerCase()); sync(); });
  addEventListener('blur', () => { keys.clear(); sync(); input.fire = false; });

  const sticks = { L: { el: $('stickL'), id: null, v: input.move }, R: { el: $('stickR'), id: null, v: input.aim } };
  const R = 52;
  const moveStick = (s, e) => {
    let dx = e.clientX - s.ox, dy = e.clientY - s.oy; const d = Math.hypot(dx, dy);
    if (d > R) { dx *= R / d; dy *= R / d; }
    s.v.x = dx / R; s.v.y = dy / R;
    s.el.firstElementChild.style.transform = `translate(${dx}px, ${dy}px)`;
    if (s === sticks.R) input.fire = d > R * 0.3;
  };
  canvas.addEventListener('pointerdown', (e) => {
    sfx.unlock();
    if (e.pointerType === 'mouse') { input.fire = true; return; }
    input.pointer = null;
    const s = e.clientX < innerWidth / 2 ? sticks.L : sticks.R;
    if (s.id !== null) return;
    s.id = e.pointerId; s.ox = e.clientX; s.oy = e.clientY;
    s.el.style.left = e.clientX + 'px'; s.el.style.top = e.clientY + 'px'; s.el.classList.add('on');
    moveStick(s, e);
  });
  canvas.addEventListener('pointermove', (e) => {
    if (e.pointerType === 'mouse') {
      input.pointer = input.pointer || { x: 0, y: 0 };
      input.pointer.x = (e.clientX / innerWidth) * 2 - 1; input.pointer.y = -(e.clientY / innerHeight) * 2 + 1;
      return;
    }
    for (const s of Object.values(sticks)) if (s.id === e.pointerId) moveStick(s, e);
  });
  const up = (e) => {
    if (e.pointerType === 'mouse') { input.fire = false; return; }
    for (const s of Object.values(sticks)) if (s.id === e.pointerId) {
      s.id = null; s.v.x = 0; s.v.y = 0; s.el.classList.remove('on');
      if (s === sticks.R) input.fire = false;
    }
  };
  addEventListener('pointerup', up); addEventListener('pointercancel', up);
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  $('btnHowl').addEventListener('pointerdown', (e) => { e.preventDefault(); input.howl = true; });
}

// ---------- HUD ----------
const ui = (() => {
  let hudAt = 0, factTimer, buffTimer, lastPack = '';
  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  return {
    setRoster(humans, kind) {
      $('roomInfo').textContent = kind === 'online'
        ? `${humans.length} wolf${humans.length === 1 ? '' : 'es'} in this room. Bots fill empty spots.`
        : 'Offline mode. You play with bot wolves.';
    },
    hud(G, pack, me, s) {
      const t = performance.now(); if (t < hudAt) return; hudAt = t + 100;
      $('sc0').textContent = G.sc[0]; $('sc1').textContent = G.sc[1];
      $('clock').textContent = G.ph === 'play' ? fmt(G.tl) : G.ph === 'end' ? 'END' : fmt(CONFIG.ROUND_SECONDS);
      const html = [0, 1, 2].map((n) => {
        const p = pack[n];
        if (!p) return `<li class="open"><span class="n">${n + 1}</span><span class="nm">Open spot</span></li>`;
        const stars = '★'.repeat(Math.max(1, Math.round(Math.abs(p.v) / 20)));
        return `<li><span class="n" style="background:${TEAMS[p.owner].css}">${n + 1}</span><span class="nm">${STORES[p.i].name}</span><span class="st">${stars}</span></li>`;
      }).join('');
      if (html !== lastPack) { lastPack = html; $('packList').innerHTML = html; }
      let banner = '';
      if (G.ph === 'wait') banner = 'Joining the pack...';
      else if (G.ph === 'count') banner = 'Match starts in ' + Math.ceil(G.tl);
      else if (G.ph === 'play' && me) {
        if (me.dead) banner = 'Back to the den...';
        else if (t < me.stun) banner = 'Howled at!';
      }
      $('banner').textContent = banner;
      if (me) {
        $('hp').textContent = '🐾'.repeat(Math.max(0, me.hp));
        document.querySelector('.score.t0').classList.toggle('mine', me.team === 0);
        document.querySelector('.score.t1').classList.toggle('mine', me.team === 1);
      }
      const b = $('btnHowl'); b.style.setProperty('--p', (1 - s.howl) * 100 + '%'); b.classList.toggle('ready', s.howl === 0);
      if (G.ph === 'end') $('resNext').textContent = 'Next match in ' + Math.ceil(G.tl + 5);
    },
    fact(text) {
      $('factText').textContent = text; $('fact').classList.add('on');
      clearTimeout(factTimer); factTimer = setTimeout(() => $('fact').classList.remove('on'), 6000);
    },
    buff(label, what) {
      $('buff').textContent = `${label}: ${what}`;
      clearTimeout(buffTimer); buffTimer = setTimeout(() => { $('buff').textContent = ''; }, 8000);
    },
    feed(text, color) {
      const d = document.createElement('div'); d.textContent = text; if (color) d.style.borderRight = `3px solid ${color}`;
      const f = $('feed'); f.prepend(d); while (f.children.length > 4) f.lastChild.remove();
      setTimeout(() => d.remove(), 5000);
    },
    flash() { const f = $('flash'); f.classList.add('on'); setTimeout(() => f.classList.remove('on'), 80); },
    results(G, me, st) {
      const [a, b] = G.sc, win = a === b ? -1 : a > b ? 0 : 1;
      $('resTitle').innerHTML = win < 0 ? 'Dead heat' : (me && me.team === win ? 'Your pack owns<span>the Map Pack</span>' : `${TEAMS[win].name} took<span>the Map Pack</span>`);
      $('resScore').textContent = `Night Pack ${a} leads. Dawn Pack ${b} leads.`;
      $('resStats').innerHTML = [['Reviews', st.reviews], ['Rankings', st.captures], ['Spam reports', st.reports], ['Tags', st.tags]]
        .map(([l, v]) => `<li><b>${v}</b>${l}</li>`).join('');
      $('results').hidden = false;
    },
    hideResults() { $('results').hidden = true; },
  };
})();

// ---------- flow ----------
const me = {
  id: (() => { let v = sessionStorage.getItem('howl-id'); if (!v) { v = Math.random().toString(36).slice(2, 10); sessionStorage.setItem('howl-id', v); } return v; })(),
  name: 'Wolf', team: -1, j: Date.now(), fur: Math.floor(Math.random() * 4),
};
let room = (params.get('room') || '').toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 24);
const isPrivate = () => !!room && !room.startsWith('town-square');
let net, game;

function inviteUrl() {
  if (!room) { room = Math.random().toString(36).slice(2, 7); history.replaceState(null, '', '?room=' + room); }
  return location.origin + location.pathname + '?room=' + room;
}
async function share(btn) {
  const url = inviteUrl(), label = btn.textContent;
  try {
    if (navigator.share && matchMedia('(pointer:coarse)').matches) await navigator.share({ title: 'Map Pack Showdown', text: 'Join my wolf pack.', url });
    else { await navigator.clipboard.writeText(url); btn.textContent = 'Link copied'; }
  } catch { btn.textContent = url.replace(/^https?:\/\//, ''); }
  setTimeout(() => { btn.textContent = label; }, 2500);
}

async function joinRoom() {
  // Public rooms overflow to the next one when full. Private rooms never hop.
  for (let n = 1; n < 20; n++) {
    const name = isPrivate() ? room : 'town-square' + (n > 1 ? '-' + n : '');
    let roster = [];
    const prev = net.onRoster; net.onRoster = (r) => { roster = r; prev(r); };
    await net.join(name, me);
    await new Promise((r) => setTimeout(r, net.kind === 'online' ? 900 : 100));
    net.onRoster = prev;
    const humans = roster.filter((m) => m.team >= 0);
    if (!isPrivate() && humans.length >= CONFIG.ROOM_CAP) { await net.leave(); continue; }
    const c = [0, 1].map((t) => humans.filter((m) => m.team === t).length);
    me.team = c[0] === c[1] ? Math.floor(Math.random() * 2) : c[0] < c[1] ? 0 : 1;
    me.j = Date.now();
    net.update(me);
    room = name;
    return name;
  }
  throw new Error('All rooms are full');
}

async function play() {
  const btn = $('btnPlay'); btn.disabled = true; btn.textContent = 'Joining...'; sfx.unlock();
  try {
    await joinRoom();
    $('menu').hidden = true; $('hud').hidden = false;
    game.start();
  } catch (e) {
    btn.disabled = false; btn.textContent = 'Try again';
    $('roomInfo').textContent = 'Could not connect. ' + e.message;
  }
}

function showMenu() { $('gate').hidden = true; $('menu').hidden = false; }

async function boot() {
  try { await Promise.all([document.fonts.load('700 40px Poppins'), document.fonts.load('600 26px Poppins')]); } catch {}
  net = createNet();
  game = new Game($('game'), net, me, ui, input, sfx);
  window.__howl = game; // handy for debugging
  setupInput($('game'));
  $('cta').href = CONFIG.CTA_URL || '#'; $('cta').hidden = !CONFIG.CTA_URL;
  $('roomInfo').textContent = net.kind === 'online' ? 'Live multiplayer. Friends with your link join your match.' : 'Offline mode. You play with bot wolves.';

  const saved = store.get('howl-lead');
  if (saved) { try { me.name = JSON.parse(saved).name || me.name; showMenu(); } catch {} }

  $('gateForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = $('fName').value.trim().slice(0, 16), email = $('fEmail').value.trim().toLowerCase();
    const err = $('gateErr'), btn = e.target.querySelector('button');
    if (name.length < 2) { err.textContent = 'Add a name. Two letters or more.'; return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { err.textContent = 'That email does not look right.'; return; }
    err.textContent = ''; btn.disabled = true; btn.textContent = 'Saving...';
    try {
      await saveLead({ name, email, room: room || 'town-square' });
      store.set('howl-lead', JSON.stringify({ name, email }));
      me.name = name; showMenu();
    } catch (ex) {
      err.textContent = 'Could not save. Check your connection and try again.';
      console.error(ex);
    }
    btn.disabled = false; btn.textContent = 'Unlock the game';
  });
  $('btnPlay').addEventListener('click', play);
  $('btnShare').addEventListener('click', (e) => share(e.currentTarget));
  $('btnInvite').addEventListener('click', (e) => share(e.currentTarget));
}
boot();

// Bootstrap: email gate, menu, one-stick input, HUD, minimap, sound.
import { CONFIG, JOBS } from './config.js';
import { createNet, saveLead } from './net.js';
import { Game } from './game.js';

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

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
    shoot: () => tone(900, 500, 0.07, 'triangle', 0.04),
    hit: () => tone(300, 900, 0.09, 'square', 0.04),
    hurt: () => tone(200, 80, 0.25, 'sawtooth', 0.1),
    pickup: () => { tone(600, 1200, 0.15); setTimeout(() => tone(900, 1800, 0.15), 90); },
    capture: () => { tone(520, 520, 0.12); setTimeout(() => tone(780, 780, 0.2), 110); },
    howl: (v = 1) => tone(280, 620, 0.7, 'sine', 0.14 * v),
  };
})();

// ---------- input: one stick, two buttons ----------
const input = { move: { x: 0, y: 0 }, act: false, howl: false };
function setupInput(canvas) {
  const keys = new Set(); let stickId = null, ox = 0, oy = 0; const el = $('stickL'), R = 56;
  const sync = () => {
    if (stickId !== null) return;
    input.move.x = (keys.has('d') || keys.has('arrowright') ? 1 : 0) - (keys.has('a') || keys.has('arrowleft') ? 1 : 0);
    input.move.y = (keys.has('s') || keys.has('arrowdown') ? 1 : 0) - (keys.has('w') || keys.has('arrowup') ? 1 : 0);
  };
  addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key.toLowerCase();
    if (!e.repeat && (k === ' ' || k === 'e' || k === 'enter')) input.act = true;
    if (!e.repeat && (k === 'q' || k === 'f' || k === 'shift' || k === 'h')) input.howl = true;
    if (k === ' ' || k.startsWith('arrow')) e.preventDefault();
    keys.add(k); sync();
  });
  addEventListener('keyup', (e) => { keys.delete(e.key.toLowerCase()); sync(); });
  addEventListener('blur', () => { keys.clear(); sync(); });

  const drag = (e) => {
    let dx = e.clientX - ox, dy = e.clientY - oy; const d = Math.hypot(dx, dy);
    if (d > R) { dx *= R / d; dy *= R / d; }
    input.move.x = dx / R; input.move.y = dy / R;
    el.firstElementChild.style.transform = `translate(${dx}px, ${dy}px)`;
  };
  canvas.addEventListener('pointerdown', (e) => {
    sfx.unlock(); if (stickId !== null) return;
    stickId = e.pointerId; ox = e.clientX; oy = e.clientY;
    el.style.left = ox + 'px'; el.style.top = oy + 'px'; el.classList.add('on'); drag(e);
  });
  addEventListener('pointermove', (e) => { if (e.pointerId === stickId) drag(e); });
  const up = (e) => { if (e.pointerId !== stickId) return; stickId = null; el.classList.remove('on'); input.move.x = 0; input.move.y = 0; sync(); };
  addEventListener('pointerup', up); addEventListener('pointercancel', up);
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  $('btnAct').addEventListener('pointerdown', (e) => { e.preventDefault(); sfx.unlock(); input.act = true; });
  $('btnHowl').addEventListener('pointerdown', (e) => { e.preventDefault(); sfx.unlock(); input.howl = true; });
}

// ---------- HUD ----------
const ui = (() => {
  let hudAt = 0, timers = {}, last = {};
  const set = (id, html) => { if (last[id] !== html) { last[id] = html; $(id).innerHTML = html; } };
  const show = (id, ms) => { $(id).classList.add('on'); clearTimeout(timers[id]); timers[id] = setTimeout(() => $(id).classList.remove('on'), ms); };
  const map = $('map').getContext('2d'), M = 148, sc = (v) => ((v + 104) / 208) * M;
  const css = (n) => '#' + n.toString(16).padStart(6, '0');

  function drawMap(g, tg) {
    const t = performance.now(), dot = (x, z, r, c) => { map.fillStyle = c; map.beginPath(); map.arc(sc(x), sc(z), r, 0, 7); map.fill(); };
    map.fillStyle = '#101010'; map.fillRect(0, 0, M, M);
    map.strokeStyle = '#3b4468'; map.lineWidth = 7;
    for (const r of [-60, 0, 60]) { map.beginPath(); map.moveTo(sc(r), 0); map.lineTo(sc(r), M); map.moveTo(0, sc(r)); map.lineTo(M, sc(r)); map.stroke(); }
    for (const s of g.world.stores) { map.fillStyle = s.rank <= 3 ? '#fff078' : '#8892b0'; map.fillRect(sc(s.x) - 3, sc(s.z) - 3, 6, 6); }
    map.fillStyle = '#092aff'; map.fillRect(sc(g.world.hq.x) - 4, sc(g.world.hq.z) - 4, 8, 8);
    const pulse = 4.5 + Math.sin(t / 200) * 1.5;
    for (const o of Object.values(g.offers)) dot(o.store.zone.x, o.store.zone.z, pulse, css(o.beacon ? JOBS[o.type].color : 0xffffff));
    if (g.mission && g.mission.point) dot(g.mission.point.x, g.mission.point.z, pulse, JOBS[g.mission.type].css);
    for (const b of g.bugs) dot(b.x, b.z, 2.5, '#ff5252');
    for (const c of g.customers) dot(c.x, c.z, 3.2, '#ff5fa8');
    for (const d of g.drones) dot(d.x, d.z, 2.5, '#ff2d6f');
    for (const r of g.remotes.values()) if (r.seen) dot(r.x, r.z, 3, '#4d6bff');
    if (!g.p.inVan) { map.fillStyle = '#faf9f5'; map.fillRect(sc(g.van.x) - 2.5, sc(g.van.z) - 2.5, 5, 5); }
    const me = g.pos(); dot(me.x, me.z, 4.5, '#fff078'); map.strokeStyle = '#101010'; map.lineWidth = 1.5; map.stroke();
    if (tg) { map.strokeStyle = 'rgba(255,240,120,.7)'; map.lineWidth = 1.5; map.setLineDash([3, 3]); map.beginPath(); map.moveTo(sc(me.x), sc(me.z)); map.lineTo(sc(tg.x), sc(tg.z)); map.stroke(); map.setLineDash([]); }
  }

  return {
    setRoster(n, kind) {
      $('roomInfo').textContent = kind === 'online' ? `${n} wolf${n === 1 ? '' : 'es'} in town right now.` : 'Offline mode. You have the town to yourself.';
    },
    hud(g, tg, howl) {
      const t = performance.now(); if (t < hudAt) return; hudAt = t + 100;
      const S = g.S, m = g.mission;
      set('leads', String(Math.round(S.leads))); set('clock', fmt(S.tl));
      set('heat', [1, 2, 3].map((n) => `<i class="${n <= S.heat ? 'hot' : ''}"></i>`).join(''));
      $('clock').classList.toggle('low', S.tl < 20);
      if (m) {
        const prog = m.type === 'page' ? (m.stage === 0 ? 'Pick up the ' + m.pageName + ' at HQ' : m.hold > 0 ? 'Publishing...' : 'Deliver the ' + m.pageName) : `${m.job.goal} ${m.got}/${m.need}`;
        set('job', `<b style="background:${m.job.css}">${m.job.label}</b><span>${esc(m.store.def.name)}. ${prog}</span><em>${fmt(Math.max(0, m.tl))}${tg && tg.d > 7 ? ' · ' + Math.round(tg.d) + ' m' : ''}</em>`);
      } else set('job', `<b>PICK A JOB</b><span>Follow the arrow to a client.</span><em>${tg ? Math.round(tg.d) + ' m' : ''}</em>`);
      const top = [...g.world.stores].sort((a, b) => a.rank - b.rank).slice(0, 3);
      set('packList', top.map((s) => `<li class="${s.rank <= 3 ? 'in' : ''}"><span class="n">#${s.rank}</span><span class="nm">${esc(s.def.name)}</span></li>`).join(''));
      set('packHead', `${g.packCount()}/3 Map Pack`);
      const board = g.board();
      set('board', board.length > 1 ? board.slice(0, 4).map((r, i) => `<li class="${r.me ? 'me' : ''}"><span>${i + 1}. ${esc(r.name)}</span><b>${r.leads}</b></li>`).join('') : '');
      set('actLabel', g.action);
      const b = $('btnHowl'); b.style.setProperty('--p', (1 - howl) * 100 + '%'); b.classList.toggle('ready', howl === 0);
      drawMap(g, tg);
    },
    banner(text, ms) { $('banner').textContent = text; show('banner', ms); },
    brief(name, quote, label, color) { $('brief').innerHTML = `<b style="background:${color}">${label}</b><strong>${esc(name)}</strong><span>"${esc(quote)}"</span>`; show('brief', 3600); },
    fact(text) { $('factText').textContent = text; show('fact', 6500); },
    feed(text, color) {
      const d = document.createElement('div'); d.textContent = text; if (color) d.style.borderLeft = `3px solid ${color}`;
      const f = $('feed'); f.prepend(d); while (f.children.length > 3) f.lastChild.remove();
      setTimeout(() => d.remove(), 5000);
    },
    flash() { const f = $('flash'); f.classList.add('on'); setTimeout(() => f.classList.remove('on'), 80); },
    results(S, pack, board) {
      const jobs = S.jobs.fix + S.jobs.reviews + S.jobs.page, leads = Math.round(S.leads);
      const title = pack >= 3 ? ['You own', 'the Map Pack.'] : pack > 0 ? ['Clients are', 'getting found.'] : jobs > 0 ? ['Good start.', 'Keep climbing.'] : ['Shift over.', 'Take a job next time.'];
      $('resTitle').innerHTML = `${title[0]}<span>${title[1]}</span>`;
      $('resScore').textContent = `${leads} leads generated. ${pack} of 3 Map Pack spots filled.`;
      $('resStats').innerHTML = [['Site fixes', S.jobs.fix], ['Review jobs', S.jobs.reviews], ['New pages', S.jobs.page], ['Map Pack', pack]].map(([l, v]) => `<li><b>${v}</b>${l}</li>`).join('');
      $('resBoard').innerHTML = board.length > 1 ? board.slice(0, 5).map((r, i) => `<li class="${r.me ? 'me' : ''}"><span>${i + 1}. ${esc(r.name)}</span><b>${r.leads}</b></li>`).join('') : '';
      $('results').hidden = false;
    },
    hideResults() { $('results').hidden = true; },
  };
})();

// ---------- flow ----------
const me = {
  id: (() => { let v = sessionStorage.getItem('howl-id'); if (!v) { v = Math.random().toString(36).slice(2, 10); sessionStorage.setItem('howl-id', v); } return v; })(),
  name: 'Wolf', fur: Math.floor(Math.random() * 4),
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
    if (navigator.share && matchMedia('(pointer:coarse)').matches) await navigator.share({ title: 'Map Pack Showdown', text: 'Race me for the Map Pack.', url });
    else { await navigator.clipboard.writeText(url); btn.textContent = 'Link copied'; }
  } catch { btn.textContent = url.replace(/^https?:\/\//, ''); }
  setTimeout(() => { btn.textContent = label; }, 2500);
}

async function joinRoom() {
  // Public rooms overflow to the next one when full. Private rooms never hop.
  for (let n = 1; n < 20; n++) {
    const name = isPrivate() ? room : 'town-square' + (n > 1 ? '-' + n : '');
    let count = 0;
    const prev = net.onRoster; net.onRoster = (r) => { count = r.length; prev(r); };
    await net.join(name, me);
    await new Promise((r) => setTimeout(r, net.kind === 'online' ? 800 : 100));
    net.onRoster = prev;
    if (!isPrivate() && count > CONFIG.ROOM_CAP) { await net.leave(); continue; }
    room = name; return name;
  }
  throw new Error('The town is full');
}

async function play() {
  const btn = $('btnPlay'); btn.disabled = true; btn.textContent = 'Clocking in...'; sfx.unlock();
  try { await Promise.race([joinRoom(), new Promise((_, no) => setTimeout(() => no(new Error('timeout')), 7000))]); } catch (e) { console.warn('Playing without multiplayer:', e.message); }
  $('menu').hidden = true; $('hud').hidden = false;
  game.start();
}

function showMenu() { $('gate').hidden = true; $('menu').hidden = false; }

async function boot() {
  try { await Promise.all([document.fonts.load('700 40px Poppins'), document.fonts.load('600 26px Poppins')]); } catch {}
  net = createNet();
  game = new Game($('game'), net, me, ui, input, sfx);
  window.__howl = game; // handy for debugging
  setupInput($('game'));
  $('cta').href = CONFIG.CTA_URL || '#'; $('cta').hidden = !CONFIG.CTA_URL;
  $('roomInfo').textContent = net.kind === 'online' ? 'Live town. Friends with your link race you for leads.' : 'Offline mode. You have the town to yourself.';

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
  $('btnAgain').addEventListener('click', () => { sfx.unlock(); game.startShift(); });
  $('btnShare').addEventListener('click', (e) => share(e.currentTarget));
  $('btnInvite').addEventListener('click', (e) => share(e.currentTarget));
}
boot();

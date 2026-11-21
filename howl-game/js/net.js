// Realtime transport. Two implementations behind one interface:
//   SupabaseNet: Supabase Realtime (WebSockets). Broadcast for messages, Presence for the roster.
//   LocalNet:    BroadcastChannel. Same-device tabs. Used when Supabase is not configured.
// Interface: join(room, meta) -> Promise, update(meta), send(msg), leave(), onMsg, onRoster.
import { CONFIG } from './config.js';

export function supabaseClient() {
  if (!CONFIG.SUPABASE_URL || !window.supabase) return null;
  if (!supabaseClient.c) {
    supabaseClient.c = window.supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_KEY, {
      auth: { persistSession: false },
      realtime: { params: { eventsPerSecond: 40 } },
    });
  }
  return supabaseClient.c;
}

class SupabaseNet {
  constructor() { this.onMsg = () => {}; this.onRoster = () => {}; this.kind = 'online'; }
  join(room, meta) {
    this.meta = meta;
    const client = supabaseClient();
    return new Promise((resolve, reject) => {
      const ch = client.channel('howl:' + room, {
        config: { broadcast: { self: false }, presence: { key: meta.id } },
      });
      this.ch = ch;
      ch.on('broadcast', { event: 'm' }, ({ payload }) => this.onMsg(payload));
      ch.on('presence', { event: 'sync' }, () => {
        const state = ch.presenceState();
        const roster = Object.values(state).map((arr) => arr[arr.length - 1]).filter((m) => m && m.id);
        this.onRoster(roster);
      });
      let done = false;
      ch.subscribe(async (status) => {
        if (status === 'SUBSCRIBED') {
          await ch.track(this.meta);
          if (!done) { done = true; resolve(); }
        } else if ((status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') && !done) {
          done = true; reject(new Error(status));
        }
      });
    });
  }
  update(meta) { this.meta = meta; if (this.ch) this.ch.track(meta); }
  send(msg) { if (this.ch) this.ch.send({ type: 'broadcast', event: 'm', payload: msg }); }
  async leave() { if (this.ch) { const ch = this.ch; this.ch = null; await supabaseClient().removeChannel(ch); } }
}

class LocalNet {
  constructor() { this.onMsg = () => {}; this.onRoster = () => {}; this.kind = 'local'; this.peers = new Map(); }
  join(room, meta) {
    this.meta = meta;
    this.bc = new BroadcastChannel('howl:' + room);
    this.bc.onmessage = (e) => {
      const d = e.data;
      if (d.__p) {
        if (d.__p === 'bye') this.peers.delete(d.id);
        else {
          this.peers.set(d.meta.id, { meta: d.meta, seen: performance.now() });
          if (d.__p === 'hello') this.bc.postMessage({ __p: 'here', meta: this.meta });
        }
        this._sync();
      } else this.onMsg(d);
    };
    this.bc.postMessage({ __p: 'hello', meta });
    this.timer = setInterval(() => {
      this.bc.postMessage({ __p: 'hb', meta: this.meta });
      const now = performance.now();
      let changed = false;
      for (const [id, p] of this.peers) if (now - p.seen > 3500) { this.peers.delete(id); changed = true; }
      if (changed) this._sync();
    }, 1000);
    this._bye = () => this.bc && this.bc.postMessage({ __p: 'bye', id: this.meta.id });
    addEventListener('pagehide', this._bye);
    return new Promise((r) => setTimeout(() => { this._sync(); r(); }, 350));
  }
  _sync() { this.onRoster([this.meta, ...[...this.peers.values()].map((p) => p.meta)]); }
  update(meta) { this.meta = meta; this.bc.postMessage({ __p: 'hb', meta }); this._sync(); }
  send(msg) { if (this.bc) this.bc.postMessage(msg); }
  async leave() {
    if (!this.bc) return;
    this._bye(); clearInterval(this.timer); removeEventListener('pagehide', this._bye);
    this.bc.close(); this.bc = null; this.peers.clear();
  }
}

export function createNet() {
  return supabaseClient() ? new SupabaseNet() : new LocalNet();
}

// Email gate storage. Supabase table when configured, Netlify Forms otherwise.
export async function saveLead(lead) {
  const client = supabaseClient();
  if (client) {
    const { error } = await client.from('leads').insert(lead);
    if (error) throw new Error(error.message);
    return 'supabase';
  }
  if (['localhost', '127.0.0.1', ''].includes(location.hostname)) return 'dev';
  const body = new URLSearchParams({ 'form-name': 'howl-leads', ...lead }).toString();
  const res = await fetch('/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
  if (!res.ok) throw new Error('Form save failed (' + res.status + ')');
  return 'netlify';
}

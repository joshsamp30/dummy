# Map Pack Showdown

A 3D multiplayer browser game from Local Howl. Two wolf packs fight for the local Map Pack.

## How it plays

- Shoot review stars at storefronts to rank them for your pack.
- The top 3 listings are the Map Pack. They pay triple leads.
- Howl stuns rivals and boosts nearby listings. 12 second cooldown.
- Technical site issues (404, slow page, no HTTPS and more) break a storefront. Shoot the warning to fix it.
- Floating pages are new website pages: Service, FAQ, About, Location. Each pays leads and gives a boost.
- Rounds last 2:30.

## Stack

- Three.js. No build step. Static files only.
- Realtime over WebSockets with Supabase Realtime (Broadcast and Presence).
- One client is host and owns shared state. Host moves to the next player if they leave.
- Bots fill each pack to 3 wolves.
- Email gate writes to the `leads` table. SQL is in `supabase/001_leads.sql`.

## Go live with multiplayer

1. Create a Supabase project. Run `supabase/001_leads.sql`.
2. Put the project URL and publishable key in `js/config.js`.
3. Deploy this folder to any static host.

With no Supabase config the game runs offline: solo with bots, or several tabs on one device.

## Run locally

```bash
python3 -m http.server 8000
```

## Rooms

- No `?room=` joins the public `town-square` room. It overflows at 8 players.
- `?room=abc12` is a private room. The Invite button builds this link.

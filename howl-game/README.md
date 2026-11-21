# Map Pack Showdown

A 3D multiplayer browser game from Local Howl. Two wolf packs fight for the local Map Pack.

## How it plays

An open town and a 3 minute shift, built around one player.

- Roam on foot or in the Local Howl van. One stick moves. Aim and fire are automatic.
- Three jobs are always on the map: Fix Site, Get Reviews, New Page. Enter a beam to start one.
- Each finished job moves that client up the rankings. Rank 3 or better is the Map Pack.
- Map Pack clients pay leads every second. Fill all 3 spots.
- Finished jobs raise spam heat. Spam bots hunt you and steal leads. Howl clears them.

## Stack

- Three.js. No build step. Static files only.
- Realtime over WebSockets with Supabase Realtime (Broadcast and Presence).
- Each player runs their own shift. The network shares positions and lead counts for the live leaderboard.
- Email gate writes to the `leads` table. SQL is in `supabase/001_leads.sql`.
- Key art and the wolf model were generated with Higgsfield.

## Go live with multiplayer

1. Create a Supabase project. Run `supabase/001_leads.sql`.
2. Put the project URL and publishable key in `js/config.js`.
3. Deploy this folder to any static host.

With no Supabase config the game runs offline as a solo town.

## Run locally

```bash
python3 -m http.server 8000
```

## Rooms

- No `?room=` joins the public `town-square` room. It overflows at 8 players.
- `?room=abc12` is a private room. The Invite button builds this link.

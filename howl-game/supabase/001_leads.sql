-- Email gate storage for Map Pack Showdown.
-- Anonymous players can insert. Nobody can read with the public key.
create table if not exists public.leads (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  name text not null check (char_length(name) between 2 and 40),
  email text not null check (char_length(email) between 5 and 200 and email like '%_@_%._%'),
  room text check (char_length(room) <= 40)
);
alter table public.leads enable row level security;
create policy "anyone can sign up" on public.leads for insert to anon with check (true);

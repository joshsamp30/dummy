// Public client config. The Supabase publishable key is safe to ship in the browser.
// Leave SUPABASE_URL empty to run in local mode (solo with bots, or tabs on one device).
export const CONFIG = {
  SUPABASE_URL: '',
  SUPABASE_KEY: '',
  ROUND_SECONDS: 150,
  ROOM_CAP: 8,
  PACK_SIZE: 3, // each pack is filled to this size with bots
  CTA_URL: 'https://localhowl.com', // link shown on the results screen
};

export const TEAMS = [
  { name: 'Night Pack', color: 0x4d6bff, css: '#4d6bff' },
  { name: 'Dawn Pack', color: 0xff5fa8, css: '#ff5fa8' },
];

export const STORES = [
  { name: "Howlin' Plumbing", cat: 'Plumber', x: -30, z: -31 },
  { name: 'Fang Family Dental', cat: 'Dentist', x: -10, z: -31 },
  { name: 'Pack Pizza', cat: 'Pizza', x: 10, z: -31 },
  { name: 'Den Roofing', cat: 'Roofer', x: 30, z: -31 },
  { name: 'Full Moon Coffee', cat: 'Coffee shop', x: -30, z: 31 },
  { name: 'Alpha HVAC', cat: 'HVAC', x: -10, z: 31 },
  { name: 'Paws Auto Repair', cat: 'Auto repair', x: 10, z: 31 },
  { name: 'Lone Wolf Law', cat: 'Law firm', x: 30, z: 31 },
];

export const PADS = [
  { x: 0, z: -13 }, { x: 0, z: 13 }, { x: -22, z: 0 }, { x: 22, z: 0 },
];

// Pickups are new website pages. Publishing one pays leads and gives a boost.
export const PAGE_LEADS = 8;
export const PICKUPS = {
  1: { key: 'photos', label: 'Service Page', color: 0xfff078, buff: 'Double review power',
       fact: 'Service page published. One page per service gives Google a clear page to match to that search.' },
  2: { key: 'cats', label: 'FAQ Page', color: 0x6cd3a8, buff: 'Rapid fire',
       fact: 'FAQ page published. Answering real customer questions lets you match more of what people search.' },
  3: { key: 'reply', label: 'About Page', color: 0xffffff, buff: 'Full heal and shield',
       fact: 'About page published. Google says to make clear who is behind a site. It builds trust.' },
  4: { key: 'nap', label: 'Location Page', color: 0xc9a2ff, buff: 'Boost every listing you hold',
       fact: 'Location page published. A unique page per area served helps you show up in that area.' },
};

// Technical website issues. They break a storefront until someone fixes them.
export const ISSUES = [
  { label: '404 ERROR', fact: 'A 404 page cannot rank. It also sends a ready customer to a dead end.' },
  { label: 'SLOW PAGE', fact: 'Slow page. Google has used page speed as a ranking factor for mobile searches since 2018.' },
  { label: 'NOT MOBILE FRIENDLY', fact: 'Google indexes and ranks from the mobile version of a site. Broken on phones means broken in search.' },
  { label: 'NO HTTPS', fact: 'No HTTPS. Google has used HTTPS as a ranking signal since 2014. Browsers flag the rest as not secure.' },
  { label: 'MISSING TITLE TAG', fact: 'Missing title tag. Google uses the title element to write the headline people see in results.' },
  { label: 'BLOCKED FROM GOOGLE', fact: 'Blocked from crawling. If Google cannot crawl a page it cannot rank it.' },
];

export const FACTS = {
  capture: [
    'Reviews. Google says more reviews and positive ratings can improve local ranking.',
    'The Map Pack is the top 3 local results. Those three spots get most of the attention.',
    'Google says your position in web results is a factor in local ranking. Website work moves the map.',
    'Fresh reviews matter. A steady stream beats one big burst.',
  ],
  proximity: 'Distance. Closer to the searcher ranks better. Your reviews hit harder up close.',
  fixed: 'Fixed. Technical fixes let the pages and reviews you already earned do their job.',
  howl: 'Howl. Being loud everywhere builds prominence. Links, mentions and listings all count.',
};

export const BOT_NAMES = ['Luna', 'Fang', 'Lobo', 'Ghost', 'Timber', 'Echo', 'Sable', 'Koda'];

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
  { name: 'Night Pack', color: 0x3b7bff, css: '#3b7bff' },
  { name: 'Dawn Pack', color: 0xff5c7a, css: '#ff5c7a' },
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

// Pickups are real local ranking levers.
export const PICKUPS = {
  1: { key: 'photos', label: 'Photos', color: 0xffc83d, buff: 'Double review power',
       fact: 'Photos. Google says photos show people your goods and services and help your profile stand out.' },
  2: { key: 'cats', label: 'Categories', color: 0x6cd3a8, buff: 'Rapid fire',
       fact: 'Categories. Relevance is how well a profile matches the search. The right primary category drives it.' },
  3: { key: 'reply', label: 'Review Reply', color: 0xffffff, buff: 'Full heal and shield',
       fact: 'Review replies. Google says replying to reviews shows you value customers and their feedback.' },
  4: { key: 'nap', label: 'Citations', color: 0xc9a2ff, buff: 'Boost every listing you hold',
       fact: 'Citations. Prominence draws on what the web says about a business. Keep name, address and phone consistent.' },
};

export const FACTS = {
  capture: [
    'Reviews. Google says more reviews and positive ratings can improve local ranking.',
    'The Map Pack is the top 3 local results. Those three spots get most of the attention.',
    'Local ranking runs on three things: relevance, distance and prominence.',
    'Fresh reviews matter. A steady stream beats one big burst.',
  ],
  proximity: 'Distance. Closer to the searcher ranks better. Your reviews hit harder up close.',
  spam: 'Spam listing. Fake profiles steal real leads. Report them to Google with the Business Redressal form.',
  report: 'Reported. Removing a fake listing can move every real business up a spot.',
  howl: 'Howl. Being loud everywhere builds prominence. Links, mentions and listings all count.',
};

export const BOT_NAMES = ['Luna', 'Fang', 'Lobo', 'Ghost', 'Timber', 'Echo', 'Sable', 'Koda'];

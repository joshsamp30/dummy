// Public client config. The Supabase publishable key is safe to ship in the browser.
// Leave SUPABASE_URL empty to run offline.
export const CONFIG = {
  SUPABASE_URL: 'https://auadieirkythwgivldma.supabase.co',
  SUPABASE_KEY: 'sb_publishable_22S6AH4dXHinfLff8aBcvw_EIZFwL-e',
  SHIFT_SECONDS: 180,
  ROOM_CAP: 8,
  CTA_URL: 'https://localhowl.com', // link shown on the results screen
};

export const COLORS = { me: 0xfff078, other: 0x4d6bff, customer: 0xff5fa8 };

export const STORES = [
  { name: "Howlin' Plumbing", cat: 'Plumber' },
  { name: 'Fang Family Dental', cat: 'Dentist' },
  { name: 'Pack Pizza', cat: 'Pizza' },
  { name: 'Den Roofing', cat: 'Roofer' },
  { name: 'Full Moon Coffee', cat: 'Coffee shop' },
  { name: 'Alpha HVAC', cat: 'HVAC' },
  { name: 'Paws Auto Repair', cat: 'Auto repair' },
  { name: 'Lone Wolf Law', cat: 'Law firm' },
  { name: 'Howl Electric', cat: 'Electrician' },
];

// Technical website issues. In a Fix Site job these run loose around the client.
export const ISSUES = ['404 ERROR', 'SLOW PAGE', 'NO HTTPS', 'BROKEN LINK', 'NOT MOBILE FRIENDLY', 'MISSING TITLE TAG'];

// The three jobs. Each one is a real piece of local SEO work.
export const JOBS = {
  fix: {
    label: 'FIX SITE', color: 0xff5252, css: '#ff5252', seconds: 45, need: 5,
    brief: ['Our site is throwing errors. Customers keep bouncing.', 'The website is broken on phones. Help.', 'Google says our pages have issues. Fix them.'],
    goal: 'Squash the issues',
    facts: [
      'A 404 page cannot rank. It also sends a ready customer to a dead end.',
      'Google has used page speed as a ranking factor for mobile searches since 2018.',
      'Google indexes and ranks from the mobile version of a site. Broken on phones means broken in search.',
      'Google has used HTTPS as a ranking signal since 2014. Browsers flag the rest as not secure.',
      'If Google cannot crawl a page it cannot rank it. Technical fixes come first.',
    ],
  },
  reviews: {
    label: 'GET REVIEWS', color: 0xfff078, css: '#fff078', seconds: 60, need: 5,
    brief: ['We do great work but nobody reviews us.', 'The shop down the street has 200 reviews. We have 9.', 'Happy customers are out there. Go ask them.'],
    goal: 'Ask customers',
    facts: [
      'Google says more reviews and positive ratings can improve local ranking.',
      'Google lets you ask customers for reviews. Paying for them breaks its rules.',
      'Fresh reviews matter. A steady stream beats one big burst.',
      'Google says replying to reviews shows you value customers and their feedback.',
    ],
  },
  page: {
    label: 'NEW PAGE', color: 0x6cd3a8, css: '#6cd3a8', seconds: 55, need: 1,
    brief: ['We offer six services. Our site has one page.', 'We serve the next town over but we never show up there.', 'People ask the same questions all day. Put the answers online.'],
    goal: 'Pick up the page at HQ and publish it here',
    pages: ['Service Page', 'Location Page', 'FAQ Page'],
    facts: [
      'One page per service gives Google a clear page to match to that search.',
      'A unique page per area served helps you show up in that area.',
      'Answering real customer questions lets you match more of what people search.',
      'Google says your position in web results is a factor in local ranking. Website work moves the map.',
    ],
  },
};

export const FACTS = {
  pack: 'The Map Pack is the top 3 local results. Those three spots get most of the calls.',
  heat: 'Spam listings are fake profiles that steal real leads. You can report them to Google.',
};

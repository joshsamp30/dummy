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

// Technical website issues, each with the real fix. In a Fix Site job these run loose around the client.
export const ISSUES = [
  { label: '404 ERROR', fix: 'Redirected the dead URL to a live page (a 301 redirect).' },
  { label: 'SLOW PAGE', fix: 'Compressed the oversized images so the page loads fast.' },
  { label: 'NO HTTPS', fix: 'Installed an SSL certificate and moved the site to https.' },
  { label: 'BROKEN LINK', fix: 'Pointed the link at a page that exists.' },
  { label: 'NOT MOBILE FRIENDLY', fix: 'Switched to a layout that fits a phone screen.' },
  { label: 'MISSING TITLE TAG', fix: 'Wrote a unique title: service, city, brand.' },
];

// How a business actually earns a review. One is shown each time you reach a customer.
export const ASKS = [
  'Asked in person right after the job.',
  'Texted a direct link to the review form.',
  'Followed up by email the next day.',
  'Put a review QR code on the invoice.',
  'Asked every customer, not only the happy ones.',
];

export const BONUS = 60; // leads for a correct call

// The three jobs. Each scenario is a real client problem with one decision and the reason behind it.
export const JOBS = {
  fix: {
    label: 'FIX SITE', color: 0xff5252, css: '#ff5252', seconds: 45, need: 5, goal: 'Squash the issues',
    did: 'Technical fixes shipped:',
    scenarios: [
      { quote: 'We deleted an old page. People still land on it from Google.',
        q: 'An old page was deleted but still gets clicks from Google. Best fix?',
        opts: ['Leave the 404 alone', '301 redirect it to the closest live page', 'Delete the rest of that section'], a: 1,
        why: 'A 301 redirect sends visitors and Google to the replacement page. A 404 is a dead end and cannot rank.' },
      { quote: 'Chrome says our contact page is "Not secure".',
        q: 'Chrome shows "Not secure" on the contact form. What is missing?', opts: ['More photos', 'HTTPS', 'A longer page title'], a: 1,
        why: 'The site needs HTTPS. Google has used it as a ranking signal since 2014 and browsers warn visitors without it.' },
      { quote: 'The site looks fine on my laptop. Customers say it is a mess on phones.',
        q: 'Which version of a site does Google mainly use to index and rank it?', opts: ['The desktop version', 'The mobile version', 'Whichever is longer'], a: 1,
        why: 'Google uses mobile-first indexing. If the phone version is broken, that is the version being ranked.' },
      { quote: 'Our home page takes forever to load.',
        q: 'A page takes 9 seconds to load on a phone. What is the usual first fix?', opts: ['Compress the huge images', 'Add a background video', 'Add more pages'], a: 0,
        why: 'Oversized images are a common cause of slow pages. Google has used page speed as a mobile ranking factor since 2018.' },
      { quote: 'Every page on our site shows up in Google as "Home".',
        q: 'What does a page title tag do?', opts: ['Makes the page load faster', 'Gives Google the headline it shows in results', 'Adds star ratings'], a: 1,
        why: 'Google uses the title element to write the clickable headline in search results. Each page needs its own.' },
    ],
  },
  reviews: {
    label: 'GET REVIEWS', color: 0xfff078, css: '#fff078', seconds: 60, need: 5, goal: 'Ask customers',
    did: 'How the reviews were earned:',
    scenarios: [
      { quote: 'Can we just give people $10 off for a 5-star review?',
        q: 'Can a business offer a discount in exchange for a Google review?', opts: ['Yes, any time', 'No. It breaks Google rules', 'Only for 5-star reviews'], a: 1,
        why: 'Google bans incentives for reviews. Asking is allowed. Paying, in cash or discounts, is not.' },
      { quote: 'Someone left us 2 stars. I want to ignore it.',
        q: 'A customer leaves a 2-star review. Best move?', opts: ['Ignore it', 'Reply politely and offer to make it right', 'Bury it with fake reviews'], a: 1,
        why: 'Google says replying shows you value customers and their feedback. Fake reviews break its rules.' },
      { quote: 'Let us only send the review link to customers we know are happy.',
        q: 'Should a business ask only happy customers and skip the rest?', opts: ['Yes, that is smart', 'No. That is review gating and Google prohibits it'], a: 1,
        why: 'Google says not to selectively solicit positive reviews. Ask everyone the same way.' },
      { quote: 'Customers say they would review us but never get around to it.',
        q: 'What makes leaving a review easiest for a customer?', opts: ['A direct link or QR code to the review form', 'Telling them to search for you', 'A letter in the mail'], a: 0,
        why: 'A Google Business Profile has a shareable review link. Fewer steps means more reviews.' },
      { quote: 'Do reviews even matter for where we rank?',
        q: 'According to Google, which of these can improve local ranking?', opts: ['Hiding the business address', 'More reviews and positive ratings', 'Fewer photos'], a: 1,
        why: 'Google states that more reviews and positive ratings can improve a business\'s local ranking.' },
    ],
  },
  page: {
    label: 'NEW PAGE', color: 0x6cd3a8, css: '#6cd3a8', seconds: 60, need: 1, goal: '',
    did: 'Published:',
    scenarios: [
      { quote: 'We offer six different services. Our site has one page called Services.',
        q: 'One page lists every service. Which page do you build?', opts: ['Service Page', 'Location Page', 'FAQ Page'], a: 0,
        why: 'One page per service gives Google a clear page to match to each search. One catch-all page competes for none of them well.' },
      { quote: 'We serve Kirkwood and Webster Groves. We only show up in one of them.',
        q: 'They serve two towns but rank in one. Which page do you build?', opts: ['FAQ Page', 'About Page', 'Location Page'], a: 2,
        why: 'A unique page for each area served, with real local detail, helps you show up there. Copy-paste city pages do not.' },
      { quote: 'People call all day asking "Do you offer financing?" and "Are you open Saturdays?"',
        q: 'Customers keep asking the same questions. Which page do you build?', opts: ['Location Page', 'FAQ Page', 'Service Page'], a: 1,
        why: 'Answering real customer questions on the site lets you match more of what people actually search.' },
      { quote: 'Nobody can tell who we are or whether we are licensed.',
        q: 'Visitors cannot tell who runs the business. Which page do you build?', opts: ['About Page', 'Service Page', 'Location Page'], a: 0,
        why: 'Google advises making it clear who is behind a site. An About page with licences and people builds trust.' },
    ],
  },
};

export const FACTS = {
  pack: 'The Map Pack is the top 3 local results. Those three spots get most of the calls.',
  heat: 'Spam listings are fake profiles that steal real leads. You can report them to Google.',
  web: 'Google says your position in web results is a factor in local ranking. Website work moves the map.',
};

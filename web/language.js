'use strict';
// One preference across the operator app, public scorecards and bin guide.
// A shared link may specify a language even on a phone with no saved preference.
window.LaneLanguage = {
  get() {
    const requested = new URLSearchParams(location.search).get('lang');
    if (['en', 'hi'].includes(requested)) return requested;
    try {
      const saved = localStorage.getItem('lane-lang') || localStorage.getItem('lane-guide-lang');
      return saved === 'hi' ? 'hi' : 'en';
    } catch (_) { return 'en'; }
  },
  set(lang) {
    const selected = lang === 'hi' ? 'hi' : 'en';
    try { localStorage.setItem('lane-lang', selected); localStorage.setItem('lane-guide-lang', selected); } catch (_) { /* optional */ }
    document.documentElement.lang = selected;
    const url = new URL(location.href);
    url.searchParams.set('lang', selected);
    history.replaceState(null, '', url);
  },
  url(path, lang) {
    const url = new URL(path, location.origin);
    url.searchParams.set('lang', lang === 'hi' ? 'hi' : 'en');
    return url.href;
  },
};

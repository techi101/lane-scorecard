// Collection-staff page: tap a floor, tap how each bin looks, optionally flag danger, send.
// Every tap is spoken in Hindi so the page works without reading.
const token = location.pathname.split('/')[2] || '';
const app = document.getElementById('app');
const s = {floors: [], demo: false, floor: null, bio: null, nonbio: null, hazard: false, deep: false, issues: [], sending: false, error: ''};
const esc = v => String(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

const RATES = [
  {value: 'clean', face: '😊', hi: 'साफ़', en: 'Clean', c: 'var(--green)'},
  {value: 'few', face: '😐', hi: 'थोड़ा मिला', en: 'A few wrong', c: 'var(--amber)'},
  {value: 'mixed', face: '😟', hi: 'पूरा मिला हुआ', en: 'Mixed', c: 'var(--red)'},
];
const BINS = {
  bio: {hi: 'हरा डिब्बा — गीला कचरा', en: 'Green bin · wet / food waste', color: '#2f7d32', say: 'हरा डिब्बा'},
  nonbio: {hi: 'नीला डिब्बा — सूखा कचरा', en: 'Blue bin · dry waste', color: '#1f5fa8', say: 'नीला डिब्बा'},
};
const ISSUES = [
  {key: 'plastic_in_wet', pic: '🛍️', hi: 'हरे डिब्बे में प्लास्टिक', en: 'Plastic in green bin'},
  {key: 'food_in_dry', pic: '🍛', hi: 'नीले डिब्बे में खाना', en: 'Food in blue bin'},
  {key: 'one_bag', pic: '👜', hi: 'सब एक ही थैली में', en: 'All in one bag'},
  {key: 'hidden_below', pic: '🔍', hi: 'नीचे छिपा ग़लत कचरा', en: 'Wrong items hidden underneath'},
];
const HELP = 'पहले जगह चुनें। फिर हरे और नीले डिब्बे को देखकर चेहरा दबाएँ। कुछ ग़लत दिखे तो उसकी तस्वीर दबाएँ। काँच, ब्लेड, सुई या खुला पैड मिले तो लाल बटन दबाएँ। आख़िर में हरा बटन, भेजें, दबाएँ।';

function speak(text) {
  try {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'hi-IN';
    const voice = speechSynthesis.getVoices().find(v => v.lang && v.lang.toLowerCase().startsWith('hi'));
    if (voice) u.voice = voice;
    u.rate = 0.9;
    speechSynthesis.speak(u);
  } catch (_) { /* Voice is a help, never a requirement. */ }
}

function binIcon(color) {
  return `<svg width="54" height="62" viewBox="0 0 54 62" aria-hidden="true"><rect x="6" y="12" width="42" height="48" rx="6" fill="${color}"/><rect x="2" y="5" width="50" height="9" rx="3" fill="${color}"/><rect x="20" y="0" width="14" height="7" rx="2" fill="${color}"/><path d="M18 24v26M27 24v26M36 24v26" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".7"/></svg>`;
}

function rateBlock(stream, n) {
  const bin = BINS[stream];
  return `<div class="step"><b>${n}</b>${bin.hi}</div>
    <div class="bin" style="--c:${bin.color}">${binIcon(bin.color)}<div><strong>${bin.hi}</strong><small>${bin.en}</small></div></div>
    <div class="rate">${RATES.map(r => `<button style="--c:${r.c}" data-rate="${stream}" data-value="${r.value}" aria-pressed="${s[stream] === r.value}" aria-label="${bin.say}: ${r.hi}"><span class="face">${r.face}</span>${r.hi}<span class="en">${r.en}</span></button>`).join('')}</div>`;
}

function render() {
  if (!s.floors.length) {
    app.innerHTML = `<div class="done"><div class="big">🏢</div><p>अभी कोई जगह नहीं जोड़ी गई।<span class="en">No places yet. Ask the warden to add them.</span></p></div>`;
    return;
  }
  const ready = s.floor && s.bio && s.nonbio && !s.sending;
  app.innerHTML = `<div class="top"><h1>कूड़ेदान रिपोर्ट <span class="en">Bin report</span></h1>${s.demo ? '<span class="demo">DEMO</span>' : ''}<button class="speak" data-action="help" aria-label="सुनें / Listen">🔊</button></div>
    <div class="step"><b>1</b>जगह चुनें <span class="en">Choose the place</span></div>
    <div class="grid">${s.floors.map(f => `<button class="tile" data-floor="${esc(f.id)}" aria-pressed="${s.floor === f.id}">${esc(f.name)}</button>`).join('')}</div>
    ${rateBlock('bio', 2)}${rateBlock('nonbio', 3)}
    <div class="step"><b>4</b>क्या ग़लत था? <span class="en">What was wrong? (optional)</span></div>
    <div class="rate">${ISSUES.map(i => `<button style="--c:var(--amber)" data-issue="${i.key}" aria-pressed="${s.issues.includes(i.key)}" aria-label="${i.hi}"><span class="face">${i.pic}</span>${i.hi}<span class="en">${i.en}</span></button>`).join('')}</div>
    <button class="hazard deep" data-action="deep" aria-pressed="${s.deep}"><span class="face">🔍</span>मैंने नीचे तक देखा<span class="en">I looked below the top layer</span></button>
    <div class="step"><b>5</b>खतरनाक चीज़? <span class="en">Anything dangerous?</span></div>
    <button class="hazard" data-action="hazard" aria-pressed="${s.hazard}"><span class="face">⚠️ 🍾 🔪 💉</span>काँच, ब्लेड, सुई या खुला पैड मिला<span class="en">Glass, blade, needle or unwrapped sanitary waste</span></button>
    ${s.error ? `<div class="error" role="alert">${esc(s.error)}</div>` : ''}
    <button class="send" data-action="send" ${ready ? '' : 'disabled'}>✓ भेजें <span class="en" style="color:inherit">Send</span></button>`;
}

async function send() {
  s.sending = true; s.error = ''; render();
  try {
    const r = await fetch(`/api/worker/${encodeURIComponent(token)}/reports`, {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Lane-Request': '1'},
      body: JSON.stringify({floor_id: s.floor, bio: s.bio, nonbio: s.nonbio, hazard: s.hazard, deep: s.deep, issues: s.issues}),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Not sent');
    const name = s.floors.find(f => f.id === s.floor)?.name || '';
    app.innerHTML = `<div class="done"><div class="big">✅</div><p>भेज दिया। धन्यवाद!<span class="en">Sent. Thank you!</span></p><p style="font-size:20px">${esc(name)}</p></div>`;
    speak('भेज दिया। धन्यवाद।');
    Object.assign(s, {floor: null, bio: null, nonbio: null, hazard: false, deep: false, issues: [], sending: false});
    setTimeout(render, 2500);
  } catch (e) {
    s.sending = false;
    s.error = 'नहीं भेजा गया। फिर से दबाएँ। · Not sent. Tap send again.';
    speak('नहीं भेजा गया। फिर से दबाएँ।');
    render();
  }
}

app.addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b || b.disabled) return;
  if (b.dataset.floor) { s.floor = b.dataset.floor; speak(b.textContent); }
  else if (b.dataset.rate) {
    const r = RATES.find(x => x.value === b.dataset.value);
    s[b.dataset.rate] = r.value; speak(`${BINS[b.dataset.rate].say}: ${r.hi}`);
  } else if (b.dataset.issue) {
    const i = ISSUES.find(x => x.key === b.dataset.issue), on = !s.issues.includes(i.key);
    s.issues = on ? [...s.issues, i.key] : s.issues.filter(k => k !== i.key);
    speak(on ? i.hi : `${i.hi} हटाया`);
  } else if (b.dataset.action === 'hazard') { s.hazard = !s.hazard; speak(s.hazard ? 'खतरनाक चीज़ दर्ज की' : 'खतरनाक चीज़ हटाई'); }
  else if (b.dataset.action === 'deep') { s.deep = !s.deep; speak(s.deep ? 'नीचे तक देखा' : 'नीचे तक देखना हटाया'); }
  else if (b.dataset.action === 'help') { speak(HELP); return; }
  else if (b.dataset.action === 'send') { send(); return; }
  s.error = ''; render();
});

(async () => {
  try {
    const r = await fetch(`/api/worker/${encodeURIComponent(token)}`);
    if (!r.ok) throw new Error();
    const d = await r.json();
    s.floors = d.floors; s.demo = d.demo;
    render();
  } catch (_) {
    app.innerHTML = `<div class="done"><div class="big">🔗</div><p>यह लिंक काम नहीं कर रहा। वार्डन से नया लिंक माँगें।<span class="en">This link is not working. Ask the warden for a new link.</span></p></div>`;
  }
})();

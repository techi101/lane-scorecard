'use strict';
// My Bin Guide: paste or photograph a receipt, get "which bin does each part go in".
// Nothing is saved. The receipt is for the household; the collector never sees it.
const app = document.getElementById('app');
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
let lang = LaneLanguage.get();
const s = {text: '', image: '', fileName: '', busy: false, error: '', result: null};
const t = (en, hi) => lang === 'hi' ? hi : en;
const ORDER = ['wet', 'dry', 'sanitary', 'special', 'ewaste'];
const COLOR = {wet: 'var(--wet)', dry: 'var(--dry)', sanitary: 'var(--sanitary)', special: 'var(--special)', ewaste: 'var(--ewaste)'};
const SAMPLE = 'Amul Taaza Toned Milk 500 ml   2 x 27.00\nBanana Robusta 1 kg   60.00\nLays Classic Salted 52g   20.00\nWhisper Ultra Clean 8 pads   99.00\nDuracell AA Battery 2pcs   120.00\nItem Total   353.00\nGST 5%';
const SAMPLE_HI = 'दूध ५०० मिलीलीटर\nकेले १ किलो\nचिप्स १ पैकेट\nसैनिटरी पैड\nबैटरी २ पीस\nकुल ३५३';

function aiNote(ai) {
  if (ai === 'disabled') return t('Photo reading is switched off on this server, so the photo was not read. Paste the receipt text or type items one per line.', 'इस सर्वर पर फ़ोटो पढ़ना बंद है, इसलिए फ़ोटो नहीं पढ़ी गई। रसीद का टेक्स्ट चिपकाएँ या हर लाइन में एक सामान लिखें।');
  if (ai === 'unavailable') return t('The photo could not be read just now. Paste the receipt text instead.', 'अभी फ़ोटो नहीं पढ़ी जा सकी। इसकी जगह रसीद का टेक्स्ट चिपकाएँ।');
  return '';
}

function results(r) {
  const label = k => r.streams[k][lang] || r.streams[k].en;
  const counts = ORDER.filter(k => r.counts[k]).map(k => `<div class="count" style="background:${COLOR[k]}"><strong>${r.counts[k]}</strong>${esc(label(k))}</div>`).join('');
  const sections = ORDER.map(k => {
    const rows = [];
    for (const item of r.items) for (const p of item.parts) if (p.stream === k) {
      const tip = p.tip && (p.tip[lang] || p.tip.en);
      rows.push(`<li><strong>${esc(item.name)}</strong>: ${esc(p.part[lang] || p.part.en)}${tip ? `. <span class="muted">${esc(tip)}</span>` : ''}${item.source === 'ai' ? `<span class="tag">${t('AI suggestion · check the pack', 'AI सुझाव · पैक पर देखें')}</span>` : ''}</li>`);
    }
    return rows.length ? `<section class="panel stream" style="--c:${COLOR[k]}"><h2>${esc(label(k))}</h2><ul>${rows.join('')}</ul></section>` : '';
  }).join('');
  const unknown = r.items.filter(i => i.source === 'unknown');
  return `${aiNote(r.ai) ? `<div class="note">${esc(aiNote(r.ai))}</div>` : ''}
    ${r.items.length ? `<section class="panel"><h2>${t(`${r.items.length} items on this receipt`, `इस रसीद पर ${r.items.length} सामान`)}</h2><div class="counts">${counts}</div></section>` : `<div class="note">${t('No items found. Paste one item per line.', 'कोई सामान नहीं मिला। हर लाइन में एक सामान लिखें।')}</div>`}
    ${sections}
    ${unknown.length ? `<section class="panel"><h2>${t('Not in our list yet', 'अभी हमारी सूची में नहीं')}</h2><p class="muted">${t('Check the pack, or ask your waste collector.', 'पैक पर देखें या कचरा लेने वाले से पूछें।')}</p><ul>${unknown.map(i => `<li>${esc(i.name)}</li>`).join('')}</ul></section>` : ''}
    <p class="muted small">${t('Bins follow the four streams in the Solid Waste Management Rules, 2026. Reviewed rules decide; AI suggestions are labelled. A receipt shows what you bought, not what you threw: it is a guide for you, never a check on you.', 'डिब्बे ठोस अपशिष्ट प्रबंधन नियम 2026 की चार धाराओं के अनुसार हैं। फ़ैसला जाँचे गए नियमों से होता है; AI सुझाव अलग से चिह्नित हैं। रसीद बताती है कि आपने क्या ख़रीदा, यह नहीं कि क्या फेंका: यह आपके लिए गाइड है, आपकी जाँच नहीं।')}</p>`;
}

function render() {
  app.innerHTML = `<div class="top"><div><p class="muted">Lane Scorecard</p><h1>${t('My Bin Guide', 'कचरा किस डिब्बे में डालें?')}</h1></div><button class="lang" data-action="lang">${lang === 'en' ? 'हिन्दी' : 'English'}</button></div>
    <p>${t('Paste a receipt or order (Zepto, Blinkit, Zomato, a shop bill) and see which bin each part goes in.', 'कोई रसीद या ऑर्डर (Zepto, Blinkit, Zomato, दुकान का बिल) चिपकाएँ और देखें कि हर हिस्सा किस डिब्बे में जाएगा।')}</p>
    <p class="muted">${t('Private: nothing is saved, and your collector never sees your receipt.', 'निजी: कुछ भी सहेजा नहीं जाता, और कचरा लेने वाला आपकी रसीद कभी नहीं देखता।')}</p>
    <form class="panel" id="guide-form">
      <label for="receipt"><strong>${t('Receipt text', 'रसीद का टेक्स्ट')}</strong> <span class="muted">${t('or type one item per line', 'या हर लाइन में एक सामान लिखें')}</span></label>
      <textarea id="receipt" name="text" maxlength="6000" placeholder="${esc(t(SAMPLE, SAMPLE_HI))}">${esc(s.text)}</textarea>
      <label class="file">${t('Or add a receipt photo', 'या रसीद की फ़ोटो जोड़ें')} <span class="muted">${s.fileName ? esc(s.fileName) : t('(read by AI when switched on)', '(AI चालू होने पर पढ़ी जाती है)')}</span><input type="file" accept="image/jpeg,image/png,image/webp" id="photo"></label>
      ${s.error ? `<div class="error" role="alert">${esc(s.error)}</div>` : ''}
      <button class="btn" type="submit" ${s.busy ? 'disabled' : ''}>${s.busy ? t('Reading…', 'पढ़ रहे हैं…') : t('Show my bins', 'मेरे डिब्बे दिखाएँ')}</button>
      <button class="btn light" type="button" data-action="sample">${t('Try a sample receipt', 'नमूना रसीद आज़माएँ')}</button>
    </form>
    <div id="results">${s.result ? results(s.result) : ''}</div>`;
}

function shrink(file) {
  // Resize in the browser so phone photos stay under the server's 2 MB limit.
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file), img = new Image();
    img.onload = () => {
      const scale = Math.min(1, 1600 / Math.max(img.width, img.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(img.width * scale); canvas.height = Math.round(img.height * scale);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL('image/jpeg', 0.85).split(',')[1]);
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error(t('That file could not be read as a photo.', 'यह फ़ाइल फ़ोटो की तरह नहीं पढ़ी जा सकी।'))); };
    img.src = url;
  });
}

async function submit(e) {
  e.preventDefault();
  s.text = document.getElementById('receipt').value;
  if (!s.text.trim() && !s.image) { s.error = t('Paste the receipt text or add a photo first.', 'पहले रसीद का टेक्स्ट चिपकाएँ या फ़ोटो जोड़ें।'); render(); return; }
  s.busy = true; s.error = ''; render();
  try {
    const r = await fetch('/api/guide', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Lane-Request': '1'}, body: JSON.stringify({text: s.text, image: s.image})});
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(lang === 'hi' ? (r.status === 429 ? 'बहुत बार कोशिश की गई। थोड़ी देर बाद फिर कोशिश करें।' : 'रसीद पढ़ी नहीं जा सकी। टेक्स्ट या फ़ोटो जाँचकर फिर कोशिश करें।') : (typeof data.detail === 'string' ? data.detail : 'Could not read that. Try again.'));
    s.result = data;
  } catch (err) { s.error = err instanceof TypeError ? t('Could not connect. Check your connection and try again.', 'सर्वर से संपर्क नहीं हुआ। इंटरनेट जाँचकर फिर कोशिश करें।') : err.message; }
  s.busy = false; render();
  if (s.result) document.getElementById('results').scrollIntoView({behavior: 'smooth'});
}

app.addEventListener('submit', submit);
app.addEventListener('change', async e => {
  if (e.target.id !== 'photo' || !e.target.files[0]) return;
  s.text = document.getElementById('receipt').value;
  try { s.image = await shrink(e.target.files[0]); s.fileName = e.target.files[0].name; s.error = ''; }
  catch (err) { s.image = ''; s.fileName = ''; s.error = err.message; }
  render();
});
app.addEventListener('click', e => {
  const b = e.target.closest('button[data-action]');
  if (!b) return;
  if (b.dataset.action === 'lang') {
    s.text = document.getElementById('receipt').value;
    lang = lang === 'en' ? 'hi' : 'en';
    LaneLanguage.set(lang);
    s.error = '';
    render();
  } else if (b.dataset.action === 'sample') { s.text = t(SAMPLE, SAMPLE_HI); s.image = ''; s.fileName = ''; s.error = ''; s.result = null; render(); }
});
document.documentElement.lang = lang;
render();

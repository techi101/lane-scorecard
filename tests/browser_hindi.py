"""Hindi workflow and speech lifecycle checks, using an isolated local server."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from uuid import uuid4

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / '.local' / ('hindi-browser-' + uuid4().hex)
DATA.mkdir(parents=True)
ARTIFACTS = ROOT / 'artifacts'
ARTIFACTS.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:8768'
CODE = 'isolated-hindi-browser-test-code'
env = {**os.environ, 'LANE_DATA_DIR': str(DATA), 'LANE_PORT': '8768', 'LANE_ADMIN_CODE': CODE, 'LANE_ENABLE_AI': '0'}
for key in ['LANE_TABLE', 'LANE_PHOTO_BUCKET', 'LANE_SECURE_COOKIE', 'LANE_ORIGIN', 'AWS_LAMBDA_FUNCTION_NAME']:
    env.pop(key, None)
process = subprocess.Popen([sys.executable, 'run.py'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=None,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
errors = []
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + '/api/health', timeout=1)
            break
        except Exception:
            if process.poll() is not None:
                raise RuntimeError('Hindi test server exited')
            time.sleep(.3)
    else:
        raise RuntimeError('Hindi test server did not start')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge' if os.name == 'nt' else None)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.goto(BASE + '/?lang=hi')
        expect(page.get_by_role('heading', name='साइन इन करें')).to_be_visible()
        page.locator('[name=code]').fill(CODE)
        page.locator('#login-form button[type=submit]').click()
        expect(page.get_by_role('heading', name='अवलोकन', exact=True)).to_be_visible()
        expect(page.locator('.stats')).to_contain_text('परिसर का स्कोर')
        expect(page.locator('.notice')).to_contain_text('काल्पनिक')
        page.screenshot(path=str(ARTIFACTS / 'hindi-dashboard.png'), full_page=True)
        # Capture untranslated visible copy for review without private pilot data.
        audit = {}
        for view in ['dashboard', 'check', 'plan', 'cards', 'history', 'photos', 'setup', 'guide']:
            page.locator(f'.sidebar [data-nav={view}]').click()
            page.wait_for_function('(view) => document.querySelector(`[data-nav="${view}"]`).classList.contains("active")', arg=view)
            audit[view] = page.locator('#main').inner_text()
        (ARTIFACTS / 'hindi-screen-copy.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
        page.set_viewport_size({'width': 390, 'height': 844})
        for view in ['dashboard', 'check', 'plan']:
            page.locator('[data-action=menu]').click()
            page.locator(f'.sidebar [data-nav={view}]').click()
            page.wait_for_function('(view) => document.querySelector(`[data-nav="${view}"]`).classList.contains("active")', arg=view)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), view
            page.screenshot(path=str(ARTIFACTS / f'hindi-{view}-mobile.png'), full_page=True)
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('#workspace').select_option('pilot')
        page.locator('.sidebar [data-nav=setup]').click()
        page.locator('#floor-form [name=name]').fill('पुस्तकालय प्रवेश')
        page.locator('#floor-form [name=permission]').check()
        page.locator('[data-action=language]').click()
        expect(page.locator('#floor-form [name=name]')).to_have_value('पुस्तकालय प्रवेश')
        expect(page.locator('#floor-form [name=permission]')).to_be_checked()
        page.locator('[data-action=language]').click()
        page.locator('#floor-form button[type=submit]').click()
        expect(page.locator('.data-list').first).to_contain_text('पुस्तकालय प्रवेश')
        page.locator('.sidebar [data-nav=check]').click()
        page.locator('[name=bio][value=mixed]').check()
        page.locator('[name=nonbio][value=clean]').check()
        page.locator('[name=issues][value=plastic_in_wet]').check()
        page.locator('[name=note]').fill('हिंदी निरीक्षण')
        page.locator('[data-action=language]').click()
        expect(page.locator('[name=bio][value=mixed]')).to_be_checked()
        expect(page.locator('[name=note]')).to_have_value('हिंदी निरीक्षण')
        page.locator('[data-action=language]').click()
        page.locator('[name=human_confirmed]').check()
        page.locator('#check-form button[type=submit]').click()
        expect(page.get_by_role('heading', name='अवलोकन', exact=True)).to_be_visible()
        page.locator('.sidebar [data-nav=plan]').click()
        expect(page.locator('.plan-card').first).to_contain_text('डिब्बों में कचरा सही तरह अलग करें')
        expect(page.locator('.plan-card').first).to_contain_text('प्लास्टिक')
        assert 'lang=hi' in page.locator('a[download]').get_attribute('href')
        page.locator('.sidebar [data-nav=cards]').click()
        page.locator('[data-card]').first.click()
        expect(page.locator('#modal')).to_be_visible()
        url = page.locator('#modal a').get_attribute('href')
        assert 'lang=hi' in url
        public = browser.new_context(viewport={'width': 390, 'height': 844})
        card = public.new_page()
        card.on('pageerror', lambda err: errors.append(str(err)))
        card.goto(url)
        expect(card.locator('html')).to_have_attribute('lang', 'hi')
        expect(card.locator('.public-card')).to_contain_text('वास्तविक पायलट निरीक्षण')
        expect(card.locator('.public-footer')).to_contain_text('शुरुआती पायलट')
        card.screenshot(path=str(ARTIFACTS / 'hindi-card-mobile.png'), full_page=True)
        assert card.evaluate('document.documentElement.scrollWidth <= innerWidth')
        card.locator('a[href*="/guide"]').click()
        expect(card.get_by_role('heading', name='कचरा किस डिब्बे में डालें?')).to_be_visible()
        card.locator('[data-action=sample]').click()
        expect(card.locator('#receipt')).to_contain_text('दूध')
        card.locator('#guide-form [type=submit]').click()
        expect(card.locator('#results')).to_contain_text('इस रसीद पर 5 सामान')
        expect(card.locator('#results')).to_contain_text('दूध की थैली')
        assert 'अभी हमारी सूची में नहीं' not in card.locator('#results').inner_text()
        card.screenshot(path=str(ARTIFACTS / 'hindi-guide-mobile.png'), full_page=True)
        assert card.evaluate('document.documentElement.scrollWidth <= innerWidth')
        card.locator('[data-action=lang]').click()
        expect(card.locator('#results')).to_contain_text('Milk pouch')
        card.reload()
        expect(card.locator('html')).to_have_attribute('lang', 'en')
        page.locator('#modal button').click()
        page.locator('.sidebar [data-nav=setup]').click()
        page.locator('[data-action=worker-create]').click()
        expect(page.locator('[data-action=worker-copy]')).to_be_visible()
        token = context.request.get(BASE + '/api/pilot/worker-link').json()['token']
        worker = public.new_page()
        worker.on('pageerror', lambda err: errors.append(str(err)))
        worker.add_init_script('''
          window.voiceList = [];
          window.spoken = [];
          window.speechEvent = null;
          Object.defineProperty(window, 'speechSynthesis', {value: {
            getVoices: () => voiceList, cancel: () => {},
            addEventListener: (name, fn) => { window.speechEvent = fn; },
            speak: u => { window.lastUtterance=u; spoken.push({text:u.text, lang:u.lang, voice:u.voice.lang}); u.onstart?.(); }
          }});
          window.SpeechSynthesisUtterance = class { constructor(text) {this.text=text;} };
        ''')
        worker.goto(BASE + '/w/' + token)
        worker.locator('[data-action=help]').click()
        expect(worker.locator('#voice-status')).to_contain_text('तैयार')
        worker.evaluate("voiceList=[{lang:'hi-IN'}]; speechEvent()")
        assert worker.evaluate('spoken[0].voice') == 'hi-IN'
        expect(worker.locator('#voice-status')).to_be_hidden()
        worker.locator('[data-floor]').first.click()
        worker.locator('[data-rate=bio][data-value=clean]').click()
        worker.locator('[data-rate=nonbio][data-value=mixed]').click()
        worker.evaluate("lastUtterance.onerror({error:'synthesis-failed'})")
        expect(worker.locator('#voice-status')).to_contain_text('आवाज़ नहीं चल पाई')
        worker.evaluate('voiceList=[]')
        worker.locator('[data-action=help]').click()
        expect(worker.locator('#voice-status')).to_contain_text('हिंदी आवाज़ उपलब्ध नहीं', timeout=4000)
        expect(worker.locator('[data-action=send]')).to_be_enabled()
        worker.screenshot(path=str(ARTIFACTS / 'hindi-worker-mobile.png'), full_page=True)
        assert worker.evaluate('document.documentElement.scrollWidth <= innerWidth')
        worker.locator('[data-action=send]').click()
        expect(worker.locator('.done')).to_contain_text('भेज दिया')
        assert any(c['round'] == 'collection' for c in context.request.get(BASE + '/api/pilot/dashboard').json()['recent'])
        assert not errors, errors
        browser.close()
    print(json.dumps({'result': 'PASS', 'checks': ['Hindi login and screens', 'form draft preservation', 'Hindi plan', 'shared card language', 'Hindi receipt classification', 'mobile layouts', 'delayed speech voices', 'speech errors', 'missing Hindi voice fallback', 'staff report saved'], 'browser_errors': errors}))
finally:
    process.terminate()
    process.wait(timeout=10)

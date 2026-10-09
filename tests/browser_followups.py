"""Real browser check of collection actions, using isolated simulated data."""
from datetime import date, timedelta
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
DATA = ROOT / '.local' / ('followups-browser-' + uuid4().hex)
DATA.mkdir(parents=True)
ARTIFACTS = ROOT / 'artifacts'
ARTIFACTS.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:8767'
CODE = 'isolated-followups-browser-test'
env = {**os.environ, 'LANE_DATA_DIR': str(DATA), 'LANE_PORT': '8767', 'LANE_ADMIN_CODE': CODE, 'LANE_ENABLE_AI': '0'}
for key in ['LANE_TABLE', 'LANE_PHOTO_BUCKET', 'LANE_SECURE_COOKIE', 'LANE_ORIGIN', 'AWS_LAMBDA_FUNCTION_NAME']:
    env.pop(key, None)
process = subprocess.Popen([sys.executable, 'run.py'], cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
errors = []
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + '/api/health', timeout=1)
            break
        except Exception:
            if process.poll() is not None:
                raise RuntimeError('Test server exited')
            time.sleep(.3)
    else:
        raise RuntimeError('Test server did not start')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge' if os.name == 'nt' else None)
        context = browser.new_context(viewport={'width': 1440, 'height': 1050})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE)
        page.locator('input[name=code]').fill(CODE)
        page.get_by_role('button', name='Sign in').click()
        expect(page.locator('#workspace')).to_be_visible()
        headers = {'X-Lane-Request': '1'}
        request = context.request
        today = date.fromisoformat(request.get(BASE + '/api/health').json()['today'])
        def day(ago):
            return (today - timedelta(days=ago)).isoformat()
        response = request.post(BASE + '/api/demo/floors', headers=headers,
                                data={'name': 'Follow-through test floor', 'permission': True})
        assert response.status == 201, response.text()
        fid = response.json()['id']
        def check(ago, separated=True, slot='morning'):
            return {'floor_id': fid, 'date': day(ago), 'round': slot, 'bio': 'clean', 'nonbio': 'clean',
                    'kept_separate': separated, 'human_confirmed': True}
        assert request.post(BASE + '/api/demo/checks', headers=headers, data=check(6, False)).status == 201
        page.locator('[data-nav=plan]').click()
        page.locator(f'[data-track-collection="{fid}"]').click()
        case = page.locator(f'[data-case="{fid}"]')
        expect(case).to_contain_text('Fix not recorded')
        case.locator('[data-record-fix]').click()
        form = page.locator('#collection-fix-form')
        form.locator('[name=date]').fill(day(5))
        form.locator('[name=owner_role]').fill('Collection coordinator')
        form.locator('[name=note]').fill('Separate cart compartments. <script>must remain plain text</script>')
        form.locator('[name=due_date]').fill(day(0))
        form.get_by_role('button', name='Save fix', exact=True).click()
        expect(case).to_contain_text('More checks needed')
        expect(case.locator('.collection-note').first).to_contain_text('<script>must remain plain text</script>')
        assert case.locator('script').count() == 0
        for ago in [4, 3, 2]:
            assert request.post(BASE + '/api/demo/checks', headers=headers, data=check(ago)).status == 201
        assert request.post(BASE + '/api/demo/checks', headers=headers, data=check(2, None, 'evening')).status == 201
        page.locator('[data-nav=plan]').click()
        expect(case).to_contain_text('Ready for operator review')
        case.locator('[data-review-fix]').click()
        page.locator('#modal [data-answer=yes]').click()
        expect(case).to_contain_text('Evidence reviewed')
        case.locator('summary').first.click()
        page.screenshot(path=str(ARTIFACTS / 'collection-followup-desktop.png'), full_page=True)
        # Evidence corrections invalidate the review on the next read.
        cid = f'{day(2)}:{fid}:morning'
        assert request.put(BASE + '/api/demo/checks/' + cid, headers=headers, data=check(2, False)).status == 200
        page.locator('[data-nav=plan]').click()
        expect(case).to_contain_text('Review needed again')
        assert case.locator('[data-review-fix]').count() == 0
        # A historical weekly filter must not hide the current action.
        page.locator('#week-end').fill(day(40))
        page.wait_for_function('(end) => state.data.end === end', arg=day(40))
        expect(case).to_contain_text('Review needed again')
        page.set_viewport_size({'width': 390, 'height': 844})
        case.scroll_into_view_if_needed()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile tracker overflows'
        page.screenshot(path=str(ARTIFACTS / 'collection-followup-mobile.png'), full_page=True)
        page.locator('[data-action=language]').click()
        expect(case).to_contain_text('दोबारा समीक्षा चाहिए')
        case.locator('[data-record-fix]').click()
        expect(page.locator('#modal')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Hindi form overflows'
        page.screenshot(path=str(ARTIFACTS / 'collection-followup-hindi.png'), full_page=True)
        page.locator('#cancel-collection-fix').click()
        browser.close()
    assert not errors, errors
    print(json.dumps({'result': 'PASS', 'checks': ['track mixing', 'persist fix', 'escape note', 'review evidence',
          'invalidate on correction', 'ignore weekly filter', 'mobile layout', 'Hindi form'], 'browser_errors': errors}))
finally:
    process.terminate()
    process.wait(timeout=10)

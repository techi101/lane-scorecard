"""Real Chromium workflow, in its own temporary data directory and server.

Run: python tests/browser_check.py
Screenshots are written to artifacts/. No live pilot data is touched.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from uuid import uuid4

from playwright.sync_api import sync_playwright, expect
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / 'artifacts'
DATA = ROOT / '.local' / ('browser-' + uuid4().hex)
ARTIFACTS.mkdir(exist_ok=True)
DATA.mkdir(parents=True)
CODE = 'browser-only-test-code-not-for-deployment'
env = {**os.environ, 'LANE_DATA_DIR':str(DATA), 'LANE_PORT':'8766', 'LANE_ADMIN_CODE':CODE, 'LANE_ENABLE_AI':'0'}
for key in ['LANE_TABLE','LANE_PHOTO_BUCKET','LANE_SECURE_COOKIE','LANE_ORIGIN','AWS_LAMBDA_FUNCTION_NAME']:
    env.pop(key, None)
process = subprocess.Popen([sys.executable, 'run.py'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
errors = []
try:
    for _ in range(60):
        try:
            urllib.request.urlopen('http://127.0.0.1:8766/api/health', timeout=1)
            break
        except Exception:
            if process.poll() is not None: raise RuntimeError('Test server exited')
            time.sleep(.3)
    else:
        raise RuntimeError('Test server did not start')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge' if os.name == 'nt' else None)
        context = browser.new_context(viewport={'width':1440,'height':1050}, device_scale_factor=1)
        page = context.new_page()
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.goto('http://127.0.0.1:8766')
        page.locator('input[name=code]').fill(CODE)
        page.get_by_role('button', name='Sign in').click()
        expect(page.get_by_role('heading', name='Overview')).to_be_visible()
        page.screenshot(path=str(ARTIFACTS / 'desktop-overview.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.locator('#workspace').select_option('pilot')
        expect(page.get_by_role('heading', name='No bin locations yet.')).to_be_visible()
        page.get_by_role('button', name='Add a location', exact=True).click()
        page.locator('#floor-form input[name=name]').fill('Browser test floor')
        page.locator('#floor-form input[name=permission]').check()
        page.locator('#floor-form button[type=submit]').click()
        expect(page.locator('.data-list').filter(has_text='Browser test floor')).to_be_visible()
        page.locator('[data-nav=check]').first.click()
        page.locator('input[name=bio][value=clean]').check()
        page.locator('input[name=nonbio][value=few]').check()
        test_photo = DATA / 'test-bin.jpg'
        Image.new('RGB', (80, 60), '#bbcc88').save(test_photo)
        page.locator('input[data-photo=bio]').set_input_files(str(test_photo))
        page.locator('#modal [data-answer=yes]').click()
        expect(page.locator('#photo-bio')).to_contain_text('Photo attached')
        expect(page.locator('#photo-bio')).to_contain_text('AI is not connected')
        expect(page.locator('input[name=bio][value=clean]')).to_be_checked()
        page.locator('textarea[name=note]').fill('Test observation from an automated browser, never real pilot data.')
        page.locator('input[name=human_confirmed]').check()
        page.screenshot(path=str(ARTIFACTS / 'desktop-check.png'), full_page=True)
        page.locator('#check-form button[type=submit]').click()
        expect(page.get_by_role('heading', name='Overview')).to_be_visible()
        expect(page.locator('.stats .stat').first).to_contain_text('75')
        page.locator('[data-nav=plan]').click()
        expect(page.get_by_role('heading', name='Weekly plan')).to_be_visible()
        expect(page.locator('.plan-card')).to_contain_text('Improve separation at the bin')
        expect(page.locator('.plan-card')).to_contain_text('75 /100')
        with page.expect_download() as download_info:
            page.get_by_role('link', name='Download weekly report').click()
        report_path = DATA / download_info.value.suggested_filename
        download_info.value.save_as(report_path)
        report_text = report_path.read_text(encoding='utf-8')
        assert 'Browser test floor' in report_text
        assert 'Test observation from an automated browser' not in report_text
        page.screenshot(path=str(ARTIFACTS / 'desktop-weekly-plan.png'), full_page=True)
        page.locator('[data-followup]').click()
        expect(page.locator('select[name=floor_id] option:checked')).to_have_text('Browser test floor')
        page.locator('[data-nav=dashboard]').click()
        page.locator('[data-card]').first.click()
        expect(page.locator('#modal')).to_be_visible()
        with context.expect_page() as popup_info:
            page.locator('#modal a').click()
        card = popup_info.value
        expect(card.get_by_role('heading', name='Browser test floor')).to_be_visible()
        expect(card.locator('.public-score')).to_contain_text('75')
        card.get_by_role('button', name='हिन्दी', exact=True).click()
        expect(card.locator('.tip-box')).to_contain_text('इस हफ़्ते')
        card.screenshot(path=str(ARTIFACTS / 'scorecard-hindi.png'), full_page=True)
        card_url = card.url
        page.locator('#modal button').click()
        page.locator('[data-nav=history]').click()
        expect(page.locator('tbody')).to_contain_text('Browser test floor')
        page.locator('[data-edit]').first.click()
        page.locator('input[name=nonbio][value=clean]').check()
        page.locator('#check-form button[type=submit]').click()
        expect(page.locator('.stats .stat').first).to_contain_text('100')
        card.goto(card_url)
        expect(card.get_by_role('heading', name='यह कार्ड उपलब्ध नहीं है।')).to_be_visible()
        page.locator('#workspace').select_option('demo')
        expect(page.locator('.notice')).to_contain_text('Simulated data for practice')
        page.set_viewport_size({'width':390,'height':844})
        page.evaluate("document.querySelector('#toast').classList.remove('show')")
        page.screenshot(path=str(ARTIFACTS / 'mobile-overview.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile page overflows'
        page.locator('[data-action=menu]').click()
        page.locator('.sidebar [data-nav=check]').click()
        expect(page.get_by_role('heading', name='Record a check')).to_be_visible()
        page.screenshot(path=str(ARTIFACTS / 'mobile-check.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile form overflows'
        page.locator('[data-action=menu]').click()
        page.locator('.sidebar [data-nav=plan]').click()
        expect(page.get_by_role('heading', name='Weekly plan')).to_be_visible()
        page.screenshot(path=str(ARTIFACTS / 'mobile-weekly-plan.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile plan overflows'
        browser.close()
    assert not errors, errors
    print(json.dumps({'result':'PASS', 'checks':['login','demo dashboard','empty pilot','add floor','record check','75-point score','weekly action plan','private report download','follow-up check','private card','Hindi card','correct check','100-point score','revoke stale card','mobile layout','mobile navigation','mobile weekly plan'], 'browser_errors':errors, 'screenshots':str(ARTIFACTS)}, indent=2))
finally:
    process.terminate()
    process.wait(timeout=10)

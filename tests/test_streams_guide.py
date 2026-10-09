import base64
import csv
import io
import json
from datetime import timedelta

import boto3
from botocore.stub import Stubber
from PIL import Image

from app.actions import check_values
from app.guide import build, classify, items_from_text, read_receipt
from app.scoring import community_goal, deep_check_plan, summarize, today

from test_workflow import client, floor, record  # noqa: F401  (pytest fixture reuse)


# --- Optional sanitary and special-care streams -------------------------------------------

def test_two_bin_checks_score_exactly_as_before(client):
    fid = floor(client)
    record(client, fid, bio='clean', nonbio='mixed')
    d = client.get('/api/pilot/dashboard').json()
    assert d['streams'] == {'bio': 100, 'nonbio': 0, 'sanitary': None, 'special': None}
    assert d['score'] == 50 and d['coverage'] == 100


def test_extra_streams_count_only_when_rated(client):
    fid = floor(client)
    record(client, fid, bio='clean', nonbio='clean', sanitary='mixed', special='unseen')
    d = client.get('/api/pilot/dashboard').json()
    row = d['floors'][0]
    assert row['streams']['sanitary'] == 0 and row['streams']['special'] is None
    assert row['expected'] == 4 and row['seen'] == 3 and row['coverage'] == 75
    assert row['score'] == round((100 + 100 + 0) / 3, 1)
    assert d['both_clean_rate'] == 100  # "both bins" stays the green + blue bins
    action = next(a for a in d['actions'] if a['floor_id'] == fid)
    assert action['kind'] == 'observe' and '1 of 4' in action['evidence']


def test_outcome_statistic_ignores_extra_streams():
    rows = [{'bio': 'clean', 'nonbio': 'few', 'sanitary': 'mixed', 'special': None}]
    assert check_values(rows) == [75]


def test_weakest_extra_stream_drives_the_tip(client):
    fid = floor(client)
    record(client, fid, bio='clean', nonbio='clean', special='few')
    action = next(a for a in client.get('/api/pilot/dashboard').json()['actions'] if a['floor_id'] == fid)
    assert action['kind'] == 'segregation' and 'special-care' in action['evidence']


def test_csv_appends_new_columns(client):
    fid = floor(client)
    record(client, fid, sanitary='clean', deep=True)
    rows = list(csv.reader(io.StringIO(client.get('/api/pilot/export.csv').text.lstrip('﻿'))))
    assert rows[0][7] == 'note' and rows[0][-3:] == ['sanitary', 'special', 'deep_check']
    assert rows[1][-3:] == ['clean', 'no bin', 'yes']


def test_worker_can_report_extra_bins_and_deep_check(client):
    fid = floor(client)
    token = client.post('/api/pilot/worker-link').json()['token']
    sent = client.post(f'/api/worker/{token}/reports', json={'floor_id': fid, 'bio': 'clean', 'nonbio': 'clean', 'sanitary': 'few', 'deep': True, 'issues': ['hidden_below']})
    assert sent.status_code == 201, sent.text
    d = client.get('/api/pilot/dashboard').json()
    assert d['deep_checks'] == 1 and d['hidden_found'] == 1 and d['streams']['sanitary'] == 50
    assert client.post(f'/api/worker/{token}/reports', json={'floor_id': fid, 'bio': 'clean', 'nonbio': 'clean', 'special': 'unseen'}).status_code == 422


# --- Random deep checks ------------------------------------------------------------------

def test_deep_plan_is_stable_secret_dependent_and_marks_done():
    floors = [{'id': f'f{i}', 'name': f'Floor {i}'} for i in range(10)]
    end = today()
    plan = deep_check_plan(floors, [], end, 'secret-a')
    assert len(plan) == 2 and plan == deep_check_plan(floors, [], end, 'secret-a')
    picks = {tuple(f['id'] for f in deep_check_plan(floors, [], end, f'secret-{n}')) for n in range(8)}
    assert len(picks) > 1  # depends on the secret, so residents cannot work it out
    done = deep_check_plan(floors, [{'floor_id': plan[0]['id'], 'date': end.isoformat(), 'deep': True}], end, 'secret-a')
    assert done[0]['done'] and not done[1]['done']
    assert deep_check_plan([{'id': 'x', 'name': 'Only'}], [], end, 's')[0]['id'] == 'x'
    assert deep_check_plan([], [], end, 's') == []


def test_dashboard_lists_deep_plan(client):
    floor(client)
    plan = client.get('/api/pilot/dashboard').json()['deep_plan']
    assert len(plan) == 1 and plan[0]['done'] is False


# --- Community goal (proposal) -----------------------------------------------------------

def test_goal_needs_rate_and_enough_checks():
    floors = [{'id': 'f', 'name': 'F'}]
    end = today()
    def checks(weeks, per_week, rating):
        return [{'id': f'{w}-{i}', 'floor_id': 'f', 'date': (end - timedelta(days=7 * w + i)).isoformat(),
                 'bio': rating, 'nonbio': 'clean', 'kept_separate': None} for w in range(weeks) for i in range(per_week)]
    goal = community_goal(floors, checks(3, 5, 'clean'), end)
    assert goal['streak'] == 3 and goal['weeks_met'] == 3
    assert community_goal(floors, checks(3, 4, 'clean'), end)['streak'] == 0  # too few checks
    assert community_goal(floors, checks(3, 5, 'few'), end)['weeks_met'] == 0


def test_report_shows_goal_and_deep_checks(client):
    fid = floor(client)
    record(client, fid, deep=True, issues=['hidden_below'])
    html = client.get('/api/pilot/report.html').text
    assert 'Community goal (proposal)' in html and 'not an existing government scheme' in html
    assert 'hidden wrong items found: <strong>1</strong>' in html


# --- My Bin Guide ------------------------------------------------------------------------

RECEIPT = """ZEPTO Order #ZP123
Amul Taaza Toned Milk 500 ml  2 x 27.00  54.00
Cadbury Dairy Milk 50g 1 40
Whisper Ultra Clean 8 pads 99
Duracell AA Battery 2pcs 120
Mystery Gadget 10
Phone: 9876543210
Item Total 912
GST 5%
"""


def test_receipt_text_becomes_items_without_totals():
    names = items_from_text(RECEIPT)
    assert names[0].startswith('Amul Taaza') and len(names) == 5
    assert not any('Total' in n or 'GST' in n or 'Phone' in n for n in names)


def test_rules_split_items_into_parts_and_streams():
    assert [p['stream'] for p in classify('Amul Taaza Toned Milk')['parts']] == ['dry', 'wet']
    assert classify('Cadbury Dairy Milk')['parts'][0]['part']['en'] == 'Wrapper or packet'  # chocolate before milk
    assert classify('Whisper Ultra Clean pads')['parts'][0]['stream'] == 'sanitary'
    assert classify('Duracell AA Battery')['parts'][0]['stream'] == 'special'
    assert classify('Mystery Gadget')['source'] == 'unknown'
    assert classify('Teapot holder')['source'] == 'unknown'  # whole words only: "tea" must not match "teapot"


def test_ai_fills_only_unknown_items_and_stays_labelled():
    result = build(['Duracell AA Battery', 'Mystery Gadget'], {
        'Duracell AA Battery': [{'part': {'en': 'x', 'hi': 'x'}, 'stream': 'wet', 'tip': {}}],
        'Mystery Gadget': [{'part': {'en': 'Gadget', 'hi': 'Gadget'}, 'stream': 'ewaste', 'tip': {}}]})
    assert result['items'][0]['source'] == 'rule' and result['items'][0]['parts'][0]['stream'] == 'special'
    assert result['items'][1]['source'] == 'ai' and result['counts']['ewaste'] == 1 and result['unknown'] == 0


def test_guide_endpoint_is_public_and_stores_nothing(client, tmp_path):
    client.cookies.clear()
    response = client.post('/api/guide', json={'text': RECEIPT})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['ai'] == 'not_used' and body['counts']['sanitary'] == 1 and body['unknown'] == 1
    assert client.post('/api/guide', json={'text': '  '}).status_code == 422
    assert client.post('/api/guide', json={'text': 'milk'}, headers={'X-Lane-Request': ''}).status_code == 403
    assert client.get('/guide').status_code == 200


def test_guide_photo_says_when_ai_is_off(client):
    image = io.BytesIO()
    Image.new('RGB', (40, 40), 'white').save(image, format='PNG')
    response = client.post('/api/guide', json={'text': 'Banana 1 kg', 'image': base64.b64encode(image.getvalue()).decode()})
    assert response.status_code == 200 and response.json()['ai'] == 'disabled'
    assert response.json()['items'][0]['source'] == 'rule'


def test_guide_rate_limit(client):
    for _ in range(30):
        assert client.post('/api/guide', json={'text': 'milk'}).status_code == 200
    assert client.post('/api/guide', json={'text': 'milk'}).status_code == 429


def test_bedrock_receipt_contract():
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
    reply = {'items': [{'name': 'Surf Excel 1kg', 'parts': [{'part': 'Detergent pouch', 'stream': 'dry'}]},
                       {'name': 'Odd thing', 'parts': [{'part': 'It', 'stream': 'lava'}]}]}
    with Stubber(bedrock) as stub:
        stub.add_response('converse', {
            'output': {'message': {'role': 'assistant', 'content': [{'text': '```json\n' + json.dumps(reply) + '\n```'}]}},
            'stopReason': 'end_turn', 'usage': {'inputTokens': 10, 'outputTokens': 15, 'totalTokens': 25}, 'metrics': {'latencyMs': 5}})
        status, names, parts = read_receipt(b'jpeg-bytes', client=bedrock)
        stub.assert_no_pending_responses()
    assert status == 'available' and names == ['Surf Excel 1kg', 'Odd thing']
    assert parts['Surf Excel 1kg'][0]['stream'] == 'dry' and 'Odd thing' not in parts  # unknown stream dropped


def test_bedrock_failure_is_reported_not_guessed():
    class Broken:
        def converse(self, **_):
            raise RuntimeError('no access')
    assert read_receipt(b'x', client=Broken()) == ('unavailable', [], {})

import csv
import io

from app.scoring import ISSUES, feedback, summarize, today, top_issue

from test_workflow import client, floor, record  # noqa: F401  (pytest fixture reuse)


def test_operator_and_worker_can_tag_issues(client):
    fid = floor(client)
    record(client, fid, issues=['plastic_in_wet', 'plastic_in_wet', 'food_in_dry'])
    token = client.post('/api/pilot/worker-link').json()['token']
    assert client.post(f'/api/worker/{token}/reports', json={'floor_id': fid, 'bio': 'few', 'nonbio': 'clean', 'issues': ['one_bag']}).status_code == 201
    recent = {c['round']: c for c in client.get('/api/pilot/dashboard').json()['recent']}
    assert recent['morning']['issues'] == ['food_in_dry', 'plastic_in_wet']  # duplicates removed
    assert recent['collection']['issues'] == ['one_bag']


def test_unknown_issue_is_rejected(client):
    fid = floor(client)
    response = client.post('/api/pilot/checks', json={'floor_id': fid, 'date': today().isoformat(), 'round': 'morning',
                                                      'bio': 'clean', 'nonbio': 'clean', 'human_confirmed': True, 'issues': ['batteries']})
    assert response.status_code == 422


def test_card_gives_three_part_feedback_with_floor_norm(client):
    first, second, third = floor(client, name='First'), floor(client, name='Second'), floor(client, name='Third')
    record(client, first, bio='few', issues=['plastic_in_wet'])
    record(client, first, round='evening', bio='mixed', issues=['plastic_in_wet', 'food_in_dry'])
    record(client, second, bio='clean', nonbio='clean')
    record(client, third, bio='few', issues=['plastic_in_wet'])
    card = client.post(f'/api/pilot/cards/{first}', json={'end': today().isoformat()}).json()
    public = client.get(f"/api/public/cards/{card['token']}").json()
    fb = public['feedback']
    assert fb['issue'] == 'plastic_in_wet' and fb['times'] == 2 and fb['checks'] == 2
    assert fb['what'] == ISSUES['plastic_in_wet']['what'] and fb['why']['hi'] and fb['fix']['en']
    assert fb['norm'] == {'floors_without': 1, 'floors': 2}  # of the other floors, only "Second" had no plastic in the wet bin


def test_no_floor_comparison_without_two_other_floors(client):
    fid, other = floor(client), floor(client, name='Other')
    record(client, fid, issues=['one_bag'])
    record(client, other)
    card = client.post(f'/api/pilot/cards/{fid}', json={'end': today().isoformat()}).json()
    assert card['feedback']['issue'] == 'one_bag' and card['feedback']['norm'] is None


def test_card_without_tags_falls_back_to_the_bin_tip(client):
    fid = floor(client)
    record(client, fid)
    card = client.post(f'/api/pilot/cards/{fid}', json={'end': today().isoformat()}).json()
    assert card['feedback'] is None and card['tip']['en']


def test_weekly_action_uses_the_tagged_mistake(client):
    fid = floor(client)
    record(client, fid, bio='few', nonbio='clean', kept_separate=True, issues=['food_in_dry'])
    action = next(a for a in client.get('/api/pilot/dashboard').json()['actions'] if a['floor_id'] == fid)
    assert action['kind'] == 'segregation' and action['action'] == ISSUES['food_in_dry']['fix']
    assert 'Seen in 1 of 1 check' in action['evidence']


def test_old_checks_without_issues_still_score():
    floors = [{'id': 'f', 'name': 'F'}]
    checks = [{'id': 'c', 'floor_id': 'f', 'date': today().isoformat(), 'round': 'morning', 'bio': 'clean', 'nonbio': 'few', 'kept_separate': None}]
    summary = summarize(floors, checks, today())
    f = summary['floors'][0]
    assert f['issues'] == {k: 0 for k in ISSUES} and top_issue(f) is None and feedback(summary, f) is None


def test_csv_lists_issues(client):
    fid = floor(client)
    record(client, fid, issues=['one_bag', 'food_in_dry'])
    rows = list(csv.reader(io.StringIO(client.get('/api/pilot/export.csv').text.lstrip('﻿'))))
    assert dict(zip(rows[0], rows[1]))['issues'] == 'food_in_dry;one_bag'

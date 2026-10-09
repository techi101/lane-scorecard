"""Persisted action workflow, evidence invalidation, and concurrency contracts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json

import boto3
from botocore.stub import Stubber

from app.followups import view
from app.scoring import today
from app.storage import Store
from test_workflow import client, floor, observation, record, generate


def day(ago):
    return (today() - timedelta(days=ago)).isoformat()


def start(client):
    fid = floor(client)
    record(client, fid, date=day(6), kept_separate=False)
    response = client.post('/api/pilot/followups', json={'floor_id': fid})
    assert response.status_code == 201, response.text
    return fid, response.json()


def fix(client, fid, action, **changes):
    payload = {'revision': action['revision'], 'date': day(5), 'due_date': day(0),
               'owner_role': 'Collection coordinator', 'note': 'Separate cart compartments.', **changes}
    return client.put(f'/api/pilot/followups/{fid}/intervention', json=payload)


def current(client):
    return client.get('/api/pilot/followups').json()[0]


def review(client, fid, action):
    return client.post(f'/api/pilot/followups/{fid}/review', json={
        'revision': action['revision'], 'evidence_signature': action['evidence_signature'],
        'human_confirmed': True})


def ready(client):
    fid, action = start(client)
    assert fix(client, fid, action).status_code == 200
    for ago in [4, 3, 2]:
        record(client, fid, date=day(ago))
    return fid, current(client)


def test_fix_is_not_success_unknowns_and_same_day_excluded(client):
    fid, action = start(client)
    assert action['status'] == 'open'
    assert review(client, fid, action).status_code == 422
    assert fix(client, fid, action).json()['status'] == 'awaiting_checks'
    record(client, fid, date=day(5))  # Fix-day ordering cannot be inferred.
    for slot in ['morning', 'evening', 'collection']:
        record(client, fid, date=day(4), round=slot)
    record(client, fid, date=day(3), kept_separate=None)
    action = current(client)
    assert action['separated_days'] == 1 and action['separated_checks'] == 3
    assert action['unknown_checks'] == 1 and len(action['evidence']) == 4
    assert review(client, fid, action).status_code == 422


def test_review_persists_and_new_mixing_invalidates_it(client):
    fid, action = ready(client)
    assert action['status'] == 'ready_for_review'
    reviewed = review(client, fid, action).json()
    assert reviewed['status'] == 'reviewed'
    assert current(client)['status'] == 'reviewed'
    record(client, fid, date=day(1), kept_separate=False)
    changed = current(client)
    assert changed['status'] == 'review_needed' and not changed['can_review']
    assert changed['review'] == reviewed['review']  # Historical review remains intact.
    assert review(client, fid, changed).status_code == 422
    response = fix(client, fid, changed, date=day(1), note='Second actual intervention.')
    assert response.status_code == 200
    assert response.json()['status'] == 'awaiting_checks'
    assert [h['event'] for h in response.json()['history']] == ['opened', 'fix_recorded', 'reviewed', 'fix_recorded']


def test_any_failure_blocks_despite_three_good_days(client):
    fid, action = ready(client)
    record(client, fid, date=day(1), kept_separate=False)
    action = current(client)
    assert action['separated_days'] == 3 and action['status'] == 'mixing_observed'
    assert review(client, fid, action).status_code == 422


def test_correction_reversal_does_not_restore_old_review(client):
    fid, action = ready(client)
    assert review(client, fid, action).status_code == 200
    cid = f'{day(2)}:{fid}:morning'
    for separated in [False, True]:
        response = client.put(f'/api/pilot/checks/{cid}', json=observation(fid, date=day(2), kept_separate=separated))
        assert response.status_code == 200
        assert current(client)['status'] == 'review_needed'
    assert current(client)['can_review']
    assert review(client, fid, current(client)).json()['status'] == 'reviewed'


def test_deleting_supporting_evidence_reopens_and_removing_floor_cleans_up(client):
    fid, action = ready(client)
    assert review(client, fid, action).status_code == 200
    assert client.delete(f'/api/pilot/checks/{day(2)}:{fid}:morning').status_code == 200
    changed = current(client)
    assert changed['status'] == 'review_needed' and changed['separated_days'] == 2
    assert client.delete(f'/api/pilot/floors/{fid}').status_code == 200
    assert client.get('/api/pilot/followups').json() == []
    assert client.app.state.store.get('pilot:followups', fid) is None


def test_stale_revision_and_stale_evidence_rejected(client):
    fid, action = start(client)
    assert fix(client, fid, action).status_code == 200
    assert fix(client, fid, action, note='Stale tab overwrite.').status_code == 409
    for ago in [4, 3, 2]:
        record(client, fid, date=day(ago))
    action = current(client)
    record(client, fid, date=day(1), kept_separate=None)
    assert review(client, fid, action).status_code == 409
    assert review(client, fid, current(client)).status_code == 200


def test_new_unknown_requires_review_and_never_counts_as_success(client):
    fid, action = ready(client)
    assert review(client, fid, action).status_code == 200
    token = client.post('/api/pilot/worker-link').json()['token']
    assert client.post(f'/api/worker/{token}/reports', json={'floor_id': fid, 'bio': 'clean', 'nonbio': 'clean'}).status_code == 201
    changed = current(client)
    assert changed['status'] == 'review_needed'
    assert changed['unknown_checks'] == 1 and changed['separated_days'] == 3


def test_dates_and_duplicate_actions_validated(client):
    fid = floor(client)
    assert client.post('/api/pilot/followups', json={'floor_id': fid}).status_code == 422
    record(client, fid, date=day(6), kept_separate=False)
    action = client.post('/api/pilot/followups', json={'floor_id': fid}).json()
    assert client.post('/api/pilot/followups', json={'floor_id': fid}).status_code == 409
    for date in [day(7), day(-1), day(366)]:
        assert fix(client, fid, action, date=date).status_code == 422
    for due in [day(7), day(-91)]:
        assert fix(client, fid, action, due_date=due).status_code == 422


def test_week_filter_does_not_hide_actions_and_stale_reviews_expire(client):
    fid, action = ready(client)
    reviewed = review(client, fid, action).json()
    client.get('/api/pilot/dashboard?end=' + day(90))
    assert current(client)['status'] == 'reviewed'
    old = client.app.state.store.get('pilot:followups', fid)
    later = view(old, client.app.state.store.list('pilot:checks'), today() + timedelta(days=6))
    assert later['status'] == 'review_needed' and not later['can_review']
    assert later['review'] == reviewed['review']


def test_workspace_auth_and_public_privacy(client):
    fid, action = ready(client)
    assert client.get('/api/demo/followups').json() == []
    assert client.post('/api/demo/followups', json={'floor_id': fid}).status_code == 404
    assert client.put(f'/api/demo/followups/{fid}/intervention', json={
        'revision': 2, 'date': day(5), 'due_date': day(0), 'note': 'Wrong workspace', 'owner_role': 'Role'}).status_code == 404
    public = client.get('/api/public/cards/' + generate(client, fid))
    assert public.status_code == 200
    assert 'Separate cart compartments.' not in public.text and 'followups' not in public.text
    report = client.get('/api/pilot/report.html').text
    assert 'Separate cart compartments.' not in report
    client.post('/api/logout')
    assert client.get('/api/pilot/followups').status_code == 401
    assert client.post('/api/pilot/followups', json={'floor_id': fid}).status_code == 401


def test_atomic_updates_only_allow_one_winner(tmp_path):
    store = Store(tmp_path)
    old = {'revision': 1}
    store.put('pilot:followups', 'floor', old)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda n: store.replace_if_unchanged('pilot:followups', 'floor', old, {'revision': 2, 'writer': n}), [1, 2]))
    assert sorted(results) == [False, True]
    assert not store.replace_if_unchanged('pilot:followups', 'missing', old, {'revision': 2})


def test_dynamodb_compare_and_swap_contract(tmp_path):
    store = Store(tmp_path)
    store.table = boto3.resource('dynamodb', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test').Table('lane-test')
    old, new = {'revision': 1}, {'revision': 2}
    params = {'TableName': 'lane-test', 'Item': {'pk': 'pilot:followups', 'sk': 'floor', 'data': json.dumps(new)},
              'ConditionExpression': '#data = :expected', 'ExpressionAttributeNames': {'#data': 'data'},
              'ExpressionAttributeValues': {':expected': json.dumps(old)}}
    with Stubber(store.table.meta.client) as stub:
        stub.add_response('put_item', {}, params)
        stub.add_client_error('put_item', service_error_code='ConditionalCheckFailedException', expected_params=params)
        assert store.replace_if_unchanged('pilot:followups', 'floor', old, new)
        assert not store.replace_if_unchanged('pilot:followups', 'floor', old, new)
        stub.assert_no_pending_responses()

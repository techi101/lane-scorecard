import csv
import io

from app.scoring import today

from test_workflow import client, floor, record  # noqa: F401  (pytest fixture reuse)


def worker_link(client, workspace='pilot'):
    response = client.post(f'/api/{workspace}/worker-link')
    assert response.status_code == 201, response.text
    return response.json()['token']


def report(client, token, fid, **changes):
    return client.post(f'/api/worker/{token}/reports', json={'floor_id': fid, 'bio': 'clean', 'nonbio': 'mixed', 'hazard': False, **changes})


def test_worker_link_needs_operator_but_reports_do_not(client):
    fid = floor(client)
    client.cookies.clear()
    assert client.post('/api/pilot/worker-link').status_code == 401
    assert client.get('/api/worker/not-a-real-token').status_code == 404
    assert report(client, 'not-a-real-token', fid).status_code == 404


def test_worker_sees_only_floor_names(client):
    fid = floor(client, name='Bhaskar · First floor')
    token = worker_link(client)
    client.cookies.clear()
    view = client.get(f'/api/worker/{token}').json()
    assert view == {'demo': False, 'today': today().isoformat(), 'floors': [{'id': fid, 'name': 'Bhaskar · First floor', 'area': ''}]}


def test_worker_report_counts_as_a_collection_check(client):
    fid = floor(client)
    record(client, fid)  # the warden's morning check stays separate
    token = worker_link(client)
    assert report(client, token, fid, hazard=True).status_code == 201
    checks = client.get('/api/pilot/dashboard').json()
    rounds = sorted(c['round'] for c in checks['recent'])
    assert rounds == ['collection', 'morning']
    worker = next(c for c in checks['recent'] if c['round'] == 'collection')
    assert worker['reporter'] == 'worker' and worker['hazard'] is True and worker['date'] == today().isoformat()
    assert checks['hazards'] == 1 and checks['worker_reports'] == 1
    action = next(a for a in checks['actions'] if a['floor_id'] == fid)
    assert action['kind'] == 'safety'


def test_second_tap_same_day_replaces_the_first(client):
    fid = floor(client)
    token = worker_link(client)
    assert report(client, token, fid, bio='mixed').json()['replaced'] is False
    assert report(client, token, fid, bio='clean').json()['replaced'] is True
    recent = client.get('/api/pilot/dashboard').json()['recent']
    assert [c['bio'] for c in recent if c['round'] == 'collection'] == ['clean']


def test_worker_cannot_send_unseen_or_extra_fields(client):
    fid = floor(client)
    token = worker_link(client)
    assert report(client, token, fid, bio='unseen').status_code == 422
    assert report(client, token, fid, date='2020-01-01').status_code == 422
    assert report(client, token, 'missing-floor').status_code == 404


def test_new_link_revokes_old_and_turn_off_works(client):
    fid = floor(client)
    old = worker_link(client)
    new = worker_link(client)
    assert report(client, old, fid).status_code == 404
    assert report(client, new, fid).status_code == 201
    assert client.delete('/api/pilot/worker-link').status_code == 200
    assert report(client, new, fid).status_code == 404
    assert client.get('/api/pilot/worker-link').json() == {'token': None}


def test_operator_correction_keeps_reporter_and_hazard(client):
    fid = floor(client)
    token = worker_link(client)
    report(client, token, fid, hazard=True)
    cid = f'{today().isoformat()}:{fid}:collection'
    fix = {'floor_id': fid, 'date': today().isoformat(), 'round': 'collection', 'bio': 'few', 'nonbio': 'few',
           'kept_separate': None, 'note': 'checked again', 'photos': [], 'human_confirmed': True}
    assert client.put(f'/api/pilot/checks/{cid}', json=fix).status_code == 200
    saved = next(c for c in client.get('/api/pilot/dashboard').json()['recent'] if c['id'] == cid)
    assert saved['reporter'] == 'worker' and saved['hazard'] is True and saved['bio'] == 'few'


def test_csv_appends_hazard_and_reporter(client):
    fid = floor(client)
    token = worker_link(client)
    report(client, token, fid, hazard=True)
    rows = list(csv.reader(io.StringIO(client.get('/api/pilot/export.csv').text.lstrip('﻿'))))
    row = dict(zip(rows[0], rows[1]))
    assert row['hazard'] == 'yes' and row['reporter'] == 'worker'


def test_worker_page_is_served(client):
    page = client.get('/w/anything')
    assert page.status_code == 200 and '/assets/worker.js' in page.text


def test_worker_reports_are_rate_limited(client):
    fid = floor(client)
    token = worker_link(client)
    codes = [report(client, token, fid).status_code for _ in range(121)]
    assert codes[:120] == [201] * 120 and codes[120] == 429

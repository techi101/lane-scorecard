import base64
import csv
import io
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app, scheduled_cards
from app.scoring import summarize, today
from app.vision import parse_suggestion, sanitize, suggest
from app.actions import weekly_actions


@pytest.fixture
def client(tmp_path, monkeypatch):
    for key in ['LANE_TABLE', 'LANE_ADMIN_CODE', 'LANE_PHOTO_BUCKET', 'AWS_LAMBDA_FUNCTION_NAME', 'LANE_ENABLE_AI', 'LANE_SECURE_COOKIE', 'LANE_ORIGIN']:
        monkeypatch.delenv(key, raising=False)
    # These tests cover the private mode; tests/test_public_view.py covers the default view-only access.
    monkeypatch.setenv('LANE_PUBLIC_VIEW', '0')
    app = create_app(tmp_path)
    with TestClient(app) as test:
        test.headers['X-Lane-Request'] = '1'
        assert test.post('/api/login', json={'code': (tmp_path / 'admin-code.txt').read_text()}).status_code == 200
        yield test


def floor(client, workspace='pilot', name='First floor'):
    response = client.post(f'/api/{workspace}/floors', json={'name': name, 'permission': True})
    assert response.status_code == 201, response.text
    return response.json()['id']


def observation(fid, **changes):
    return {'floor_id': fid, 'date': today().isoformat(), 'round': 'morning', 'bio': 'clean', 'nonbio': 'mixed', 'kept_separate': True, 'note': '', 'photos': [], 'human_confirmed': True, **changes}


def record(client, fid, **changes):
    response = client.post('/api/pilot/checks', json=observation(fid, **changes))
    assert response.status_code == 201, response.text
    return response.json()


def generate(client, fid):
    response = client.post(f'/api/pilot/cards/{fid}', json={'end': today().isoformat()})
    assert response.status_code == 200, response.text
    return response.json()['token']


def test_demo_and_pilot_are_separate(client):
    demo = client.get('/api/demo/dashboard').json()
    pilot = client.get('/api/pilot/dashboard').json()
    assert demo['total_floors'] == 6 and demo['checks'] == 42
    assert all(c['source'] == 'simulated' for c in demo['recent'])
    assert pilot['total_floors'] == 0 and pilot['score'] is None
    fid = client.get('/api/demo/floors').json()[0]['id']
    assert client.post('/api/pilot/checks', json=observation(fid)).status_code == 404


def test_weekly_actions_prioritize_collection_and_missing_evidence():
    floors = [{'id': name, 'name': name} for name in ['Empty', 'Unknown', 'Collection', 'Contamination', 'Clean']]
    checks = [observation('Unknown', bio='unseen', nonbio='unseen'),
              observation('Collection', bio='clean', nonbio='clean', kept_separate=False),
              observation('Contamination', bio='clean', nonbio='mixed'),
              observation('Clean', bio='clean', nonbio='clean')]
    actions = weekly_actions(summarize(floors, checks, today()), checks)
    by_name = {a['name']: a for a in actions}
    assert by_name['Empty']['kind'] == 'observe' and by_name['Empty']['score'] is None
    assert by_name['Unknown']['kind'] == 'observe' and by_name['Unknown']['coverage'] == 0
    assert by_name['Collection']['kind'] == 'collection'
    assert by_name['Contamination']['kind'] == 'segregation'
    assert by_name['Clean']['kind'] == 'maintain'
    assert [a['name'] for a in actions] == sorted(by_name)
    assert all(a['action']['hi'] for a in actions)


def test_weekly_actions_do_not_reuse_old_collection_problems(client):
    fid = floor(client)
    record(client, fid, date=(today()-timedelta(days=7)).isoformat(), kept_separate=False)
    record(client, fid, bio='clean', nonbio='clean')
    report = client.get('/api/pilot/dashboard').json()
    assert report['actions'][0]['kind'] == 'maintain'
    assert report['actions'][0]['checks'] == 1


def test_weekly_report_is_private_escaped_and_has_no_observation_details(client):
    fid = floor(client, name='<img src=x onerror=alert(1)>')
    record(client, fid, note='SECRET OPERATOR NOTE')
    token = generate(client, fid)
    response = client.get('/api/pilot/report.html?lang=hi')
    assert response.status_code == 200
    assert 'attachment;' in response.headers['content-disposition']
    assert 'वास्तविक पायलट निरीक्षण' in response.text
    assert '&lt;img src=x onerror=alert(1)&gt;' in response.text
    assert '<img src=x' not in response.text
    assert 'SECRET OPERATOR NOTE' not in response.text and token not in response.text
    assert 'सूखी पैकिंग' in response.text
    assert client.get('/api/pilot/report.html?lang=other').status_code == 422
    assert 'DEMO — SIMULATED OBSERVATIONS' in client.get('/api/demo/report.html').text
    with TestClient(client.app) as public:
        assert public.get('/api/pilot/report.html').status_code == 401


def test_scoring_missing_is_not_clean_and_window_is_inclusive():
    end = today()
    floors = [{'id': 'a', 'name': 'A'}, {'id': 'b', 'name': 'B'}]
    rows = [observation('a', date=(end-timedelta(days=6)).isoformat(), bio='clean', nonbio='unseen'),
            observation('a', date=end.isoformat(), bio='mixed', nonbio='few'),
            observation('b', bio='unseen', nonbio='unseen'),
            observation('b', date=(end-timedelta(days=7)).isoformat(), bio='clean', nonbio='clean')]
    summary = summarize(floors, rows, end)
    assert summary['checks'] == 3
    assert summary['score'] == 50
    assert summary['floors'][0]['coverage'] == 75
    assert summary['floors'][1]['score'] is None
    assert summary['complete_checks'] == 1
    assert summary['both_clean_rate'] == 0
    assert summary['active_floors'] == 1


def test_duplicate_check_does_not_overwrite(client):
    fid = floor(client)
    record(client, fid)
    response = client.post('/api/pilot/checks', json=observation(fid, bio='mixed'))
    assert response.status_code == 409
    report = client.get('/api/pilot/dashboard').json()
    assert report['checks'] == 1 and report['score'] == 50


def test_manual_confirmation_permissions_future_dates_and_invalid_ratings(client):
    assert client.post('/api/pilot/floors', json={'name':'x', 'permission':False}).status_code == 422
    fid = floor(client)
    for changes in [{'human_confirmed':False}, {'bio':'great'}, {'date':(today()+timedelta(days=1)).isoformat()}, {'nonbio':None}, {'photos':['bad-id']}]:
        assert client.post('/api/pilot/checks', json=observation(fid, **changes)).status_code == 422


def test_private_card_is_redacted_and_revocable(client):
    fid = floor(client)
    record(client, fid, note='Private operator note')
    token = generate(client, fid)
    assert generate(client, fid) == token
    with TestClient(client.app) as public:
        value = public.get('/api/public/cards/'+token)
        assert value.status_code == 200
        data = value.json()
        assert data['score'] == 50 and data['tip']['hi']
        assert not {'id','token','index','photos','note'} & data.keys()
        assert 'Private operator note' not in value.text
        assert public.get('/api/pilot/dashboard').status_code == 401
        assert public.get('/api/pilot/export.csv').status_code == 401
        assert public.get('/card/'+token).status_code == 200
    assert client.delete('/api/pilot/cards/'+token).status_code == 200
    assert client.get('/api/public/cards/'+token).status_code == 404


def test_correction_recalculates_and_revokes_snapshot(client):
    fid = floor(client)
    check = record(client, fid)
    token = generate(client, fid)
    response = client.put('/api/pilot/checks/'+check['id'], json=observation(fid, nonbio='clean'))
    assert response.status_code == 200
    assert client.get('/api/pilot/dashboard').json()['score'] == 100
    assert client.get('/api/public/cards/'+token).status_code == 404
    assert client.put('/api/pilot/checks/'+check['id'], json=observation(fid, round='evening')).status_code == 409


def test_cookie_auth_csrf_logout_and_wrong_code(client):
    with TestClient(client.app) as public:
        assert public.post('/api/login', json={'code':'wrong'}).status_code == 403
        assert public.post('/api/login', headers={'X-Lane-Request':'1'}, json={'code':'🔐wrong'}).status_code == 401
    assert client.post('/api/pilot/floors', headers={'Origin':'https://evil.example'}, json={'name':'x','permission':True}).status_code == 403
    assert client.post('/api/pilot/floors', headers={'X-Lane-Request':''}, json={'name':'x','permission':True}).status_code == 403
    response = client.get('/')
    assert response.headers['x-frame-options'] == 'DENY'
    assert 'frame-ancestors' in response.headers['content-security-policy']
    client.post('/api/logout')
    assert client.get('/api/pilot/dashboard').status_code == 401


def test_csv_quotes_formula_content_and_filters_week(client):
    fid = floor(client, name='=HYPERLINK("bad")')
    record(client, fid, note='  =1+1,\nnext line')
    record(client, fid, date=(today()-timedelta(days=8)).isoformat())
    response = client.get('/api/pilot/export.csv')
    rows = list(csv.reader(io.StringIO(response.text.lstrip('\ufeff'))))
    assert len(rows) == 2
    assert rows[1][0] == 'real pilot'
    assert rows[1][1].startswith("'=")
    assert rows[1][7] == "'=1+1,\nnext line"


def photo_bytes():
    image = Image.new('RGB', (40, 30), '#ddaa44')
    buffer = io.BytesIO()
    exif = Image.Exif(); exif[270] = 'private metadata'
    image.save(buffer, format='JPEG', exif=exif)
    return buffer.getvalue()


def test_photo_metadata_stripped_and_no_fake_ai():
    raw = sanitize(photo_bytes())
    assert not Image.open(io.BytesIO(raw)).getexif()
    assert parse_suggestion('```json\n{"rating":"unseen","reason":"Obscured"}\n```')['rating'] == 'unseen'
    with pytest.raises(ValueError):
        sanitize(b'not an image')
    with pytest.raises(ValueError):
        parse_suggestion('{"rating":"excellent","reason":"test"}')
    class Unavailable:
        def converse(self, **kwargs): raise RuntimeError('private AWS error')
    result = suggest(raw, 'bio', client=Unavailable())
    assert result['status'] == 'unavailable' and result['rating'] is None
    assert 'private AWS' not in result['reason']


def test_photo_attachment_evaluation_and_deletion(client, monkeypatch):
    monkeypatch.setattr('app.main.suggest', lambda raw, stream: {'status':'available','rating':'few','reason':'Visible wrapper','model':'test-only'})
    encoded = base64.b64encode(photo_bytes()).decode()
    response = client.post('/api/pilot/photos', json={'image':encoded,'stream':'bio','permission':True})
    assert response.status_code == 201
    pid = response.json()['id']
    fid = floor(client)
    check = record(client, fid, bio='few', photos=[pid])
    assert client.get('/api/pilot/dashboard').json()['evaluation']['bio'] == {'total':1,'matched':1}
    assert client.post('/api/pilot/checks', json=observation(fid, round='evening', photos=[pid])).status_code == 409
    assert client.delete('/api/pilot/photos/'+pid).status_code == 409
    with TestClient(client.app) as public:
        assert public.get('/api/pilot/photos/'+pid).status_code == 401
    assert client.delete('/api/pilot/checks/'+check['id']).status_code == 200
    assert client.get('/api/pilot/photos/'+pid).status_code == 404
    assert not (client.app.state.directory / 'photos' / (pid+'.jpg')).exists()


def test_floor_deletion_removes_checks_and_cards(client):
    fid = floor(client)
    record(client, fid)
    token = generate(client, fid)
    assert client.delete('/api/pilot/floors/'+fid).status_code == 200
    assert client.get('/api/pilot/dashboard').json()['checks'] == 0
    assert client.get('/api/public/cards/'+token).status_code == 404


def test_weekly_job_only_generates_real_pilot_cards(client):
    fid = floor(client)
    record(client, fid, date=(today()-timedelta(days=1)).isoformat())
    floor(client, name='Unobserved floor')
    result = scheduled_cards(client.app.state.store)
    assert result['generated'] == 1
    cards = client.get('/api/pilot/cards').json()
    assert len(cards) == 1 and cards[0]['source'] == 'real pilot'
    assert cards[0]['end'] == (today()-timedelta(days=1)).isoformat()


def test_data_and_access_code_survive_application_restart(client):
    fid = floor(client)
    record(client, fid, bio='few', nonbio='few')
    second_app = create_app(client.app.state.directory)
    with TestClient(second_app) as second:
        second.headers['X-Lane-Request'] = '1'
        code = (client.app.state.directory / 'admin-code.txt').read_text()
        assert second.post('/api/login', json={'code':code}).status_code == 200
        report = second.get('/api/pilot/dashboard').json()
        assert report['checks'] == 1 and report['score'] == 50


def test_cleanup_removes_only_old_unattached_photos(client):
    from app.maintenance import cleanup
    from datetime import datetime, timezone
    import time
    store, directory = client.app.state.store, client.app.state.directory
    old = (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    (directory / 'photos').mkdir(exist_ok=True)
    for pid in ('abandoned', 'attached'):
        (directory / 'photos' / (pid+'.jpg')).write_bytes(photo_bytes())
        store.put('pilot:photos', pid, {'id':pid, 'stream':'bio','created_at':old,'suggestion':{'status':'disabled','rating':None}})
    fid = floor(client)
    record(client, fid, photos=['attached'])
    store.put('sessions','expired-test',{'key':'expired-test','expires':time.time()-1})
    result = cleanup(store, directory)
    assert result == {'sessions':1,'unattached_photos':1}
    assert store.get('pilot:photos','attached') is not None
    assert store.get('pilot:photos','abandoned') is None
    assert (directory / 'photos' / 'attached.jpg').exists()
    assert not (directory / 'photos' / 'abandoned.jpg').exists()

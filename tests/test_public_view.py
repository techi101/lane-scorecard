import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.scoring import today


@pytest.fixture
def app(tmp_path, monkeypatch):
    for key in ['LANE_TABLE', 'LANE_ADMIN_CODE', 'LANE_PHOTO_BUCKET', 'AWS_LAMBDA_FUNCTION_NAME', 'LANE_ENABLE_AI', 'LANE_SECURE_COOKIE', 'LANE_ORIGIN', 'LANE_PUBLIC_VIEW']:
        monkeypatch.delenv(key, raising=False)
    return create_app(tmp_path)


@pytest.fixture
def operator(app, tmp_path):
    with TestClient(app) as test:
        test.headers['X-Lane-Request'] = '1'
        assert test.post('/api/login', json={'code': (tmp_path / 'admin-code.txt').read_text()}).status_code == 200
        fid = test.post('/api/pilot/floors', json={'name': 'Canteen', 'permission': True}).json()['id']
        check = {'floor_id': fid, 'date': today().isoformat(), 'round': 'morning', 'bio': 'mixed', 'nonbio': 'clean',
                 'kept_separate': None, 'note': '', 'photos': [], 'human_confirmed': True}
        assert test.post('/api/pilot/checks', json=check).status_code == 201
        assert test.post('/api/pilot/worker-link').status_code == 201
        yield test, fid


@pytest.fixture
def visitor(app):
    with TestClient(app) as test:
        test.headers['X-Lane-Request'] = '1'
        yield test


@pytest.mark.parametrize('workspace', ['demo', 'pilot'])
def test_visitor_can_read_both_workspaces(operator, visitor, workspace):
    for path in ['dashboard', 'floors', 'cards', 'photos', 'followups', 'export.csv', 'report.html']:
        assert visitor.get(f'/api/{workspace}/{path}').status_code == 200, path
    if workspace == 'pilot':
        assert visitor.get('/api/pilot/dashboard').json()['checks'] == 1


def test_visitor_cannot_change_anything(operator, visitor):
    _, fid = operator
    check_id = f'{today().isoformat()}:{fid}:morning'
    attempts = [
        ('post', '/api/pilot/floors', {'name': 'Vandal', 'permission': True}),
        ('put', f'/api/pilot/floors/{fid}', {'name': 'Renamed', 'permission': True}),
        ('delete', f'/api/pilot/floors/{fid}', None),
        ('post', '/api/pilot/checks', {'floor_id': fid, 'date': today().isoformat(), 'round': 'evening', 'bio': 'clean',
                                       'nonbio': 'clean', 'kept_separate': None, 'note': '', 'photos': [], 'human_confirmed': True}),
        ('delete', f'/api/pilot/checks/{check_id}', None),
        ('post', f'/api/pilot/cards/{fid}', {'end': today().isoformat()}),
        ('post', '/api/pilot/worker-link', None),
        ('delete', '/api/pilot/worker-link', None),
        ('post', '/api/pilot/followups', {'floor_id': fid}),
    ]
    for method, path, body in attempts:
        response = visitor.request(method.upper(), path, json=body)
        assert response.status_code == 401, (method, path, response.status_code)
    test, _ = operator
    assert [f['name'] for f in test.get('/api/pilot/floors').json()] == ['Canteen']
    assert test.get('/api/pilot/dashboard').json()['checks'] == 1


def test_secrets_stay_operator_only(operator, visitor):
    assert visitor.get('/api/pilot/worker-link').status_code == 401
    assert visitor.get('/api/pilot/audit').status_code == 401
    assert visitor.get('/api/session').status_code == 401
    test, _ = operator
    assert test.get('/api/pilot/worker-link').json()['token']


def test_viewer_reports_who_is_looking_and_latest_data(operator, visitor):
    test, _ = operator
    seen = visitor.get('/api/viewer').json()
    assert seen['operator'] is False and seen['public_view'] is True
    assert seen['latest']['pilot'] == today().isoformat()
    assert test.get('/api/viewer').json()['operator'] is True


def test_public_view_can_be_switched_off(tmp_path, monkeypatch):
    monkeypatch.setenv('LANE_PUBLIC_VIEW', '0')
    for key in ['LANE_TABLE', 'LANE_ADMIN_CODE', 'LANE_PHOTO_BUCKET', 'AWS_LAMBDA_FUNCTION_NAME']:
        monkeypatch.delenv(key, raising=False)
    with TestClient(create_app(tmp_path)) as test:
        assert test.get('/api/pilot/dashboard').status_code == 401
        assert test.get('/api/viewer').json()['public_view'] is False

import base64

from test_workflow import client, floor, photo_bytes, record  # noqa: F401  (pytest fixture reuse)


def upload(client, stream='bio'):
    encoded = base64.b64encode(photo_bytes()).decode()
    response = client.post('/api/pilot/photos', json={'image': encoded, 'stream': stream, 'permission': True})
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_photo_list_shows_location_date_round_and_bin(client):
    fid = client.post('/api/pilot/floors', json={'name': 'Library · entrance', 'area': 'Library', 'permission': True}).json()['id']
    pid = upload(client, 'nonbio')
    check = record(client, fid, photos=[pid])
    loose = upload(client)
    rows = {r['id']: r for r in client.get('/api/pilot/photos').json()}
    assert rows[pid]['stream'] == 'nonbio'
    assert rows[pid]['check'] == {'id': check['id'], 'date': check['date'], 'round': 'morning', 'location': 'Library · entrance', 'area': 'Library'}
    assert rows[loose]['check'] is None


def test_deleting_an_attached_photo_keeps_the_check(client):
    fid = floor(client)
    pid = upload(client)
    check = record(client, fid, photos=[pid], bio='few')
    assert client.delete(f'/api/pilot/photos/{pid}').status_code == 409  # attached: must use the check route
    assert client.delete(f"/api/pilot/checks/{check['id']}/photos/{pid}").status_code == 200
    after = next(c for c in client.get('/api/pilot/dashboard').json()['recent'] if c['id'] == check['id'])
    assert after['photos'] == [] and after['bio'] == 'few'
    assert client.get(f'/api/pilot/photos/{pid}').status_code == 404
    assert not (client.app.state.directory / 'photos' / f'{pid}.jpg').exists()
    assert client.get('/api/pilot/photos').json() == []
    assert any(a['action'] == 'photo_deleted' for a in client.get('/api/pilot/audit').json())


def test_wrong_check_or_photo_is_refused(client):
    fid = floor(client)
    pid = upload(client)
    check = record(client, fid, photos=[pid])
    assert client.delete(f"/api/pilot/checks/{check['id']}/photos/not-a-photo").status_code == 404
    assert client.delete(f'/api/pilot/checks/not-a-check/photos/{pid}').status_code == 404
    assert client.delete(f"/api/demo/checks/{check['id']}/photos/{pid}").status_code == 404  # other workspace


def test_photos_need_sign_in(client):
    client.cookies.clear()
    assert client.get('/api/pilot/photos').status_code == 401

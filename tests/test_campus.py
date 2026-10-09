from app.main import DEMO_LOCATIONS, MAX_LOCATIONS, create_app, seed_demo
from app.scoring import area_summary, location_order, summarize, today
from app.storage import Store

from test_workflow import client, floor, record  # noqa: F401  (pytest fixture reuse)


def add(client, name, area=''):
    response = client.post('/api/pilot/floors', json={'name': name, 'area': area, 'permission': True})
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_locations_keep_their_area(client):
    fid = add(client, 'Library · entrance', 'Library')
    assert next(f for f in client.get('/api/pilot/floors').json() if f['id'] == fid)['area'] == 'Library'


def test_area_is_optional_and_limited(client):
    assert add(client, 'Somewhere')
    long = client.post('/api/pilot/floors', json={'name': 'X', 'area': 'a' * 41, 'permission': True})
    assert long.status_code == 422


def test_campus_allows_many_locations(client):
    for i in range(60):  # more than the old 50-floor hostel limit
        add(client, f'Spot {i}', 'Academic blocks')
    assert MAX_LOCATIONS == 200


def test_plan_and_worker_list_are_grouped_by_area(client):
    add(client, 'Zeta gate', 'Hostels'); add(client, 'Alpha path'); add(client, 'Beta canteen', 'Canteen & food')
    names = [a['name'] for a in client.get('/api/pilot/dashboard').json()['actions']]
    assert names == ['Beta canteen', 'Zeta gate', 'Alpha path']  # areas A-Z, locations without an area last
    token = client.post('/api/pilot/worker-link').json()['token']
    view = client.get(f'/api/worker/{token}').json()
    assert [(f['area'], f['name']) for f in view['floors']] == [('Canteen & food', 'Beta canteen'), ('Hostels', 'Zeta gate'), ('', 'Alpha path')]


def test_area_summary_rolls_up_scores_and_hazards():
    floors = [{'id': 'a', 'name': 'A', 'area': 'Library'}, {'id': 'b', 'name': 'B', 'area': 'Library'}, {'id': 'c', 'name': 'C'}]
    day = today().isoformat()
    checks = [{'id': '1', 'floor_id': 'a', 'date': day, 'round': 'morning', 'bio': 'clean', 'nonbio': 'clean', 'kept_separate': None},
              {'id': '2', 'floor_id': 'b', 'date': day, 'round': 'morning', 'bio': 'mixed', 'nonbio': 'clean', 'kept_separate': None, 'hazard': True}]
    rows = area_summary(summarize(floors, checks, today()))
    assert rows[0] == {'area': 'Library', 'locations': 2, 'checks': 2, 'hazards': 1, 'score': 75.0, 'scored': 2}
    assert rows[-1]['area'] == 'Other' and rows[-1]['score'] is None


def test_demo_is_a_campus_and_old_hostel_demo_is_replaced(tmp_path):
    store = Store(tmp_path)
    store.put('meta', 'demo-seeded', {'at': 'old'})
    store.put('demo:floors', 'demo-floor-0', {'id': 'demo-floor-0', 'name': 'Ground floor', 'permission': True})
    store.put('demo:checks', 'old', {'id': 'old', 'floor_id': 'demo-floor-0', 'date': today().isoformat()})
    store.put('demo:floors', 'mine', {'id': 'mine', 'name': 'TEST · mine', 'permission': True})
    seed_demo(store)
    names = {f['name'] for f in store.list('demo:floors')}
    assert names == {n for n, _ in DEMO_LOCATIONS} | {'TEST · mine'}
    assert not any(c['id'] == 'old' for c in store.list('demo:checks'))
    seed_demo(store)  # runs once
    assert len(store.list('demo:floors')) == len(DEMO_LOCATIONS) + 1


def test_location_order_puts_unassigned_last():
    rows = [{'name': 'b'}, {'name': 'a', 'area': 'Sports'}, {'name': 'c', 'area': 'Admin'}]
    assert [r['name'] for r in sorted(rows, key=location_order)] == ['c', 'a', 'b']


def test_rename_keeps_checks_and_photos(client):
    fid = add(client, 'Spot 05 · near lit building')
    record(client, fid)
    r = client.put(f'/api/pilot/floors/{fid}', json={'name': 'Aryabhatta block · front', 'area': 'Academic blocks', 'permission': True})
    assert r.status_code == 200 and r.json()['name'] == 'Aryabhatta block · front'
    action = next(a for a in client.get('/api/pilot/dashboard').json()['actions'] if a['floor_id'] == fid)
    assert action['name'] == 'Aryabhatta block · front' and action['area'] == 'Academic blocks' and action['checks'] == 1


def test_rename_refuses_duplicates_and_unknown(client):
    a, b = add(client, 'A'), add(client, 'B')
    assert client.put(f'/api/pilot/floors/{b}', json={'name': 'a', 'area': '', 'permission': True}).status_code == 409
    assert client.put('/api/pilot/floors/nope', json={'name': 'C', 'area': '', 'permission': True}).status_code == 404
    assert client.put(f'/api/pilot/floors/{a}', json={'name': 'A', 'area': 'Library', 'permission': True}).status_code == 200  # same name, new area

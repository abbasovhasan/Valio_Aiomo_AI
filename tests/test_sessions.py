from fastapi.testclient import TestClient
from backend.app import create_app
from backend.config import access_codes
from backend.store import Store


def test_session_survives_restart_and_logout_remains_revoked(tmp_path):
    store=Store(path=tmp_path/'sessions.sqlite3',postgres=False)
    first=TestClient(create_app(store))
    login=first.post('/api/v1/session',json={'access_code':access_codes()['buyer']})
    assert login.status_code==200
    cookie=first.cookies.get('aimo_session')
    second=TestClient(create_app(store))
    second.cookies.set('aimo_session',cookie)
    assert second.get('/api/v1/session').json()['role']=='buyer'
    assert second.delete('/api/v1/session').status_code==200
    third=TestClient(create_app(store))
    third.cookies.set('aimo_session',cookie)
    assert third.get('/api/v1/session').json()['role'] is None

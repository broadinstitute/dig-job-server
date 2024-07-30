from starlette.testclient import TestClient


def test_foo(api_client: TestClient):
    res = api_client.post("/api/login", json={"username": "testuser@broadinstitute.org", "password": "change.me"})
    assert res.status_code == 200

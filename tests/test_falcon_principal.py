from starlette.testclient import TestClient

from job_server import falcon_tokens
from tests.fixtures import seed_dataset


def test_dependency_accepts_jwt(api_client: TestClient):
    from tests.test_api import get_token
    seed_dataset("ds1", username="testuser")
    jwt = get_token(api_client)
    res = api_client.get(
        "/api/_falcon_principal_probe/ds1",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert res.status_code == 200
    assert res.json() == {"user_id": 1, "dataset_name": "ds1"}


def test_dependency_accepts_dft_token(api_client: TestClient):
    seed_dataset("ds1", username="testuser")
    token, _ = falcon_tokens.mint(user_id=1, dataset_name="ds1")

    res = api_client.get(
        "/api/_falcon_principal_probe/ds1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json() == {"user_id": 1, "dataset_name": "ds1"}


def test_dependency_rejects_token_for_different_dataset(api_client):
    seed_dataset("ds1", username="testuser")
    seed_dataset("ds2", username="testuser")
    token, _ = falcon_tokens.mint(user_id=1, dataset_name="ds1")

    res = api_client.get(
        "/api/_falcon_principal_probe/ds2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_dependency_rejects_no_credentials(api_client):
    res = api_client.get("/api/_falcon_principal_probe/ds1")
    assert res.status_code == 401

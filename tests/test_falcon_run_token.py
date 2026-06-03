import pytest
from sqlalchemy import text

from job_server.database import get_db
from tests.fixtures import seed_dataset
from tests.test_api import get_token


@pytest.fixture
def auth_token(api_client):
    return get_token(api_client)


def test_mints_token_for_owned_dataset(api_client, auth_token):
    seed_dataset("ds1", username="testuser")

    res = api_client.post(
        "/api/falcon/run-token",
        json={"dataset_name": "ds1"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token"].startswith("dft_")
    assert "expires_at" in body


def test_rejects_unowned_dataset(api_client, auth_token):
    # seed a dataset that belongs to a different user
    with get_db() as con:
        con.execute(text(
            "INSERT INTO users (id, user_name, password, created_at) "
            "VALUES (2, 'other', '', NOW())"
        ))
        con.commit()
    seed_dataset("other_ds", username="other")

    res = api_client.post(
        "/api/falcon/run-token",
        json={"dataset_name": "other_ds"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code in (403, 404)


def test_rejects_without_session(api_client):
    res = api_client.post("/api/falcon/run-token", json={"dataset_name": "ds1"})
    assert res.status_code == 401



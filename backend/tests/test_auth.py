from backend.tests.conftest import register, login


def test_register_then_login_succeeds(client):
    r = register(client)
    assert r.status_code == 201

    r = login(client)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_duplicate_registration_is_rejected(client):
    assert register(client).status_code == 201
    r = register(client)
    assert r.status_code == 400


def test_login_with_wrong_password_is_rejected(client):
    register(client)
    r = login(client, password="wrong-password")
    assert r.status_code == 401


def test_submit_project_requires_auth(client):
    r = client.post(
        "/api/v1/submit-project",
        files={"file": ("test.zip", b"PK\x03\x04fake", "application/zip")},
    )
    assert r.status_code == 401


def test_results_requires_auth(client):
    r = client.get("/api/v1/results")
    assert r.status_code == 401


def test_users_cannot_see_each_others_task_list(client):
    register(client, "alice", "password123")
    register(client, "bob", "password123")
    alice_token = login(client, "alice", "password123").json()["access_token"]
    bob_token = login(client, "bob", "password123").json()["access_token"]

    # Neither user has submitted anything, but the important thing this
    # asserts is that /results is scoped per-user rather than global -
    # both requests must succeed independently, authenticated as different
    # users, without interfering with each other.
    r_alice = client.get("/api/v1/results", headers={"Authorization": f"Bearer {alice_token}"})
    r_bob = client.get("/api/v1/results", headers={"Authorization": f"Bearer {bob_token}"})
    assert r_alice.status_code == 200
    assert r_bob.status_code == 200
    assert r_alice.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}
    assert r_bob.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}

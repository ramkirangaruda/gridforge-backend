from backend.tests.conftest import auth_headers, register_and_login, submit_fake_task


def test_results_pagination_defaults_and_ordering(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    for i in range(3):
        r = submit_fake_task(client, headers, filename=f"proj{i}.zip")
        assert r.status_code == 200, r.text

    r = client.get("/api/v1/results", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 3
    # newest first
    assert [t["filename"] for t in data["items"]] == ["proj2.zip", "proj1.zip", "proj0.zip"]


def test_results_pagination_limit_and_offset_cover_all_pages_without_overlap(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    for i in range(5):
        submit_fake_task(client, headers, filename=f"proj{i}.zip")

    page1 = client.get("/api/v1/results?limit=2&offset=0", headers=headers).json()
    page2 = client.get("/api/v1/results?limit=2&offset=2", headers=headers).json()
    page3 = client.get("/api/v1/results?limit=2&offset=4", headers=headers).json()

    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert len(page3["items"]) == 1
    assert page1["total"] == page2["total"] == page3["total"] == 5

    ids = [t["id"] for page in (page1, page2, page3) for t in page["items"]]
    assert len(ids) == len(set(ids)) == 5


def test_results_limit_out_of_bounds_is_rejected(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    assert client.get("/api/v1/results?limit=0", headers=headers).status_code == 422
    assert client.get("/api/v1/results?limit=101", headers=headers).status_code == 422
    assert client.get("/api/v1/results?offset=-1", headers=headers).status_code == 422


def test_delete_task_requires_auth(client):
    r = client.delete("/api/v1/task/some-id")
    assert r.status_code == 401


def test_delete_nonexistent_task_returns_404(client):
    token = register_and_login(client)
    r = client.delete("/api/v1/task/does-not-exist", headers=auth_headers(token))
    assert r.status_code == 404


def test_users_cannot_delete_each_others_tasks(client):
    alice_token = register_and_login(client, "alice", "password123")
    bob_token = register_and_login(client, "bob", "password123")

    r = submit_fake_task(client, auth_headers(alice_token))
    task_id = r.json()["id"]

    r = client.delete(f"/api/v1/task/{task_id}", headers=auth_headers(bob_token))
    assert r.status_code == 404

    # untouched for alice
    r = client.get(f"/api/v1/task/{task_id}", headers=auth_headers(alice_token))
    assert r.status_code == 200


def test_owner_can_delete_own_task(client):
    token = register_and_login(client)
    headers = auth_headers(token)
    r = submit_fake_task(client, headers)
    task_id = r.json()["id"]

    r = client.delete(f"/api/v1/task/{task_id}", headers=headers)
    assert r.status_code == 204
    assert r.text == ""

    assert client.get(f"/api/v1/task/{task_id}", headers=headers).status_code == 404
    assert client.get("/api/v1/results", headers=headers).json()["total"] == 0

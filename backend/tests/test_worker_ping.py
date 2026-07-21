def test_worker_ping_requires_worker_key(client):
    r = client.get("/api/v1/worker/ping")
    assert r.status_code == 403


def test_worker_ping_rejects_wrong_key(client):
    r = client.get("/api/v1/worker/ping", headers={"X-Worker-Key": "wrong-key"})
    assert r.status_code == 403


def test_worker_ping_accepts_correct_key(client):
    # Matches conftest.py's os.environ.setdefault("WORKER_API_KEY", ...)
    r = client.get("/api/v1/worker/ping", headers={"X-Worker-Key": "test-worker-key-for-ci-only"})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

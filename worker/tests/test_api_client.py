from unittest.mock import MagicMock, patch

from api_client import update_task_status
from config import settings


def _mock_response():
    response = MagicMock(status_code=200)
    response.json.return_value = {"ok": True}
    response.raise_for_status.return_value = None
    return response


@patch("api_client.requests.post")
def test_update_task_status_authenticates_with_worker_key(mock_post):
    mock_post.return_value = _mock_response()

    update_task_status("task-123", "running")

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["X-Worker-Key"] == settings.WORKER_API_KEY
    assert kwargs["json"] == {"status": "running"}


@patch("api_client.requests.post")
def test_update_task_status_omits_unset_optional_fields(mock_post):
    mock_post.return_value = _mock_response()

    update_task_status("task-123", "completed", logs="done", exit_code=0)

    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert payload["logs"] == "done"
    assert payload["exit_code"] == 0
    # Never sent, not merely None - the real update_task endpoint treats a
    # present-but-null field differently from an absent one (exclude_unset).
    assert "execution_time" not in payload


@patch("api_client.requests.post")
def test_update_task_status_returns_none_on_connection_error(mock_post):
    import requests

    mock_post.side_effect = requests.exceptions.ConnectionError("refused")

    result = update_task_status("task-123", "running")

    assert result is None

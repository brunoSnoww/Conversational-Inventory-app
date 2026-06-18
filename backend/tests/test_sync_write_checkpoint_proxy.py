import json
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse


@pytest.fixture
def write_checkpoint_url():
    return reverse("sync-write-checkpoint")


def test_write_checkpoint_proxy_requires_client_id(client, write_checkpoint_url):
    resp = client.get(
        write_checkpoint_url,
        HTTP_AUTHORIZATION="Token ps-token",
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "client_id required"


def test_write_checkpoint_proxy_requires_auth(client, write_checkpoint_url):
    resp = client.get(write_checkpoint_url, {"client_id": "abc"})
    assert resp.status_code == 401


@patch("sync_api.views.POWERSYNC_URL", "http://powersync.test:2000")
@patch("sync_api.views.urlopen")
def test_write_checkpoint_proxy_forwards(mock_urlopen, client, write_checkpoint_url):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(
        {"data": {"write_checkpoint": "ckpt-123"}}
    ).encode()
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    resp = client.get(
        write_checkpoint_url,
        {"client_id": "client-1"},
        HTTP_AUTHORIZATION="Token ps-token",
    )

    assert resp.status_code == 200
    assert resp.json() == {"data": {"write_checkpoint": "ckpt-123"}}
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "http://powersync.test:2000/write-checkpoint2.json?client_id=client-1"
    assert request.headers["Authorization"] == "Token ps-token"

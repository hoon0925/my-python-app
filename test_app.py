from unittest.mock import MagicMock, patch

with patch("redis.Redis", MagicMock()), patch("pika.BlockingConnection", MagicMock()):
    from app import app


def test_hello():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200


def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200

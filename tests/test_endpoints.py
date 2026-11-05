import requests


def test_health():
    response = requests.get("http://localhost:8000/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "2.0.0"

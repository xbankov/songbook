import requests


def test_index():
    response = requests.get("http://localhost:8000/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI"}

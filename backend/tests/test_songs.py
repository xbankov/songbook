# backend/tests/test_songs.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_songs():
    response = client.get("/songs")
    assert response.status_code == 200
    assert "songs" in response.json()

def test_create_song_text_field():
    response = client.post(
        "/songs",
        data={"input-method": "text-field", "chordpro": "some chordpro data"}
    )
    assert response.status_code == 302  # Redirect to home page

def test_create_song_url_field(monkeypatch):
    def mock_download(url):
        return {"artist": "Test Artist", "title": "Test Title"}
    
    monkeypatch.setattr("utils.download", mock_download)
    
    response = client.post(
        "/songs",
        data={"input-method": "url-field", "url-field": "http://example.com/song"}
    )
    assert response.status_code == 302  # Redirect to home page

def test_get_song():
    # Assuming there's a song with ID '60d21b4667d0d8992e610c85' in the database
    response = client.get("/songs/60d21b4667d0d8992e610c85")
    assert response.status_code == 200
    assert "song" in response.json()

def test_add_song():
    response = client.get("/songs/add")
    assert response.status_code == 200
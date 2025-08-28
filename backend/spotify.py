"""
Dieses Modul kapselt die gesamte Logik für die Interaktion mit der Spotify API.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SpotifyClient:
    """Ein Client für die Interaktion mit der Spotify Web API."""
    API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self):
        self._client_id = os.getenv('SPOTIPY_CLIENT_ID')
        self._client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        self._access_token = self._get_access_token()

    def _get_access_token(self):
        url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret
        }
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        return response.json()["access_token"]

    def _make_request(self, endpoint):
        url = f"{self.API_BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_playlist_tracks(self, playlist_id, market):
        """Holt alle Tracks einer bestimmten Playlist."""
        endpoint = f"/playlists/{playlist_id}/tracks?market={market}&limit=50"
        all_tracks = []
        while endpoint:
            data = self._make_request(endpoint)
            for item in data.get("items", []):
                track = item.get("track")
                if track and track.get("name") and track.get("artists"):
                    all_tracks.append({
                        "name": track["name"],
                        "artists": [artist["name"] for artist in track.get("artists", [])],
                        "album": track.get("album", {}).get("name", "Unknown Album"),
                    })
            next_url = data.get("next")
            endpoint = next_url.replace(self.API_BASE_URL, "") if next_url else None
        return all_tracks

    def get_playlist_name(self, playlist_id):
        endpoint = f"/playlists/{playlist_id}"
        data = self._make_request(endpoint)
        return data.get("name", "Unknown Playlist")

def _extract_playlist_id(playlist_url):
    try:
        return playlist_url.split("/playlist/")[1].split("?")[0]
    except IndexError as e:
        raise ValueError("Ungültige Spotify-Playlist-URL") from e

def get_all_tracks(link, market):
    playlist_id = _extract_playlist_id(link)
    client = SpotifyClient()
    return client.get_playlist_tracks(playlist_id, market)

def get_playlist_name(link):
    playlist_id = _extract_playlist_id(link)
    client = SpotifyClient()
    return client.get_playlist_name(playlist_id)

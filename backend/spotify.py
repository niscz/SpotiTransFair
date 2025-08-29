"""
This module encapsulates all logic for interacting with the Spotify API.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SpotifyError(Exception):
    """Custom exception for errors related to the Spotify API."""

class SpotifyClient:
    """A client for interacting with the Spotify Web API."""
    API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self):
        self._client_id = os.getenv('SPOTIPY_CLIENT_ID')
        self._client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        self._access_token = self._get_access_token()

    def _get_access_token(self):
        """Fetches a new access token from the Spotify API."""
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
        """Makes an authenticated request to a Spotify API endpoint."""
        url = f"{self.API_BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 401:
                # one refresh attempt
                self._access_token = self._get_access_token()
                headers["Authorization"] = f"Bearer {self._access_token}"
                resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise SpotifyError(
                    "Playlist not found. Please ensure the URL is correct and the playlist is public."
                ) from e
            if e.response.status_code == 401:
                raise SpotifyError(
                    "Invalid Spotify credentials. Please check your .env file."
                ) from e
            # Catch other potential HTTP errors
            raise SpotifyError(f"Spotify API returned an error: {e}") from e
        except requests.exceptions.RequestException as e:
            # Catch network errors
            raise SpotifyError(f"Could not connect to Spotify API: {e}") from e

    def get_playlist_tracks(self, playlist_id, market=None):
        """Fetches all tracks from a given playlist."""
        endpoint = f"/playlists/{playlist_id}/tracks"
        if market:
            endpoint += f"?market={market}&limit=50"
        else:
            endpoint += "?limit=50"
        all_tracks = []
        while endpoint:
            data = self._make_request(endpoint)
            for item in data.get("items", []):
                track = item.get("track")
                # Add check to ignore tracks without a name or artists
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
        """Fetches the name of a playlist."""
        endpoint = f"/playlists/{playlist_id}"
        data = self._make_request(endpoint)
        return data.get("name", "Unknown Playlist")

def _extract_playlist_id(playlist_url):
    """Extracts the playlist ID from a Spotify URL."""
    try:
        return playlist_url.split("/playlist/")[1].split("?")[0]
    except IndexError as e:
        raise ValueError("Invalid Spotify playlist URL") from e

def get_all_tracks(link, market):
    """Main function to retrieve all tracks."""
    playlist_id = _extract_playlist_id(link)
    client = SpotifyClient()
    return client.get_playlist_tracks(playlist_id, market)

def get_playlist_name(link):
    """Main function to retrieve the playlist name."""
    playlist_id = _extract_playlist_id(link)
    client = SpotifyClient()
    return client.get_playlist_name(playlist_id)

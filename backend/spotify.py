"""Thin Spotify Web API client used by the backend.

Notes:
- Client Credentials flow only (no user grant needed).
- Requests are executed through a Session with Retry/backoff.
- Errors are normalized into SpotifyError for the Flask layer.
"""

from __future__ import annotations

import os
from typing import List, Dict, Optional

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()


class SpotifyError(Exception):
    """Custom exception for errors related to the Spotify API."""


def _session() -> requests.Session:
    """Create a requests session with sane retry/backoff defaults."""
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


class SpotifyClient:
    """A tiny client for interacting with the Spotify Web API."""
    API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self) -> None:
        self._client_id = os.getenv("SPOTIPY_CLIENT_ID")
        self._client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        self._access_token = self._get_access_token()
        self._http = _session()

    def _get_access_token(self) -> str:
        """Fetch a bearer token using Client Credentials flow."""
        if not self._client_id or not self._client_secret:
            raise SpotifyError(
                "Missing SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET. "
                "Set them in your .env (or docker-compose env_file)."
            )
        url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        resp = _session().post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _make_request(self, url: str) -> Dict:
        """Perform an authenticated GET with auto-refresh on 401."""
        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            resp = self._http.get(url, headers=headers, timeout=10)
            if resp.status_code == 401:
                # refresh token once
                self._access_token = self._get_access_token()
                headers["Authorization"] = f"Bearer {self._access_token}"
                resp = self._http.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 404:
                raise SpotifyError(
                    "Playlist not found. Please ensure the URL is correct and the playlist is public."
                ) from e
            if status == 401:
                raise SpotifyError("Invalid Spotify credentials. Please check your .env file.") from e
            raise SpotifyError(f"Spotify API returned an error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise SpotifyError(f"Could not connect to Spotify API: {e}") from e

    def get_playlist_tracks(self, playlist_id: str, market: Optional[str] = None) -> List[Dict]:
        """Return flattened track info (name, artists, album) for a playlist."""
        url = f"{self.API_BASE_URL}/playlists/{playlist_id}/tracks?market={market}&limit=50"
        all_tracks: List[Dict] = []
        while url:
            data = self._make_request(url)
            for item in data.get("items", []):
                track = item.get("track")
                if track and track.get("name") and track.get("artists"):
                    all_tracks.append(
                        {
                            "name": track["name"],
                            "artists": [artist["name"] for artist in track.get("artists", [])],
                            "album": track.get("album", {}).get("name", "Unknown Album"),
                        }
                    )
            url = data.get("next")
        return all_tracks

    def get_playlist_name(self, playlist_id: str) -> str:
        """Resolve playlist display name."""
        url = f"{self.API_BASE_URL}/playlists/{playlist_id}"
        data = self._make_request(url)
        return data.get("name", "Unknown Playlist")


def _extract_playlist_id(playlist_url: str) -> str:
    """Extract the playlist ID from a canonical Spotify playlist URL."""
    try:
        part = playlist_url.split("/playlist/")[1]
        part = part.split("?")[0].split("/")[0]
        if not part:
            raise IndexError()
        return part
    except IndexError as e:
        raise ValueError("Invalid Spotify playlist URL") from e


def get_all_tracks(link: str, market: Optional[str]) -> List[Dict]:
    """Facade to return all playlist tracks given a full Spotify link."""
    playlist_id = _extract_playlist_id(link)
    client = SpotifyClient()
    return client.get_playlist_tracks(playlist_id, market)


def get_playlist_name(link: str) -> str:
    """Facade to return the playlist display name given a full Spotify link."""
    playlist_id = _extract_playlist_id(link)
    client = SpotifyClient()
    return client.get_playlist_name(playlist_id)

"""Spotify Web API client."""

from __future__ import annotations

import os
import time
import base64
from typing import List, Dict, Optional, Any

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
        allowed_methods=["GET", "POST", "PUT", "DELETE"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


class SpotifyClient:
    """Client for interacting with the Spotify Web API."""
    API_BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, access_token: Optional[str] = None, refresh_token: Optional[str] = None) -> None:
        self.client_id = os.getenv("SPOTIPY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._http = _session()

        if not self.access_token and self.client_id and self.client_secret:
            self._authenticate_client_credentials()

    def _authenticate_client_credentials(self) -> None:
        """Fetch a bearer token using Client Credentials flow."""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            resp = self._http.post(self.AUTH_URL, headers=headers, data=data, timeout=10)
            resp.raise_for_status()
            self.access_token = resp.json()["access_token"]
        except requests.exceptions.RequestException as e:
            raise SpotifyError(f"Failed to authenticate with Client Credentials: {e}") from e

    def _refresh_access_token(self) -> None:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
             # If we don't have a refresh token, we might be in CC flow, try that again
            if self.client_id and self.client_secret:
                self._authenticate_client_credentials()
                return
            raise SpotifyError("No refresh token available.")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic " + base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        try:
            resp = self._http.post(self.AUTH_URL, headers=headers, data=data, timeout=10)
            resp.raise_for_status()
            token_info = resp.json()
            self.access_token = token_info["access_token"]
            # Update refresh token if provided
            if "refresh_token" in token_info:
                self.refresh_token = token_info["refresh_token"]
        except requests.exceptions.RequestException as e:
            raise SpotifyError(f"Failed to refresh token: {e}") from e

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Perform an authenticated request with auto-refresh on 401."""
        url = f"{self.API_BASE_URL}{endpoint}"
        if not self.access_token:
            raise SpotifyError("No access token provided.")

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            resp = self._http.request(method, url, headers=headers, **kwargs, timeout=10)

            if resp.status_code == 401:
                self._refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                resp = self._http.request(method, url, headers=headers, **kwargs, timeout=10)

            resp.raise_for_status()
            if resp.content:
                return resp.json()
            return None
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status == 404:
                # sometimes normal for search or empty
                raise SpotifyError(f"Resource not found: {url}") from e
            raise SpotifyError(f"Spotify API error ({status}): {e}") from e
        except requests.exceptions.RequestException as e:
            raise SpotifyError(f"Connection error: {e}") from e

    def get_current_user(self) -> Dict:
        """Get detailed profile information about the current user."""
        return self._request("GET", "/me")

    def get_user_playlists(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get a list of the playlists owned or followed by the current user."""
        return self._request("GET", f"/me/playlists?limit={limit}&offset={offset}")

    def get_playlist_tracks(self, playlist_id: str, market: Optional[str] = None) -> List[Dict]:
        """Return flattened track info (name, artists, album, id, isrc, duration_ms) for a playlist."""
        market_param = f"&market={market}" if market else ""
        endpoint = f"/playlists/{playlist_id}/tracks?limit=50{market_param}"
        all_tracks: List[Dict] = []

        while endpoint:
            # We use the full URL from 'next' if it exists, or construct relative
            if endpoint.startswith("http"):
                # _request expects relative endpoint usually, but we can hack it or handle pagination better
                # Let's just strip base url if present
                if endpoint.startswith(self.API_BASE_URL):
                    endpoint = endpoint[len(self.API_BASE_URL):]

            data = self._request("GET", endpoint)
            for item in data.get("items", []):
                track = item.get("track")
                # Handle cases where track might be None (e.g. episodes)
                if track and track.get("id") and track.get("type") == "track":
                    all_tracks.append({
                        "id": track["id"],
                        "name": track["name"],
                        "artists": [artist["name"] for artist in track.get("artists", [])],
                        "album": track.get("album", {}).get("name", "Unknown Album"),
                        "duration_ms": track.get("duration_ms", 0),
                        "isrc": track.get("external_ids", {}).get("isrc"),
                        "uri": track.get("uri")
                    })

            endpoint = data.get("next")
            if endpoint and endpoint.startswith(self.API_BASE_URL):
                endpoint = endpoint[len(self.API_BASE_URL):]
            elif not endpoint:
                endpoint = None

        return all_tracks

    def get_playlist(self, playlist_id: str) -> Dict:
        """Get a playlist owned by a Spotify user."""
        return self._request("GET", f"/playlists/{playlist_id}")


def _extract_playlist_id(playlist_url: str) -> str:
    """Extract the playlist ID from a canonical Spotify playlist URL."""
    try:
        part = playlist_url.split("/playlist/")[1]
        part = part.split("?")[0].split("/")[0]
        if not part:
            raise IndexError()
        return part
    except (IndexError, AttributeError) as e:
        raise ValueError("Invalid Spotify playlist URL") from e


def get_all_tracks(link: str, market: Optional[str] = None) -> List[Dict]:
    """Facade to return all playlist tracks given a full Spotify link (uses Client Credentials)."""
    playlist_id = _extract_playlist_id(link)
    # This facade creates a fresh client which will default to Client Credentials (no user tokens)
    client = SpotifyClient()
    return client.get_playlist_tracks(playlist_id, market)


def get_playlist_name(link: str) -> str:
    """Facade to return the playlist display name given a full Spotify link."""
    playlist_id = _extract_playlist_id(link)
    client = SpotifyClient()
    data = client.get_playlist(playlist_id)
    return data.get("name", "Unknown Playlist")

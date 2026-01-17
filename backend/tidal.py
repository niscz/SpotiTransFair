"""TIDAL Web API client."""
from __future__ import annotations

import os
from typing import List, Dict, Any

import requests

class TidalError(Exception):
    pass

class TidalClient:
    API_BASE_URL = "https://api.tidal.com/v1"

    def __init__(self, access_token: str, country_code: str | None = None):
        self.access_token = access_token
        self.country_code = country_code or os.getenv("TIDAL_COUNTRY_CODE", "US")
        self._session = requests.Session()

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> Any:
        params = params or {}
        if self.country_code and "countryCode" not in params:
            params["countryCode"] = self.country_code
        url = f"{self.API_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
            # Content-Type defaults to x-www-form-urlencoded in requests if data is a dict
        }

        try:
            resp = self._session.request(method, url, headers=headers, params=params, data=data, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            msg = f"TIDAL API error: {e}"
            if e.response is not None:
                msg += f" | Body: {e.response.text}"
            raise TidalError(msg) from e
        except Exception as e:
            raise TidalError(f"TIDAL client error: {e}") from e

    def get_user_id(self) -> str:
        """Get the current user's ID from the session."""
        # /sessions endpoint typically returns the session info for the token
        data = self._request("GET", "/sessions")
        return str(data.get("userId"))

    def search_tracks(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for tracks."""
        params = {"query": query, "limit": limit, "types": "TRACKS"}
        data = self._request("GET", "/search", params=params)

        tracks = []
        if "tracks" in data and "items" in data["tracks"]:
            for item in data["tracks"]["items"]:
                tracks.append({
                    "id": str(item.get("id")),
                    "title": item.get("title"),
                    "artists": [a.get("name") for a in item.get("artists", [])],
                    "album": item.get("album", {}).get("title"),
                    "duration": item.get("duration"),
                    "isrc": item.get("isrc")
                })
        return tracks

    def create_playlist(self, user_id: str, title: str, description: str = "") -> str:
        """Create a new playlist and return its UUID."""
        data = {"title": title, "description": description}
        resp = self._request("POST", f"/users/{user_id}/playlists", data=data)
        return resp.get("uuid")

    def add_tracks(self, playlist_uuid: str, track_ids: List[str]) -> None:
        """Add tracks to a playlist. track_ids is a list of track ID strings."""
        if not track_ids:
            return

        # TIDAL allows adding multiple tracks via comma-separated string in 'trackIds'
        # Check for limits. Usually 50 or 100 is safe. We should chunk if necessary.
        chunk_size = 50
        for i in range(0, len(track_ids), chunk_size):
            chunk = track_ids[i:i + chunk_size]
            data = {
                "trackIds": ",".join(chunk),
                "toIndex": 0 # This might prepend. If we want append, we should rely on default or calc index.
                # Actually, if we omit toIndex, it usually appends.
            }
            # Remove toIndex to see if it appends by default
            del data["toIndex"]

            self._request("POST", f"/playlists/{playlist_uuid}/items", data=data)

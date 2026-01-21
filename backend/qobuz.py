"""Qobuz API client."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

QOBUZ_APP_ID = os.getenv("QOBUZ_APP_ID")
QOBUZ_BASE_URL = os.getenv("QOBUZ_BASE_URL", "https://www.qobuz.com/api.json/0.2")

class QobuzError(RuntimeError):
    """Raised for Qobuz API errors."""


def login_qobuz(email: str, password: str, *, app_id: Optional[str] = None) -> Dict[str, Any]:
    app_id = app_id or QOBUZ_APP_ID
    if not app_id:
        raise QobuzError("Missing Qobuz app id. Set QOBUZ_APP_ID.")
    if not email or not password:
        raise QobuzError("Qobuz email and password are required.")

    url = f"{QOBUZ_BASE_URL}/user/login"
    params = {
        "email": email,
        "password": password,
        "app_id": app_id,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    if "error" in payload:
        message = payload["error"].get("message", "Unknown Qobuz error")
        raise QobuzError(message)

    token = payload.get("user_auth_token") or payload.get("token")
    if not token:
        raise QobuzError("Qobuz login did not return an auth token.")

    user_id = None
    user = payload.get("user") or {}
    if isinstance(user, dict):
        user_id = user.get("id")
    user_id = user_id or payload.get("user_id")

    credentials = {
        "access_token": token,
        "app_id": app_id,
    }
    if user_id:
        credentials["user_id"] = user_id

    return credentials


class QobuzClient:
    """Minimal Qobuz API helper for playlists and search."""

    def __init__(self, *, app_id: str, user_auth_token: str):
        if not app_id:
            raise QobuzError("Qobuz app id missing.")
        if not user_auth_token:
            raise QobuzError("Qobuz user auth token missing.")
        self.app_id = app_id
        self.user_auth_token = user_auth_token

    def _request(self, endpoint: str, *, params: Optional[Dict[str, Any]] = None, method: str = "get") -> Dict[str, Any]:
        url = f"{QOBUZ_BASE_URL}/{endpoint}"
        query = params.copy() if params else {}
        query.setdefault("app_id", self.app_id)
        query.setdefault("user_auth_token", self.user_auth_token)

        if method == "post":
            resp = requests.post(url, data=query, timeout=10)
        else:
            resp = requests.get(url, params=query, timeout=10)
        resp.raise_for_status()
        payload = resp.json()

        if "error" in payload:
            message = payload["error"].get("message", "Unknown Qobuz error")
            raise QobuzError(message)
        return payload

    def search_tracks(self, query: str, *, limit: int = 10) -> List[Dict[str, Any]]:
        payload = self._request("track/search", params={"query": query, "limit": limit})
        tracks_data = payload.get("tracks")
        if not isinstance(tracks_data, dict):
            tracks_data = {}
        items = tracks_data.get("items", [])
        if not isinstance(items, list):
            items = []

        results: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            artist_name = None
            artist = item.get("artist")
            if isinstance(artist, dict):
                artist_name = artist.get("name")

            album_title = None
            album = item.get("album")
            if isinstance(album, dict):
                album_title = album.get("title")

            results.append({
                "id": str(item.get("id")),
                "title": item.get("title"),
                "artists": [artist_name] if artist_name else [],
                "duration": item.get("duration"),
                "album": album_title,
                "isrc": item.get("isrc"),
            })
        return results

    def create_playlist(self, name: str, description: str = "") -> str:
        payload = self._request(
            "playlist/create",
            params={
                "name": name,
                "description": description,
                "public": 0,
            },
            method="post",
        )
        playlist = payload.get("playlist") or payload
        playlist_id = playlist.get("id") or playlist.get("playlist_id")
        if not playlist_id:
            raise QobuzError("Failed to create Qobuz playlist.")
        return str(playlist_id)

    def add_tracks(self, playlist_id: str, track_ids: List[str]) -> None:
        if not track_ids:
            return
        track_ids_payload = ",".join(str(tid) for tid in track_ids)
        self._request(
            "playlist/addTracks",
            params={
                "playlist_id": playlist_id,
                "track_ids": track_ids_payload,
            },
            method="post",
        )

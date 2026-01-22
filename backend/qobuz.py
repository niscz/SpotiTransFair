"""Qobuz API client."""
from __future__ import annotations

import logging
import os
import time
import hashlib
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

QOBUZ_APP_ID = os.getenv("QOBUZ_APP_ID")
QOBUZ_APP_SECRET = os.getenv("QOBUZ_APP_SECRET")
QOBUZ_BASE_URL = os.getenv("QOBUZ_BASE_URL", "https://www.qobuz.com/api.json/0.2")

class QobuzError(RuntimeError):
    """Raised for Qobuz API errors."""


def _calculate_signature(endpoint: str, params: Dict[str, Any], ts: str, app_secret: str) -> str:
    """Calculates Qobuz API signature."""
    # endpoint example: "track/search" (no leading slash usually, but let's handle cleanup)
    method_name = endpoint.strip("/")

    # Sort parameters by key
    keys = sorted(params.keys())

    # Concatenate method + paramKey + paramValue + ...
    msg = method_name
    for k in keys:
        # Convert values to string
        val = str(params[k])
        msg += f"{k}{val}"

    msg += ts
    msg += app_secret

    return hashlib.md5(msg.encode("utf-8")).hexdigest()


def login_qobuz(email: str, password: str, *, app_id: Optional[str] = None, app_secret: Optional[str] = None) -> Dict[str, Any]:
    app_id = app_id or QOBUZ_APP_ID
    app_secret = app_secret or QOBUZ_APP_SECRET

    if not app_id:
        raise QobuzError("Missing Qobuz app id. Set QOBUZ_APP_ID.")
    if not email or not password:
        raise QobuzError("Qobuz email and password are required.")

    endpoint = "user/login"
    url = f"{QOBUZ_BASE_URL}/{endpoint}"

    params = {
        "email": email,
        "password": password,
        "app_id": app_id,
    }

    if app_secret:
        ts = str(int(time.time()))
        params["request_ts"] = ts
        params["request_sig"] = _calculate_signature(endpoint, params, ts, app_secret)

    resp = None
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as e:
        logger.error(f"Qobuz login failed: {e}")
        try:
             if resp is not None:
                err_payload = resp.json()
                if "error" in err_payload:
                    raise QobuzError(err_payload["error"].get("message"))
        except:
            pass
        raise QobuzError("Qobuz login request failed.")

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
    # Persist secret if used, so we can sign future requests
    if app_secret:
        credentials["app_secret"] = app_secret

    if user_id:
        credentials["user_id"] = user_id

    return credentials


class QobuzClient:
    """Minimal Qobuz API helper for playlists and search."""

    def __init__(self, *, app_id: str, user_auth_token: str, app_secret: Optional[str] = None):
        if not app_id:
            raise QobuzError("Qobuz app id missing.")
        if not user_auth_token:
            raise QobuzError("Qobuz user auth token missing.")
        self.app_id = app_id
        self.user_auth_token = user_auth_token
        self.app_secret = app_secret

    def _request(self, endpoint: str, *, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, method: str = "get") -> Dict[str, Any]:
        url = f"{QOBUZ_BASE_URL}/{endpoint}"
        query = params.copy() if params else {}

        # Add auth params to query
        query.setdefault("app_id", self.app_id)
        query.setdefault("user_auth_token", self.user_auth_token)

        # Calculate signature if secret is present
        if self.app_secret:
            ts = str(int(time.time()))
            query["request_ts"] = ts

            # Signature includes params AND data (if any)
            sig_params = query.copy()
            if data:
                sig_params.update(data)

            query["request_sig"] = _calculate_signature(endpoint, sig_params, ts, self.app_secret)

        resp = None
        try:
            if method.lower() == "post":
                resp = requests.post(url, params=query, data=data, timeout=20)
            else:
                resp = requests.get(url, params=query, timeout=20)

            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as e:
            logger.error(f"Qobuz request failed: {e} | {endpoint}")
            try:
                if resp is not None:
                    err_payload = resp.json()
                    if "error" in err_payload:
                        raise QobuzError(err_payload["error"].get("message"))
            except:
                pass
            raise QobuzError(f"Qobuz API request failed: {endpoint}")

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

            # Artist handling
            artists_list = []

            # Main artist
            artist = item.get("artist")
            if isinstance(artist, dict):
                name = artist.get("name")
                if name:
                    artists_list.append(name)

            # Additional artists/performers?
            if "artists" in item and isinstance(item["artists"], list):
                for a in item["artists"]:
                    if isinstance(a, dict) and a.get("name") and a.get("name") not in artists_list:
                         artists_list.append(a.get("name"))

            album_title = None
            album = item.get("album")
            if isinstance(album, dict):
                album_title = album.get("title")

            results.append({
                "id": str(item.get("id")),
                "title": item.get("title"),
                "artists": artists_list,
                "duration": item.get("duration"), # Seconds
                "album": album_title,
                "isrc": item.get("isrc"),
            })
        return results

    def create_playlist(self, name: str, description: str = "") -> str:
        # Note: 'name' is required.
        data = {
            "name": name,
            "description": description or "",
            "public": 0,
        }
        payload = self._request(
            "playlist/create",
            data=data,
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

        # Qobuz API limit per request is often 50.
        batch_size = 50
        for i in range(0, len(track_ids), batch_size):
            chunk = track_ids[i:i + batch_size]
            track_ids_payload = ",".join(str(tid) for tid in chunk)

            self._request(
                "playlist/addTracks",
                params={"playlist_id": playlist_id},
                data={"track_ids": track_ids_payload},
                method="post",
            )
            time.sleep(0.2)

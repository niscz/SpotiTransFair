"""SpotiTransFair backend Flask application.

This module exposes HTTP endpoints for:
- validating YouTube Music auth headers,
- previewing Spotify playlists,
- creating/updating YT Music playlists from Spotify,
- lightweight search/add helpers for YT Music,
- basic aggregate stats persisted on disk.

All user-facing strings are kept concise. Internal comments/docstrings are in English.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import fcntl
import ipaddress
from typing import Any, Dict, Union, cast
from geoip2.database import Reader as GeoIPReader
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from asgiref.wsgi import WsgiToAsgi

from ytm import (
    create_ytm_playlist,
    validate_headers,
    YTMError,
    search_tracks,
    add_single_video_to_playlist,
)
from spotify import get_all_tracks, get_playlist_name, SpotifyError

load_dotenv()

wsgi_app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CORS(
    wsgi_app,
    resources={
        r"/*": {
            "origins": [os.getenv("FRONTEND_URL", "http://localhost:5173")],
            "methods": ["POST", "GET", "OPTIONS"],
        }
    },
)

DEFAULT_MARKET = os.getenv("DEFAULT_SPOTIFY_MARKET", "US")
GEOIP_DB = os.getenv("GEOIP_DB")
STATS_FILE = os.getenv("STATS_FILE", "/data/stats.json")
pathlib.Path(STATS_FILE).parent.mkdir(parents=True, exist_ok=True)


def _json() -> Dict[str, Any]:
    """Return JSON body or an empty dict if parsing fails."""
    return request.get_json(silent=True) or {}


def _ok(payload: Dict[str, Any], status: int = 200):
    """Return a JSON success response."""
    return jsonify(payload), status


def _error(code: str, message: str, status: int):
    """Return a JSON error envelope compatible with the UI."""
    return jsonify({"error": {"code": code, "message": message}}), status


def _stats_read() -> Dict[str, int]:
    """Read aggregate stats, handling first-run and partial file content gracefully."""
    try:
        with open(STATS_FILE, "a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            f.seek(0)
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return {
            "playlists": int(data.get("playlists", 0)),
            "songs": int(data.get("songs", 0)),
        }
    except FileNotFoundError:
        return {"playlists": 0, "songs": 0}


def _stats_bump(add_playlists: int = 0, add_songs: int = 0) -> Dict[str, int]:
    """Atomically bump aggregate stats with file locking."""
    with open(STATS_FILE, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
        data["playlists"] = int(data.get("playlists", 0)) + int(add_playlists)
        data["songs"] = int(data.get("songs", 0)) + int(add_songs)
        f.seek(0)
        f.truncate()
        json.dump(data, f)
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)
    return {"playlists": int(data["playlists"]), "songs": int(data["songs"])}

def _client_ip() -> str:
    """Ermittle die (wahrscheinlich) echte Client-IP unter Berücksichtigung von Proxy-Headern."""

    xff = request.headers.get("X-Forwarded-For", "")
    if xff:

        ip = [p.strip() for p in xff.split(",") if p.strip()][0]
    else:
        ip = request.headers.get("X-Real-IP", request.remote_addr or "")

    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
            return ""
    except ValueError:
        return ""
    return ip

def _guess_from_accept_language(h: str) -> str | None:
    """
    Nimmt den ersten Sprachbereich aus Accept-Language.
    Wenn Region vorhanden (de-DE), nutze Region (DE).
    Ohne Region (z.B. 'en') nutze heuristische Defaults.
    """
    if not h:
        return None
    first = h.split(",")[0].strip().lower()
    parts = first.split(";")[0].split("-")
    if len(parts) >= 2 and len(parts[1]) == 2:
        return parts[1].upper()
    lang = parts[0]
    fallback = {
        "en": "US",
        "de": "DE",
        "fr": "FR",
        "it": "IT",
        "es": "ES",
        "pt": "BR",
        "nl": "NL",
        "sv": "SE",
        "pl": "PL",
        "ja": "JP",
        "ko": "KR",
        "tr": "TR",
        "ru": "RU",
        "ar": "AE",
        "zh": "SG",
        "cs": "CZ",
        "da": "DK",
        "fi": "FI",
        "el": "GR",
        "hu": "HU",
        "no": "NO",
        "ro": "RO",
        "sk": "SK",
    }
    return fallback.get(lang)

def _guess_from_timezone(tz: str | None) -> str | None:
    """
    Very-light Mapping von verbreiteten IANA-Zeitzonen zur ISO-2 Country.
    Kein perfekter Ersatz für GeoIP; bewusst klein gehalten.
    """
    if not tz:
        return None
    tz = tz.strip()
    simple = {

        "Europe/Berlin": "DE", "Europe/Vienna": "AT", "Europe/Zurich": "CH",
        "Europe/Paris": "FR", "Europe/Rome": "IT", "Europe/Madrid": "ES",
        "Europe/Amsterdam": "NL", "Europe/Stockholm": "SE", "Europe/Warsaw": "PL",
        "Europe/Dublin": "IE", "Europe/London": "GB",

        "America/New_York": "US", "America/Chicago": "US", "America/Denver": "US", "America/Los_Angeles": "US",
        "America/Toronto": "CA", "America/Vancouver": "CA",
        "America/Sao_Paulo": "BR", "America/Argentina/Buenos_Aires": "AR",
        "America/Mexico_City": "MX", "America/Bogota": "CO", "America/Santiago": "CL",

        "Asia/Tokyo": "JP", "Asia/Seoul": "KR", "Asia/Kolkata": "IN",
        "Asia/Jakarta": "ID", "Asia/Singapore": "SG", "Asia/Bangkok": "TH",
        "Asia/Kuala_Lumpur": "MY", "Asia/Ho_Chi_Minh": "VN", "Asia/Manila": "PH",
        "Australia/Sydney": "AU", "Pacific/Auckland": "NZ",

        "Asia/Dubai": "AE", "Asia/Riyadh": "SA", "Africa/Johannesburg": "ZA",
        "Europe/Istanbul": "TR",
    }
    return simple.get(tz)

def _guess_from_geoip(ip: str) -> str | None:
    """Liefert ISO-2 Country via lokaler MaxMind-DB zurück (ohne externe Anfrage)."""
    if not (ip and GEOIP_DB and os.path.exists(GEOIP_DB)):
        return None
    try:
        with GeoIPReader(GEOIP_DB) as reader:
            resp = reader.country(ip)
            return (resp.country.iso_code or "").upper() or None
    except Exception:
        return None

@wsgi_app.route("/market/guess", methods=["GET"])
def market_guess():
    """Best-effort Market-Vorschlag (privacy-aware, offline)."""
    tz = request.args.get("tz")
    accept_lang = request.headers.get("Accept-Language", "")
    ip = _client_ip()

    guesses = []
    tz_cc = _guess_from_timezone(tz)
    if tz_cc:
        guesses.append({"method": "timezone", "market": tz_cc, "confidence": 0.75})

    al_cc = _guess_from_accept_language(accept_lang)
    if al_cc:
        guesses.append({"method": "accept-language", "market": al_cc, "confidence": 0.70})

    gi_cc = _guess_from_geoip(ip)
    if gi_cc:
        guesses.insert(0, {"method": "geoip", "market": gi_cc, "confidence": 0.9})

    market = (guesses[0]["market"] if guesses else DEFAULT_MARKET)
    return _ok({"market": market, "guesses": guesses, "default": DEFAULT_MARKET})

@wsgi_app.route("/", methods=["GET"])
def home():
    """Health endpoint."""
    return _ok({"message": "Server Online"})


@wsgi_app.route("/validate-headers", methods=["POST"])
def route_validate_headers():
    """Validate raw YT Music auth headers (string or key/value object)."""
    data = _json()
    headers_any: Any = data.get("auth_headers", None)

    if headers_any is None:
        return _error("BAD_REQUEST", "Field 'auth_headers' missing.", 400)

    if not isinstance(headers_any, (str, dict)):
        return _error(
            "BAD_REQUEST",
            "Field 'auth_headers' must be a string (raw headers) or an object map.",
            400,
        )

    headers_raw = cast(Union[str, Dict[str, str]], headers_any)
    ok, msg = validate_headers(headers_raw)
    if ok:
        return _ok({"valid": True, "message": msg})
    return _error("YTM_AUTH_INVALID", msg, 422)


@wsgi_app.route("/spotify/preview", methods=["GET"])
def spotify_preview():
    """Return playlist name and track count to allow a UI preview before cloning."""
    playlist_link = request.args.get("playlist_link")
    market = request.args.get("market", DEFAULT_MARKET)

    if not playlist_link:
        return _error("BAD_REQUEST", "Query param 'playlist_link' is required.", 400)

    try:
        tracks = get_all_tracks(playlist_link, market)
        name = get_playlist_name(playlist_link)
        return _ok({"name": name, "track_count": len(tracks)})
    except SpotifyError as exc:
        logging.warning("Spotify error: %s", exc)
        return _error("SPOTIFY_ERROR", str(exc), 422)
    except ValueError as exc:
        logging.warning("Bad playlist link: %s", exc)
        return _error("BAD_REQUEST", str(exc), 400)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logging.exception("Unhandled error in /spotify/preview: %s", exc)
        return _error(
            "INTERNAL",
            "An internal server error occurred. Please try again later.",
            500,
        )


@wsgi_app.route("/create", methods=["POST"])
def create_playlist():
    """Create a new or update an existing YT Music playlist based on a Spotify playlist."""
    data = _json()
    playlist_link = data.get("playlist_link")
    auth_headers = data.get("auth_headers")
    market = data.get("market", DEFAULT_MARKET)
    privacy_status = data.get("privacy_status", "PRIVATE")
    title_override = data.get("title_override")
    dry_run = bool(data.get("dry_run", False))
    target_playlist_id = data.get("target_playlist_id")

    if not playlist_link or not auth_headers:
        return _error(
            "BAD_REQUEST",
            "Fields 'playlist_link' and 'auth_headers' are required.",
            400,
        )

    try:
        playlist_id, missed = create_ytm_playlist(
            playlist_link,
            auth_headers,
            market=market,
            privacy_status=privacy_status,
            title_override=title_override,
            dry_run=dry_run,
            target_playlist_id=target_playlist_id,
        )

        message = (
            "Dry run successful."
            if dry_run
            else (
                "Playlist updated successfully!"
                if target_playlist_id
                else "Playlist created successfully!"
            )
        )

        resp: Dict[str, Any] = {"message": message, "missed_tracks": missed}

        if not dry_run and playlist_id:
            resp["playlist_id"] = playlist_id
            resp["playlist_url"] = f"https://music.youtube.com/playlist?list={playlist_id}"

            inserted = int((missed or {}).get("_stats", {}).get("inserted", 0))
            # Only bump "playlists" on creation; always bump "songs" by inserted
            if not target_playlist_id:
                _stats_bump(add_playlists=1, add_songs=inserted)
            else:
                _stats_bump(add_playlists=0, add_songs=inserted)

        return _ok(resp)

    except SpotifyError as exc:
        logging.warning("Spotify API error: %s", exc)
        return _error("SPOTIFY_ERROR", str(exc), 422)
    except YTMError as exc:
        logging.warning("YTM error: %s", exc)
        return _error("YTM_ERROR", str(exc), 422)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logging.exception("Unhandled error in /create: %s", exc)
        return _error(
            "INTERNAL",
            "An internal server error occurred. Please try again later.",
            500,
        )


@wsgi_app.route("/ytm/search", methods=["POST"])
def ytm_search():
    """Search YouTube Music; allows filter and top_k for UI suggestions."""
    # Body: { "query": "...", "auth_headers": "...", "filter": "songs|videos|uploads", "top_k": 5 }
    # Returns: { "results": [ { "videoId": "...", "title": "...", "artists": [ ... ] }, ... ] }
    data = _json()
    query = data.get("query")
    auth_headers = data.get("auth_headers")
    filt = data.get("filter", "songs")
    top_k = int(data.get("top_k", 5))

    if not query or not auth_headers:
        return _error("BAD_REQUEST", "Fields 'query' and 'auth_headers' are required.", 400)

    try:
        # positional args to avoid keyword compatibility issues across versions
        results = results = search_tracks(query, auth_headers, filt=filt, top_k=top_k)
        return _ok({"results": results})
    except YTMError as exc:
        logging.warning("YTM error in search: %s", exc)
        return _error("YTM_ERROR", str(exc), 422)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logging.exception("Unhandled error in /ytm/search: %s", exc)
        return _error("INTERNAL", "An internal server error occurred.", 500)


@wsgi_app.route("/ytm/add", methods=["POST"])
def ytm_add():
    """Add a single video to an existing YT Music playlist."""
    # Body: { "playlist_id": "...", "video_id": "...", "auth_headers": "..." }
    data = _json()
    pid = data.get("playlist_id")
    vid = data.get("video_id")
    headers = data.get("auth_headers")

    if not (pid and vid and headers):
        return _error(
            "BAD_REQUEST",
            "Fields 'playlist_id','video_id','auth_headers' are required.",
            400,
        )
    try:
        ok = add_single_video_to_playlist(pid, vid, headers)
        return _ok({"ok": bool(ok)})
    except YTMError as exc:
        logging.warning("YTM error in add: %s", exc)
        return _error("YTM_ERROR", str(exc), 422)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logging.exception("Unhandled error in /ytm/add: %s", exc)
        return _error("INTERNAL", "An internal server error occurred.", 500)


@wsgi_app.route("/stats", methods=["GET"])
def stats():
    """Return aggregate counters."""
    return _ok(_stats_read())


app = WsgiToAsgi(wsgi_app)

if __name__ == "__main__":
    wsgi_app.run(port=8001)

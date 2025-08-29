"""
Main application file for the Flask server.
"""
import os
import logging
from typing import Any, Dict, Union
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from asgiref.wsgi import WsgiToAsgi
from ytm import create_ytm_playlist, validate_headers, YTMError
from spotify import get_all_tracks, get_playlist_name, SpotifyError

load_dotenv()

# Step 1: Create the normal Flask WSGI app
wsgi_app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CORS(wsgi_app, resources={
    r"/*": {
        "origins": [os.getenv('FRONTEND_URL', 'http://localhost:5173')],
        "methods": ["POST", "GET"],
    }
})

DEFAULT_MARKET = os.getenv("DEFAULT_SPOTIFY_MARKET", "US")

def _json():
    return request.get_json(silent=True) or {}


def _ok(payload: Dict[str, Any], status=200):
    return jsonify(payload), status


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


@wsgi_app.route('/', methods=['GET'])
def home():
    return _ok({"message": "Server Online"})


@wsgi_app.route('/validate-headers', methods=['POST'])
def route_validate_headers():
    data = _json()
    headers_raw: Union[str, Dict[str, str]] = data.get('auth_headers')
    if not headers_raw:
        return _error("BAD_REQUEST", "Field 'auth_headers' missing.", 400)

    ok, msg = validate_headers(headers_raw)
    if ok:
        return _ok({"valid": True, "message": msg})
    return _error("YTM_AUTH_INVALID", msg, 422)


@wsgi_app.route('/spotify/preview', methods=['GET'])
def spotify_preview():
    playlist_link = request.args.get('playlist_link')
    market = request.args.get('market', DEFAULT_MARKET)

    if not playlist_link:
        return _error("BAD_REQUEST", "Query param 'playlist_link' is required.", 400)

    try:
        tracks = get_all_tracks(playlist_link, market)
        name = get_playlist_name(playlist_link)
        return _ok({"name": name, "track_count": len(tracks)})
    except SpotifyError as e:
        logging.warning("Spotify error: %s", e)
        return _error("SPOTIFY_ERROR", str(e), 422)
    except Exception:
        logging.exception("Unhandled error in /spotify/preview")
        return _error("INTERNAL", "An internal server error occurred. Please try again later.", 500)

@wsgi_app.route('/create', methods=['POST'])
def create_playlist():
    """
    Body:
    {
        "playlist_link": "...",                     (required)
        "auth_headers": "<raw string | dict>",      (required)
        "market": "US" | "...",                     (optional, default=US)
        "privacy_status": "PRIVATE"|"PUBLIC"|...,   (optional, default=PRIVATE)
        "title_override": "My Title",               (optional)
        "dry_run": true|false                       (optional, default=false)
    }
    """
    data = _json()
    playlist_link = data.get('playlist_link')
    auth_headers = data.get('auth_headers')
    market = data.get('market', DEFAULT_MARKET)
    privacy_status = data.get('privacy_status', "PRIVATE")
    title_override = data.get('title_override')
    dry_run = bool(data.get('dry_run', False))

    if not playlist_link or not auth_headers:
        return _error("BAD_REQUEST", "Fields 'playlist_link' and 'auth_headers' are required.", 400)

    try:
        playlist_id, missed_tracks = create_ytm_playlist(
            playlist_link,
            auth_headers,
            market=market,
            privacy_status=privacy_status,
            title_override=title_override,
            dry_run=dry_run
        )

        resp = {
            "message": "Dry run successful." if dry_run else "Playlist created successfully!",
            "missed_tracks": missed_tracks
        }
        if not dry_run and playlist_id:
            resp["playlist_id"] = playlist_id
            resp["playlist_url"] = f"https://music.youtube.com/playlist?list={playlist_id}"

        return _ok(resp, 200)

    except SpotifyError as e:
        logging.warning("Spotify API error: %s", e)
        return _error("SPOTIFY_ERROR", str(e), 422)

    except YTMError as e:
        logging.warning("YTM error: %s", e)
        return _error("YTM_ERROR", str(e), 422)

    except Exception:
        logging.exception("Unhandled error in /create")
        return _error("INTERNAL", "An internal server error occurred. Please try again later.", 500)


# ASGI wrapper for Gunicorn Uvicorn worker
app = WsgiToAsgi(wsgi_app)

if __name__ == '__main__':
    wsgi_app.run(port=8001)

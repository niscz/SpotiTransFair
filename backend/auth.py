import os
import base64
import requests
from urllib.parse import urlencode
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
# Defaults if not set, though they should be set
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:3000/callback/spotify")

TIDAL_CLIENT_ID = os.getenv("TIDAL_CLIENT_ID")
TIDAL_CLIENT_SECRET = os.getenv("TIDAL_CLIENT_SECRET")
TIDAL_REDIRECT_URI = os.getenv("TIDAL_REDIRECT_URI", "http://localhost:3000/callback/tidal")

def get_spotify_auth_url(state: str) -> str:
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "state": state,
        "scope": "user-read-private playlist-read-private playlist-read-collaborative"
    }
    return "https://accounts.spotify.com/authorize?" + urlencode(params)

def get_tidal_auth_url(state: str) -> str:
    params = {
        "client_id": TIDAL_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": TIDAL_REDIRECT_URI,
        "state": state,
        "scope": "r_usr w_usr"
    }
    return "https://login.tidal.com/authorize?" + urlencode(params)

def exchange_spotify_code(code: str) -> Dict[str, Any]:
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI
    }
    resp = requests.post(url, headers=headers, data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()

def exchange_tidal_code(code: str) -> Dict[str, Any]:
    url = "https://auth.tidal.com/v1/oauth2/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{TIDAL_CLIENT_ID}:{TIDAL_CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": TIDAL_REDIRECT_URI
    }
    resp = requests.post(url, headers=headers, data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()

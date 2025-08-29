"""
This module handles the interaction with the YouTube Music API.
"""
import concurrent.futures
import tempfile
import os
import ytmusicapi
from typing import Tuple, Dict, Any, Union
from requests.exceptions import RequestException
from spotify import get_all_tracks, get_playlist_name, SpotifyError

BATCH_SIZE = 100

class YTMError(Exception):
    """Custom exception for errors related to YouTube Music processing."""

def _headers_to_raw(headers_input: Union[str, Dict[str, str]]) -> str:
    """Accept dict or raw string and normalize to the 'headers_raw' format expected by ytmusicapi.setup."""
    if isinstance(headers_input, str):
        return headers_input
    if isinstance(headers_input, dict):
        # Convert {"cookie": "...", "user-agent": "..."} to:
        # "cookie: ...\nuser-agent: ..."
        return "\n".join(f"{k}: {v}" for k, v in headers_input.items())
    raise YTMError("Invalid headers format. Must be raw string or key/value dict.")

def search_track(ytmusic, track):
    """Searches for a single track on YouTube Music and returns its video ID or None."""
    q_title = track["name"].lower()
    q_artist = track["artists"][0].lower()
    try:
        search_results = ytmusic.search(f"{track['name']} {track['artists'][0]}", filter="songs") or []
        for r in search_results[:5]:
            title = (r.get("title") or "").lower()
            artists = " ".join(a.get("name","") for a in r.get("artists", [])).lower()
            if q_title in title and (q_artist in artists or artists in q_artist):
                return r.get("videoId")
        # fallback to first result if anything exists
        return (search_results[0].get("videoId") if search_results else None)
    except RequestException as e:
        print(f"Network error while searching for '{q_artist} - {q_title}': {e}")
    except IndexError:
        print(f"No results found for '{q_artist} - {q_title}' on YouTube Music.")
    except Exception as e:
        print(f"Generic error while searching for '{q_artist} - {q_title}': {e}")
    return None


def get_video_ids(ytmusic, tracks):
    """Searches for tracks on YouTube Music in parallel and returns their video IDs."""
    video_ids = []
    missed_tracks = {"count": 0, "tracks": []}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_track = {executor.submit(search_track, ytmusic, track): track for track in tracks}
        for future in concurrent.futures.as_completed(future_to_track):
            track = future_to_track[future]
            try:
                video_id = future.result()
                if video_id:
                    video_ids.append(video_id)
                else:
                    missed_tracks["count"] += 1
                    missed_tracks["tracks"].append(f"{track['name']} - {track['artists'][0]}")
            except Exception as e:
                print(f"An executor exception occurred for track {track['name']}: {e}")
                missed_tracks["count"] += 1
                missed_tracks["tracks"].append(f"{track['name']} - {track['artists'][0]}")

    print(f"Found {len(video_ids)} of {len(tracks)} tracks on YouTube Music.")
    if not video_ids and tracks:
        raise YTMError("Not a single track could be found on YouTube Music. Are your authentication headers correct and valid?")
    return video_ids, missed_tracks


def validate_headers(headers_raw: Union[str, Dict[str, str]]) -> Tuple[bool, str]:
    """Lightweight check to see if YTM headers are usable."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    try:
        ytmusicapi.setup(filepath=temp_file.name, headers_raw=_headers_to_raw(headers_raw))
        ytmusic = ytmusicapi.YTMusic(temp_file.name)
        # small/auth-only call
        _ = ytmusic.get_library_playlists(limit=1)
        return True, "Headers valid."
    except Exception as e:
        return False, f"Headers invalid or expired: {str(e)}"
    finally:
        temp_file.close()
        os.unlink(temp_file.name)


def create_ytm_playlist(
    playlist_link: str,
    headers_raw: Union[str, Dict[str, str]],
    *,
    market: str = "US",
    privacy_status: str = "PRIVATE",
    title_override: str | None = None,
    dry_run: bool = False,
) -> Tuple[str | None, Dict[str, Any]]:
    """
    Creates a YouTube Music playlist from a Spotify playlist link.

    Returns (playlist_id or None if dry_run, missed_tracks dict).
    """
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')

    try:
        ytmusicapi.setup(filepath=temp_file.name, headers_raw=_headers_to_raw(headers_raw))
        ytmusic = ytmusicapi.YTMusic(temp_file.name)

        tracks = get_all_tracks(playlist_link, market)
        name = title_override or get_playlist_name(playlist_link)
        video_ids, missed_tracks = get_video_ids(ytmusic, tracks)

        if dry_run:
            # report only
            return None, missed_tracks

        # 1) Create Empty/Initial-Playlist
        playlist_id = ytmusic.create_playlist(
            title=name,
            description="Created with SpotiTransFair",
            privacy_status=privacy_status
        )

        # 2) Add Items in Batches
        for i in range(0, len(video_ids), BATCH_SIZE):
            ytmusic.add_playlist_items(playlist_id, video_ids[i:i + BATCH_SIZE])

        return playlist_id, missed_tracks
    finally:
        temp_file.close()
        os.unlink(temp_file.name)

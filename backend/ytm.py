"""
This module handles the interaction with the YouTube Music API.
"""
import concurrent.futures
import tempfile
import os
import logging
import time
from typing import Tuple, Dict, Any, Union, List
import requests
import ytmusicapi
from ytmusicapi.exceptions import YTMusicServerError
from requests.exceptions import RequestException
from spotify import get_all_tracks, get_playlist_name

YTM_EDIT_URL = "https://music.youtube.com/youtubei/v1/playlist/edit?prettyPrint=false"
YTM_BATCH_SIZE = int(os.getenv("YTM_BATCH_SIZE", "60"))
YTM_SLEEP_SECS = float(os.getenv("YTM_SLEEP_SECS", "0.3"))
YTM_POST_CREATE_SLEEP = float(os.getenv("YTM_POST_CREATE_SLEEP", "1.0"))

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

def _existing_video_ids(ytmusic, playlist_id: str) -> set[str]:
    try:
        pl = ytmusic.get_playlist(playlist_id, limit=100000)
        return {t.get("videoId") for t in (pl.get("tracks") or []) if t.get("videoId")}
    except Exception as e:
        logging.warning("Could not fetch existing items for playlist %s: %s", playlist_id, e)
        return set()

def _add_tracks_resilient(ytmusic, playlist_id: str, video_ids: list[str]) -> list[str]:
    """Fügt video_ids robust hinzu: dedupe gegen bestehende, bei Fehlern Split/Retry bis Einzelstück.
    Gibt Liste der endgültig gescheiterten videoIds zurück."""
    failed: list[str] = []
    existing = _existing_video_ids(ytmusic, playlist_id)

    def add_chunk(chunk: list[str]) -> None:
        nonlocal existing, failed
        # Gegen bereits enthaltene Titel deduplizieren
        filtered = [v for v in chunk if v and v not in existing]
        if not filtered:
            return

        try:
            res = ytmusic.add_playlist_items(playlist_id, filtered, duplicates=True)
            ok = not isinstance(res, dict) or res.get("status") in (None, "STATUS_SUCCEEDED")
            if ok:
                existing.update(filtered)
                logging.info("Inserted %d items", len(filtered))
                return
            logging.error("Add returned non-success: %s", str(res)[:300])
        except YTMusicServerError as e:
            # 409 → split & retry
            if "409" in str(e):
                logging.warning("409 on %d items, will split and retry", len(filtered))
            else:
                logging.exception("YTMusicServerError on %d items: %s", len(filtered), e)
        except Exception as e:
            logging.exception("Unexpected error adding %d items: %s", len(filtered), e)

        if len(filtered) == 1:
            failed.extend(filtered)
            return
        mid = len(filtered) // 2
        add_chunk(filtered[:mid]); time.sleep(YTM_SLEEP_SECS)
        add_chunk(filtered[mid:]); time.sleep(YTM_SLEEP_SECS)

    total = len(video_ids)
    logging.info("Adding %d tracks to playlist %s in chunks of %d", total, playlist_id, YTM_BATCH_SIZE)
    for start in range(0, total, YTM_BATCH_SIZE):
        add_chunk(video_ids[start:start + YTM_BATCH_SIZE])
        time.sleep(YTM_SLEEP_SECS)
    return failed

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

def _ytm_context(client_version: str = "1.20250827.05.00", hl="de", gl="DE"):
    return {
        "context": {
            "client": {
                "clientName": "WEB_REMIX",
                "clientVersion": client_version,
                "hl": hl,
                "gl": gl,
            }
        }
    }

def add_tracks_to_playlist(playlist_id: str, video_ids: list[str], headers: dict, client_version="1.20250827.05.00"):
    """Fügt video_ids in Batches zu playlist_id hinzu. Gibt (ok_count, failed_ids) zurück."""
    ok = 0
    failed: list[str] = []

    # Unverzichtbare Header sicherstellen
    h = {
        "origin": headers.get("origin", "https://music.youtube.com"),
        "referer": headers.get("referer", "https://music.youtube.com/"),
        "authorization": headers["authorization"],  # SAPISIDHASH ...
        "cookie": headers["cookie"],
        "x-youtube-client-name": headers.get("x-youtube-client-name", "67"),
        "x-youtube-client-version": headers.get("x-youtube-client-version", client_version),
        "content-type": "application/json",
    }
    # Nice-to-have (falls vorhanden)
    for k in ("x-goog-visitor-id", "x-goog-authuser", "x-youtube-identity-token"):
        if k in headers:
            h[k] = headers[k]

    def chunks(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i:i+n]

    for chunk in chunks(video_ids, YTM_BATCH_SIZE):
        payload = _ytm_context(client_version)
        payload["actions"] = [
            {"addToPlaylistCommand": {"playlistId": playlist_id, "videoId": vid}}
            for vid in chunk
        ]

        r = requests.post(YTM_EDIT_URL, headers=h, json=payload, timeout=30)
        if r.status_code != 200:
            logging.error("YTM edit failed: status=%s body=%s", r.status_code, r.text[:500])
            failed.extend(chunk)
            # kleine Pause und weiter, nicht hart abbrechen
            time.sleep(0.5)
            continue

        # Optional: Response prüfen, ob Aktionen acked wurden
        ok += len(chunk)
        time.sleep(0.15)  # Rate-Limit nicht reizen

    return ok, failed

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

        # ---- Duplikate erkennen (gleiche videoId mehrmals) und melden
        def _fmt_track(t: Dict[str, Any]) -> str:
            # robuste Extraktion
            artist = (
                t.get("artist")
                or (t.get("artists") or [{}])[0].get("name")
                or t.get("artists_str")
                or "Unknown Artist"
            )
            album = (
                t.get("album")
                or t.get("album_name")
                or (t.get("albumObj") or {}).get("name")
                or ""
            )
            title = t.get("title") or t.get("name") or t.get("track") or "Unknown Title"
            return f"{artist} (-{album}) - {title}" if album else f"{artist} - {title}"

        first_seen: Dict[str, int] = {}
        unique_video_ids: List[str] = []
        duplicate_lines: List[str] = []
        for idx, vid in enumerate(video_ids):
            if vid in first_seen:
                # diesen Track (zweiter Treffer) als Duplikat melden
                try:
                    duplicate_lines.append(_fmt_track(tracks[idx]))
                except Exception:
                    duplicate_lines.append(f"[duplicate videoId={vid}]")
            else:
                first_seen[vid] = idx
                unique_video_ids.append(vid)

        dup_count = len(video_ids) - len(unique_video_ids)
        if dup_count:
            logging.info("Found %d duplicate(s) → will skip them.", dup_count)
        # in die Missed-Struktur aufnehmen (neues Feld)
        missed_tracks = missed_tracks or {}
        missed_tracks["duplicates"] = {
            "count": dup_count,
            "lines": duplicate_lines,
        }

        # wir fügen nur die eindeutigen ein
        video_ids = unique_video_ids

        if dry_run:
            return None, missed_tracks

        # 1) Create Empty/Initial-Playlist
        playlist_id = ytmusic.create_playlist(
            title=name,
            description="Created with SpotiTransFair",
            privacy_status=privacy_status
        )

        # 2) Add Items in Batches (mit Logging & Fehleraufsammlung)
        time.sleep(YTM_POST_CREATE_SLEEP)

        failed_inserts = _add_tracks_resilient(ytmusic, playlist_id, video_ids)

        if failed_inserts:
            logging.warning("Insert failed for %d/%d tracks", len(failed_inserts), len(video_ids))
            missed_tracks = {
                "count": missed_tracks.get("count", 0) + len(failed_inserts),
                "tracks": missed_tracks.get("tracks", []) + [
                    {"videoId": vid, "reason": "insert_failed"} for vid in failed_inserts
                ],
            }

        return playlist_id, missed_tracks

    finally:
        temp_file.close()
        os.unlink(temp_file.name)

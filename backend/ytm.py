"""YouTube Music glue logic.

Responsibilities:
- Validate raw auth headers via ytmusicapi bootstrap.
- Token-bucket rate limiting shared within the process.
- Parallelized track search with heuristics and stable ordering.
- Resilient batched insert with split/retry and de-duplication.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import re
import tempfile
import time
from typing import Tuple, Dict, Any, Union, List, Optional, Set

import ytmusicapi
from ytmusicapi.exceptions import YTMusicServerError
from spotify import get_all_tracks, get_playlist_name

YTM_BATCH_SIZE = int(os.getenv("YTM_BATCH_SIZE", "60"))
YTM_SLEEP_SECS = float(os.getenv("YTM_SLEEP_SECS", "0.3"))
YTM_POST_CREATE_SLEEP = float(os.getenv("YTM_POST_CREATE_SLEEP", "1.0"))
YTM_SEARCH_WORKERS = int(os.getenv("YTM_SEARCH_WORKERS", "8"))
YTM_QPS = float(os.getenv("YTM_QPS", "5"))


class YTMError(Exception):
    """Custom exception for errors related to YouTube Music processing."""


# -------- Rate Limiter (simple token bucket, per process) ----------
class _TokenBucket:
    """Simple token-bucket limiter to keep requests per second under control."""

    def __init__(self, rate_per_sec: float, capacity: Optional[int] = None) -> None:
        self.rate = max(rate_per_sec, 0.1)
        self.capacity = int(capacity if capacity is not None else max(self.rate * 2, 1))
        self.tokens = self.capacity
        self.last = time.monotonic()

    def acquire(self) -> None:
        """Block until a token can be consumed."""
        now = time.monotonic()
        elapsed = now - self.last
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens < 1:
            needed = (1 - self.tokens) / self.rate
            if needed > 0:
                time.sleep(needed)
            now2 = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now2 - now) * self.rate) - 1
            self.last = now2
            self.tokens = max(self.tokens, 0)
        else:
            self.tokens -= 1
            self.last = now


_rate_limiter = _TokenBucket(YTM_QPS)


def _headers_to_raw(headers_input: Union[str, Dict[str, str]]) -> str:
    """Accept raw header string or a dict and normalize to raw multi-line string."""
    if isinstance(headers_input, str):
        return headers_input
    if isinstance(headers_input, dict):
        return "\n".join(f"{k}: {v}" for k, v in headers_input.items())
    raise YTMError("Invalid headers format. Must be raw string or key/value dict.")


def _existing_video_ids(ytmusic: ytmusicapi.YTMusic, playlist_id: str) -> Set[str]:
    """Fetch current items for the target playlist to avoid inserting duplicates."""
    try:
        _rate_limiter.acquire()
        pl = ytmusic.get_playlist(playlist_id, limit=100000)
        existing: Set[str] = set()
        for t in (pl.get("tracks") or []):
            if isinstance(t, dict):
                vid = t.get("videoId")
                if isinstance(vid, str) and vid:
                    existing.add(vid)
        return existing
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logging.warning(
            "Could not fetch existing items for playlist %s: %s",
            playlist_id,
            exc,
        )
        return set()


def _normalize(s: str) -> str:
    """Lowercase, strip featuring/[]-parts, remove punctuation and normalize whitespace."""
    s = s.lower()
    s = re.sub(r"\(feat\.[^)]+\)", "", s)
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"[^a-z0-9\s\-:&]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _fmt_label(t: dict) -> str:
    """Human readable label for logs and UI diagnostics."""
    artists = t.get("artists") or t.get("artist") or []
    if isinstance(artists, list):
        artist = ", ".join(
            a.get("name", a) if isinstance(a, dict) else str(a) for a in artists
        )
    else:
        artist = str(artists)

    if isinstance(t.get("album"), dict):
        album = (t.get("album", {}) or {}).get("name") or ""
    else:
        album = t.get("album") or t.get("album_name") or ""

    title = t.get("name") or t.get("title") or t.get("track") or "Unknown Title"
    return f"{artist} — {title}" if not album else f"{artist} — {album} — {title}"


def validate_headers(headers_raw: Union[str, Dict[str, str]]) -> Tuple[bool, str]:
    """Try a light call with the provided raw headers to verify validity."""
    tmpdir = "/dev/shm" if os.path.isdir("/dev/shm") else None
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", dir=tmpdir) as temp_file:
            temp_path = temp_file.name

        ytmusicapi.setup(filepath=temp_path, headers_raw=_headers_to_raw(headers_raw))
        ytmusic = ytmusicapi.YTMusic(temp_path)
        _rate_limiter.acquire()
        _ = ytmusic.get_library_playlists(limit=1)
        return True, "Headers valid."
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return False, f"Headers invalid or expired: {str(exc)}"
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def add_single_video_to_playlist(
    playlist_id: str, video_id: str, headers_raw: Union[str, Dict[str, str]]
) -> bool:
    """Add a single videoId to the target playlist (duplicates disabled)."""
    tmpdir = "/dev/shm" if os.path.isdir("/dev/shm") else None
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", dir=tmpdir) as temp_file:
            temp_path = temp_file.name

        ytmusicapi.setup(filepath=temp_path, headers_raw=_headers_to_raw(headers_raw))
        ytm = ytmusicapi.YTMusic(temp_path)
        _rate_limiter.acquire()
        res = ytm.add_playlist_items(playlist_id, [video_id], duplicates=False)
        ok = not isinstance(res, dict) or res.get("status") in (None, "STATUS_SUCCEEDED")
        return bool(ok)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def search_tracks(
    query: str, headers_raw: Union[str, Dict[str, str]], *, filt: str = "songs", top_k: int = 5
) -> List[Dict[str, Any]]:
    """Lightweight YT Music search for UI suggestions; returns top_k raw results."""
    tmpdir = "/dev/shm" if os.path.isdir("/dev/shm") else None
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", dir=tmpdir) as temp_file:
            temp_path = temp_file.name

        ytmusicapi.setup(filepath=temp_path, headers_raw=_headers_to_raw(headers_raw))
        ytm = ytmusicapi.YTMusic(temp_path)
        _rate_limiter.acquire()
        if filt == "uploads":
            results = ytm.search(query, scope="uploads") or []
        else:
            results = (
                ytm.search(query, scope="uploads")
                if filt == "uploads"
                else ytm.search(query, filter=filt)
            ) or []
        return results[:top_k]
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _search_track_exactish(ytmusic: ytmusicapi.YTMusic, track: dict) -> Optional[str]:
    """Heuristic song lookup that prefers normalized title/artist containment."""
    q_title = _normalize(str(track.get("name") or ""))
    artist0 = ""
    artists = track.get("artists") or []
    if isinstance(artists, list) and artists:
        a0 = artists[0]
        artist0 = a0.get("name") if isinstance(a0, dict) else str(a0)
    q_artist = _normalize(str(artist0))
    query = f"{str(track.get('name') or '')} {artist0}".strip()

    try:
        _rate_limiter.acquire()
        candidates = ytmusic.search(query, filter="songs") or []
        for r in candidates[:7]:
            title = _normalize(str(r.get("title") or ""))
            artists_str = " ".join(a.get("name", "") for a in r.get("artists", [])).lower()
            if q_title in title and (q_artist in artists_str or artists_str in q_artist):
                return r.get("videoId")
        return candidates[0].get("videoId") if candidates else None
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logging.warning("Search error for '%s': %s", query, exc)
        return None


def get_video_ids(ytmusic: ytmusicapi.YTMusic, tracks: List[dict]) -> Tuple[List[str], Dict[str, Any]]:
    """Index-stable search: return list aligned with `tracks` order (None filtered)."""
    video_ids: List[Optional[str]] = [None] * len(tracks)
    missed_tracks: Dict[str, Any] = {"count": 0, "tracks": []}

    def task(i: int, t: dict) -> Tuple[int, Optional[str]]:
        try:
            vid = _search_track_exactish(ytmusic, t)
            return i, vid
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logging.warning("Executor task failed for %s: %s", t_label(t), exc)
            return i, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=YTM_SEARCH_WORKERS) as ex:
        futures = [ex.submit(task, i, t) for i, t in enumerate(tracks)]
        for fut in concurrent.futures.as_completed(futures):
            i, vid = fut.result()
            if vid:
                video_ids[i] = vid
            else:
                missed_tracks["count"] += 1
                missed_tracks["tracks"].append(f"{t_label(tracks[i])}")

    found = [v for v in video_ids if v]
    logging.info("Found %d of %d tracks on YouTube Music.", len(found), len(tracks))
    if not found and tracks:
        raise YTMError(
            "Not a single track could be found on YouTube Music. "
            "Are your authentication headers correct and valid?"
        )
    return video_ids, missed_tracks


def t_label(t: Dict[str, Any]) -> str:
    """Safe wrapper that never raises; returns a user friendly label."""
    try:
        return _fmt_label(t)
    except Exception:  # pylint: disable=broad-exception-caught
        return "Unknown Artist — Unknown Title"


def _add_tracks_resilient(
    ytmusic: ytmusicapi.YTMusic, playlist_id: str, video_ids: List[str]
) -> List[str]:
    """Robust add with chunking and binary split retries. Duplicates are pre-filtered."""
    failed: List[str] = []
    existing = _existing_video_ids(ytmusic, playlist_id)

    def add_chunk(chunk: List[str]) -> None:
        nonlocal existing, failed
        filtered = [v for v in chunk if v and v not in existing]
        if not filtered:
            return
        try:
            _rate_limiter.acquire()
            res = ytmusic.add_playlist_items(playlist_id, filtered, duplicates=False)
            ok = not isinstance(res, dict) or res.get("status") in (None, "STATUS_SUCCEEDED")
            if ok:
                existing.update(filtered)
                logging.info("Inserted %d items", len(filtered))
                return
            logging.error("Add returned non-success: %s", str(res)[:300])
        except YTMusicServerError as exc:
            if "409" in str(exc):
                logging.warning(
                    "409 on %d items, will split and retry",
                    len(filtered),
                )
            else:
                logging.exception(
                    "YTMusicServerError on %d items: %s",
                    len(filtered),
                    exc,
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logging.exception(
                "Unexpected error adding %d items: %s",
                len(filtered),
                exc,
            )

        if len(filtered) == 1:
            failed.extend(filtered)
            return

        mid = len(filtered) // 2
        add_chunk(filtered[:mid])
        time.sleep(YTM_SLEEP_SECS)
        add_chunk(filtered[mid:])
        time.sleep(YTM_SLEEP_SECS)

    total = len(video_ids)
    logging.info(
        "Adding %d tracks to playlist %s in chunks of %d",
        total,
        playlist_id,
        YTM_BATCH_SIZE,
    )
    for start in range(0, total, YTM_BATCH_SIZE):
        add_chunk(video_ids[start : start + YTM_BATCH_SIZE])
        time.sleep(YTM_SLEEP_SECS)
    return failed


def create_ytm_playlist(
    playlist_link: str,
    headers_raw: Union[str, Dict[str, str]],
    *,
    market: str = "US",
    privacy_status: str = "PRIVATE",
    title_override: Optional[str] = None,
    dry_run: bool = False,
    target_playlist_id: Optional[str] = None,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Create or update a YT Music playlist from a Spotify link and return (playlist_id, missed)."""
    tmpdir = "/dev/shm" if os.path.isdir("/dev/shm") else None
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", dir=tmpdir) as temp_file:
            temp_path = temp_file.name

        ytmusicapi.setup(filepath=temp_path, headers_raw=_headers_to_raw(headers_raw))
        ytmusic = ytmusicapi.YTMusic(temp_path)

        tracks = get_all_tracks(playlist_link, market)
        name = title_override or get_playlist_name(playlist_link)
        video_ids, missed_tracks = get_video_ids(ytmusic, tracks)

        labels: List[str] = [t_label(t) for t in tracks]

        # De-duplicate by videoId while keeping the order stable
        seen: Set[str] = set()
        unique_video_ids: List[str] = []
        dup_labels: List[str] = []
        label_by_id: Dict[str, str] = {}
        for vid, lab in zip(video_ids, labels):
            if not vid:
                continue
            if vid in seen:
                dup_labels.append(lab)
                continue
            seen.add(vid)
            unique_video_ids.append(vid)
            label_by_id.setdefault(vid, lab)

        dup_count = len(dup_labels)
        missed: Dict[str, Any] = {
            "count": int(missed_tracks.get("count", 0)) if isinstance(missed_tracks, dict) else 0,
            "tracks": list(missed_tracks.get("tracks", [])) if isinstance(missed_tracks, dict) else [],
            "duplicates": {"count": dup_count, "items": dup_labels},
            "_stats": {"found_total": int(len(unique_video_ids) + dup_count)},
        }

        if dry_run:
            return None, missed

        if target_playlist_id:
            pid: Union[str, Dict[str, Any]] = target_playlist_id
        else:
            # create a new playlist
            pid = ytmusic.create_playlist(
                title=name,
                description="Created with SpotiTransFair",
                privacy_status=privacy_status,
            )
            time.sleep(YTM_POST_CREATE_SLEEP)

        # ytmusicapi historically returned a string; some forks may return dicts
        if isinstance(pid, dict):
            pid = pid.get("playlistId") or pid.get("id") or ""
        if not isinstance(pid, str) or not pid:
            raise YTMError("Failed to obtain playlist id from YouTube Music response.")

        failed_inserts = _add_tracks_resilient(ytmusic, pid, unique_video_ids)
        if failed_inserts:
            logging.warning(
                "Insert failed for %d/%d tracks",
                len(failed_inserts),
                len(unique_video_ids),
            )
            missed["count"] += len(failed_inserts)
            missed["tracks"].extend(
                [label_by_id.get(vid, f"[insert_failed] {vid}") for vid in failed_inserts]
            )

        inserted_count = len(unique_video_ids) - len(failed_inserts)
        missed["_stats"]["inserted"] = int(inserted_count)

        return pid, missed

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass

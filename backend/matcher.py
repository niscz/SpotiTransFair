import re
from difflib import SequenceMatcher
from typing import Dict, Any, List, Tuple, Optional
from models import ItemStatus

def normalize_string(s: str) -> str:
    if not s:
        return ""
    s = str(s).lower()
    # Remove (feat. ...)
    s = re.sub(r"\(feat\..*?\)", "", s)
    # Remove - Remastered...
    s = re.sub(r"-\s*remastered.*", "", s)
    # Remove punctuation
    s = re.sub(r"[^\w\s]", "", s)
    # Collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s

def calculate_score(source: Dict[str, Any], target: Dict[str, Any]) -> float:
    # Check ISRC first - strong signal
    src_isrc = source.get("isrc")
    tgt_isrc = target.get("isrc")
    if src_isrc and tgt_isrc and src_isrc == tgt_isrc:
        return 1.0

    # 1. Title Match
    src_title = normalize_string(source.get("name", ""))
    tgt_title = normalize_string(target.get("title", ""))
    title_score = SequenceMatcher(None, src_title, tgt_title).ratio()

    # 2. Artist Match
    src_artists = [normalize_string(a) for a in source.get("artists", [])]
    tgt_artists = [normalize_string(a) for a in target.get("artists", [])]

    artist_score = 0.0
    if src_artists and tgt_artists:
        scores = []
        for sa in src_artists:
            for ta in tgt_artists:
                scores.append(SequenceMatcher(None, sa, ta).ratio())
        artist_score = max(scores) if scores else 0.0

    # 3. Duration Match
    # Spotify duration is ms
    src_dur = source.get("duration_ms", 0)
    # TIDAL usually returns seconds.
    tgt_dur_raw = target.get("duration", 0)
    tgt_dur = tgt_dur_raw * 1000 # Assume seconds as per typical API

    duration_score = 1.0
    if src_dur and tgt_dur:
        diff = abs(src_dur - tgt_dur)
        if diff > 15000: # 15s tolerance
            duration_score = 0.0
        elif diff > 5000: # 5s tolerance
            duration_score = 0.5

    # Weights: Title 50%, Artist 35%, Duration 15%
    final_score = (title_score * 0.50) + (artist_score * 0.35) + (duration_score * 0.15)

    return final_score

def match_track(source_track: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], ItemStatus]:
    if not candidates:
        return None, ItemStatus.NOT_FOUND

    best_match = None
    best_score = 0.0

    for cand in candidates:
        score = calculate_score(source_track, cand)
        cand["_score"] = score
        if score > best_score:
            best_score = score
            best_match = cand

    if best_score > 0.90:
        return best_match, ItemStatus.MATCHED
    elif best_score >= 0.75:
        return best_match, ItemStatus.UNCERTAIN
    else:
        return None, ItemStatus.NOT_FOUND

"""
This module handles the interaction with the YouTube Music API.
"""
import concurrent.futures
import tempfile
import os
import ytmusicapi
from requests.exceptions import RequestException
from spotify import get_all_tracks, get_playlist_name, SpotifyError


class YTMError(Exception):
    """Custom exception for errors related to YouTube Music processing."""


def search_track(ytmusic, track):
    """Searches for a single track on YouTube Music and returns its video ID or None."""
    search_string = f"{track['name']} {track['artists'][0]}"
    try:
        search_results = ytmusic.search(search_string, filter="songs")
        if search_results:
            return search_results[0]["videoId"]
        return None
    except RequestException as e:
        print(f"Network error while searching for '{search_string}': {e}")
    except IndexError:
        print(f"No results found for '{search_string}' on YouTube Music.")
    except Exception as e:
        print(f"Generic error while searching for '{search_string}': {e}")
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


def create_ytm_playlist(playlist_link, headers_raw):
    """Creates a YouTube Music playlist from a Spotify playlist link."""
    
    # NamedTemporaryFile creates a secure, temporary file.
    # 'delete=False' is necessary on Windows for reusing the path.
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    
    try:
        # Let the library process the headers and write to the temporary file.
        ytmusicapi.setup(filepath=temp_file.name, headers_raw=headers_raw)
        
        # Initialize the client with the path to the correctly formatted temporary file.
        ytmusic = ytmusicapi.YTMusic(temp_file.name)
        
        tracks = get_all_tracks(playlist_link, "IN")
        name = get_playlist_name(playlist_link)
        video_ids, missed_tracks = get_video_ids(ytmusic, tracks)

        if video_ids:
            ytmusic.create_playlist(
                title=name,
                description="Created with SpotiTransFair",
                privacy_status="PRIVATE",
                video_ids=video_ids
            )
        return missed_tracks
    finally:
        # Ensure the temporary file is ALWAYS deleted,
        # even if an error occurs.
        temp_file.close()
        os.unlink(temp_file.name)

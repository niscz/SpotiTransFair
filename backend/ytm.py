"""
Dieses Modul ist für die Interaktion mit der YouTube Music API zuständig.
"""
import concurrent.futures
import tempfile
import os
import ytmusicapi
from requests.exceptions import RequestException
from spotify import get_all_tracks, get_playlist_name


class YTMError(Exception):
    """Benutzerdefinierte Ausnahme für Fehler im Zusammenhang mit der YouTube Music Verarbeitung."""


def search_track(ytmusic, track):
    """Sucht einen einzelnen Titel auf YouTube Music und gibt die Video-ID oder None zurück."""
    search_string = f"{track['name']} {track['artists'][0]}"
    try:
        search_results = ytmusic.search(search_string, filter="songs")
        if search_results:
            return search_results[0]["videoId"]
        return None
    except RequestException as e:
        print(f"Netzwerkfehler bei der Suche nach '{search_string}': {e}")
    except IndexError:
        print(f"Keine Ergebnisse für '{search_string}' auf YouTube Music gefunden.")
    except Exception as e:
        print(f"Allgemeiner Fehler bei der Suche nach '{search_string}': {e}")
    return None


def get_video_ids(ytmusic, tracks):
    """Sucht parallel auf YouTube Music nach Titeln und gibt deren Video-IDs zurück."""
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
                print(f"Eine Executor-Ausnahme ist für den Titel {track['name']} aufgetreten: {e}")
                missed_tracks["count"] += 1
                missed_tracks["tracks"].append(f"{track['name']} - {track['artists'][0]}")

    print(f"{len(video_ids)} von {len(tracks)} Titeln auf YouTube Music gefunden.")
    if not video_ids and tracks:
        raise YTMError("Kein einziger Titel konnte auf YouTube Music gefunden werden. Sind Ihre Authentifizierungs-Header korrekt und gültig?")
    return video_ids, missed_tracks


def create_ytm_playlist(playlist_link, headers_raw):
    """Erstellt eine YouTube Music Playlist aus einem Spotify-Playlist-Link."""
    
    # NamedTemporaryFile erstellt eine sichere, temporäre Datei.
    # 'delete=False' ist auf Windows für die Wiederverwendung des Pfades notwendig.
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    
    try:
        # Lasse die Bibliothek die Header verarbeiten und in die temporäre Datei schreiben.
        ytmusicapi.setup(filepath=temp_file.name, headers_raw=headers_raw)
        
        # Initialisiere den Client mit dem Pfad zur korrekt formatierten temporären Datei.
        ytmusic = ytmusicapi.YTMusic(temp_file.name)
        
        tracks = get_all_tracks(playlist_link, "IN")
        name = get_playlist_name(playlist_link)
        video_ids, missed_tracks = get_video_ids(ytmusic, tracks)

        if video_ids:
            ytmusic.create_playlist(
                title=name,
                description="Erstellt mit SpotiTransFair",
                privacy_status="PRIVATE",
                video_ids=video_ids
            )
        return missed_tracks
    finally:
        # Stelle sicher, dass die temporäre Datei IMMER gelöscht wird,
        # auch wenn ein Fehler auftritt.
        temp_file.close()
        os.unlink(temp_file.name)

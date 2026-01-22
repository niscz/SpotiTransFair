import os
import logging
import tempfile

import redis
import ytmusicapi
from rq import Worker, Queue
from sqlmodel import Session, select
from database import engine
from models import ImportJob, ImportItem, JobStatus, ItemStatus, Provider, Connection as DBConnection
from spotify import SpotifyClient
from tidal import TidalClient
from matcher import match_track
from ytm import get_video_ids, _headers_to_raw, _add_tracks_resilient
from qobuz import QobuzClient, QOBUZ_APP_SECRET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def finalize_import_job(job_id: int):
    with Session(engine) as session:
        job = session.get(ImportJob, job_id)
        if not job: return

        try:
            logger.info(f"Finalizing job {job_id}")

            # Gather matched items
            items = session.exec(select(ImportItem).where(ImportItem.job_id == job.id, ImportItem.status == ItemStatus.MATCHED)).all()
            track_ids = [i.selected_match_id for i in items if i.selected_match_id]

            if not track_ids:
                logger.warning("No tracks to import")
                job.status = JobStatus.DONE
                session.add(job)
                session.commit()
                return

            target_playlist_id = None

            if job.target_provider == Provider.TIDAL:
                tidal_conn = session.exec(select(DBConnection).where(DBConnection.user_id == job.user_id, DBConnection.provider == Provider.TIDAL)).first()
                if not tidal_conn:
                    raise RuntimeError("TIDAL connection not found for user.")
                if not tidal_conn.credentials.get("access_token"):
                    raise RuntimeError("TIDAL access token missing for user.")
                tidal_client = TidalClient(access_token=tidal_conn.credentials.get("access_token"))

                # Create Playlist
                name = job.source_playlist_name or "Imported Playlist"
                target_playlist_id = tidal_client.create_playlist(tidal_client.get_user_id(), name, "Migrated with SpotiTransFair")

                # Add Tracks
                tidal_client.add_tracks(target_playlist_id, track_ids)

            elif job.target_provider == Provider.QOBUZ:
                qobuz_conn = session.exec(select(DBConnection).where(DBConnection.user_id == job.user_id, DBConnection.provider == Provider.QOBUZ)).first()
                if not qobuz_conn:
                    raise RuntimeError("Qobuz connection not found for user.")
                access_token = qobuz_conn.credentials.get("access_token")
                app_id = qobuz_conn.credentials.get("app_id")
                app_secret = qobuz_conn.credentials.get("app_secret") or QOBUZ_APP_SECRET
                if not access_token or not app_id:
                    raise RuntimeError("Qobuz credentials missing for user.")
                qobuz_client = QobuzClient(app_id=app_id, user_auth_token=access_token, app_secret=app_secret)

                name = job.source_playlist_name or "Imported Playlist"
                target_playlist_id = qobuz_client.create_playlist(name, "Migrated with SpotiTransFair")
                qobuz_client.add_tracks(target_playlist_id, track_ids)

            elif job.target_provider == Provider.YTM:
                ytm_conn = session.exec(select(DBConnection).where(DBConnection.user_id == job.user_id, DBConnection.provider == Provider.YTM)).first()
                if not ytm_conn:
                    raise RuntimeError("YTM connection not found for user.")
                creds = ytm_conn.credentials
                if isinstance(creds, dict) and "raw" in creds:
                    headers_raw = creds["raw"]
                else:
                    headers_raw = _headers_to_raw(creds)
                if not headers_raw:
                    raise RuntimeError("YTM authentication headers missing for user.")

                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp:
                        temp_path = temp.name

                    ytmusicapi.setup(filepath=temp_path, headers_raw=headers_raw)
                    ytmusic = ytmusicapi.YTMusic(temp_path)

                    name = job.source_playlist_name or "Imported Playlist"
                    # Create playlist returns ID or dict depending on version. ytm.create_ytm_playlist handled it.
                    # We'll use basic ytmusic.create_playlist
                    res = ytmusic.create_playlist(title=name, description="Migrated with SpotiTransFair")
                    if isinstance(res, dict):
                        target_playlist_id = res.get("playlistId") or res.get("id")
                    else:
                        target_playlist_id = str(res)

                    # Add tracks
                    _add_tracks_resilient(ytmusic, target_playlist_id, track_ids)

                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass

            job.target_playlist_id = target_playlist_id
            job.status = JobStatus.DONE
            session.add(job)
            session.commit()
            logger.info(f"Job {job_id} done. Playlist: {target_playlist_id}")

        except Exception as e:
            logger.exception(f"Finalize job {job_id} failed")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            session.add(job)
            session.commit()

def process_import_job(job_id: int):
    with Session(engine) as session:
        job = session.get(ImportJob, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        try:
            job.status = JobStatus.RUNNING
            session.add(job)
            session.commit()

            logger.info(f"Processing job {job_id} for user {job.user_id} to {job.target_provider}")

            # 1. Fetch Source Tracks (Spotify)
            spotify_conn = session.exec(select(DBConnection).where(DBConnection.user_id == job.user_id, DBConnection.provider == Provider.SPOTIFY)).first()
            if not spotify_conn:
                raise RuntimeError("Spotify connection not found for user.")

            token = spotify_conn.credentials.get("access_token") if spotify_conn else None
            refresh = spotify_conn.credentials.get("refresh_token") if spotify_conn else None
            if not token and not refresh:
                raise RuntimeError("Spotify credentials are missing access and refresh tokens.")

            def on_token_refresh(new_token_info):
                if spotify_conn:
                    if "refresh_token" not in new_token_info and spotify_conn.credentials.get("refresh_token"):
                        new_token_info["refresh_token"] = spotify_conn.credentials["refresh_token"]
                    spotify_conn.credentials = new_token_info
                    session.add(spotify_conn)
                    session.commit()

            sp_client = SpotifyClient(access_token=token, refresh_token=refresh, on_token_refresh=on_token_refresh)

            tracks = sp_client.get_playlist_tracks(job.source_playlist_id)
            logger.info(f"Fetched {len(tracks)} tracks from Spotify")

            if not job.source_playlist_name:
                try:
                    p_data = sp_client.get_playlist(job.source_playlist_id)
                    job.source_playlist_name = p_data.get("name")
                    session.add(job)
                except Exception:
                    pass

            # 2. Match
            if job.target_provider == Provider.TIDAL:
                tidal_conn = session.exec(select(DBConnection).where(DBConnection.user_id == job.user_id, DBConnection.provider == Provider.TIDAL)).first()
                if not tidal_conn:
                    raise Exception("Tidal connection not found")

                tidal_client = TidalClient(access_token=tidal_conn.credentials.get("access_token"))

                for track in tracks:
                    query = f"{track['name']} {track['artists'][0]}" if track['artists'] else track['name']
                    candidates = tidal_client.search_tracks(query)
                    match, status = match_track(track, candidates)

                    item = ImportItem(
                        job_id=job.id,
                        original_track_data=track,
                        match_data=match,
                        status=status,
                        selected_match_id=match["id"] if match else None
                    )
                    session.add(item)

            elif job.target_provider == Provider.QOBUZ:
                qobuz_conn = session.exec(select(DBConnection).where(DBConnection.user_id == job.user_id, DBConnection.provider == Provider.QOBUZ)).first()
                if not qobuz_conn:
                    raise Exception("Qobuz connection not found")
                access_token = qobuz_conn.credentials.get("access_token")
                app_id = qobuz_conn.credentials.get("app_id")
                app_secret = qobuz_conn.credentials.get("app_secret") or QOBUZ_APP_SECRET
                if not access_token or not app_id:
                    raise Exception("Qobuz credentials missing")
                qobuz_client = QobuzClient(app_id=app_id, user_auth_token=access_token, app_secret=app_secret)

                for track in tracks:
                    query = f"{track['name']} {track['artists'][0]}" if track['artists'] else track['name']
                    candidates = qobuz_client.search_tracks(query, limit=10)
                    match, status = match_track(track, candidates)

                    item = ImportItem(
                        job_id=job.id,
                        original_track_data=track,
                        match_data=match,
                        status=status,
                        selected_match_id=match["id"] if match else None
                    )
                    session.add(item)

            elif job.target_provider == Provider.YTM:
                ytm_conn = session.exec(select(DBConnection).where(DBConnection.user_id == job.user_id, DBConnection.provider == Provider.YTM)).first()
                if not ytm_conn:
                    raise Exception("YTM connection not found")

                creds = ytm_conn.credentials
                if isinstance(creds, dict) and "raw" in creds:
                    headers_raw = creds["raw"]
                else:
                    headers_raw = _headers_to_raw(creds)

                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp:
                        temp_path = temp.name

                    ytmusicapi.setup(filepath=temp_path, headers_raw=headers_raw)
                    ytmusic = ytmusicapi.YTMusic(temp_path)

                    # aligned list of video ids (or None)
                    video_ids, missed = get_video_ids(ytmusic, tracks)

                    for track, vid in zip(tracks, video_ids):
                        status = ItemStatus.MATCHED if vid else ItemStatus.NOT_FOUND
                        match_data = {"id": vid, "title": track["name"]} if vid else None

                        item = ImportItem(
                            job_id=job.id,
                            original_track_data=track,
                            match_data=match_data,
                            status=status,
                            selected_match_id=vid
                        )
                        session.add(item)
                finally:
                    if temp_path and os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass

            # 3. Completion
            job.status = JobStatus.WAITING_REVIEW
            session.add(job)
            session.commit()
            logger.info(f"Job {job_id} matching completed. Waiting for review.")

        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            session.add(job)
            session.commit()

if __name__ == "__main__":
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    conn = redis.from_url(redis_url)
    # RQ > 1.0
    worker = Worker([Queue("default", connection=conn)], connection=conn)
    worker.work()

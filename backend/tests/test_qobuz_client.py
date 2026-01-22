import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Patch env vars BEFORE importing qobuz
with patch.dict(os.environ, {"QOBUZ_APP_ID": "env_id", "QOBUZ_APP_SECRET": "env_secret"}):
    from qobuz import QobuzClient, login_qobuz, QobuzError

class TestQobuzClient(unittest.TestCase):
    def setUp(self):
        self.app_id = "test_app_id"
        self.secret = "test_secret"
        self.token = "test_token"
        self.client = QobuzClient(app_id=self.app_id, user_auth_token=self.token, app_secret=self.secret)

    @patch("qobuz.requests.get")
    @patch("qobuz.time.time")
    def test_login_qobuz_success(self, mock_time, mock_get):
        mock_time.return_value = 1000
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "user_auth_token": "new_token",
            "user": {"id": 123}
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        creds = login_qobuz("email", "password", app_id="test_id", app_secret="test_secret")
        self.assertEqual(creds["access_token"], "new_token")
        self.assertEqual(creds["user_id"], 123)
        self.assertEqual(creds["app_secret"], "test_secret")

        # Verify signature in params
        args, kwargs = mock_get.call_args
        params = kwargs["params"]
        self.assertIn("request_sig", params)
        self.assertIn("request_ts", params)

    @patch("qobuz.requests.get")
    @patch("qobuz.time.time")
    def test_search_tracks(self, mock_time, mock_get):
        mock_time.return_value = 1000
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tracks": {
                "items": [
                    {
                        "id": 1,
                        "title": "Track 1",
                        "artist": {"name": "Artist 1"},
                        "artists": [{"name": "Artist 1"}, {"name": "Feat"}],
                        "duration": 200,
                        "album": {"title": "Album 1"},
                        "isrc": "ISRC1"
                    }
                ]
            }
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        results = self.client.search_tracks("query")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "1")
        self.assertEqual(results[0]["title"], "Track 1")
        self.assertIn("Artist 1", results[0]["artists"])
        self.assertIn("Feat", results[0]["artists"])

        # Verify params
        args, kwargs = mock_get.call_args
        params = kwargs["params"]
        self.assertIn("query", params)
        self.assertIn("request_sig", params)
        self.assertIn("request_ts", params)
        self.assertEqual(params["app_id"], self.app_id)

    @patch("qobuz.requests.post")
    @patch("qobuz.time.time")
    def test_create_playlist(self, mock_time, mock_post):
        mock_time.return_value = 1000
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 100}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        pid = self.client.create_playlist("My Playlist")
        self.assertEqual(pid, "100")

        args, kwargs = mock_post.call_args
        # Params should contain auth + sig
        params = kwargs["params"]
        self.assertIn("request_sig", params)
        self.assertIn("app_id", params)

        # Data should contain payload
        data = kwargs["data"]
        self.assertEqual(data["name"], "My Playlist")
        self.assertNotIn("app_id", data) # app_id should be in params

    @patch("qobuz.requests.post")
    def test_add_tracks_batching(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 60 tracks
        tracks = [str(i) for i in range(60)]
        self.client.add_tracks("100", tracks)

        self.assertEqual(mock_post.call_count, 2)

        # First call: 50 tracks
        call1 = mock_post.call_args_list[0]
        data1 = call1[1]["data"]
        self.assertEqual(len(data1["track_ids"].split(",")), 50)

        # Second call: 10 tracks
        call2 = mock_post.call_args_list[1]
        data2 = call2[1]["data"]
        self.assertEqual(len(data2["track_ids"].split(",")), 10)

if __name__ == "__main__":
    unittest.main()

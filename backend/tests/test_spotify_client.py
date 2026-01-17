import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import spotify
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spotify import SpotifyClient

class TestSpotifyClient(unittest.TestCase):
    def test_token_refresh_callback(self):
        # Setup
        initial_token = "old_token"
        refresh_token = "refresh_token"
        new_token_info = {"access_token": "new_token", "refresh_token": "refresh_token"}

        callback_mock = MagicMock()

        # We need to mock requests.Session to simulate 401 and then 200
        with patch('spotify._session') as mock_session_factory:
            mock_session = mock_session_factory.return_value

            # First request returns 401
            resp_401 = MagicMock()
            resp_401.status_code = 401
            resp_401.content = b'{"error": "expired"}'

            # Refresh request returns 200 with new token
            resp_refresh = MagicMock()
            resp_refresh.status_code = 200
            resp_refresh.json.return_value = new_token_info

            # Second request (retry) returns 200 with data
            resp_200 = MagicMock()
            resp_200.status_code = 200
            resp_200.content = b'{"items": []}'
            resp_200.json.return_value = {"items": []}

            def request_side_effect(method, url, **kwargs):
                # The client calls request(...)
                auth_header = kwargs.get("headers", {}).get("Authorization", "")

                # Check if we are refreshing (which calls request?? No, refresh calls POST directly)
                # Client._refresh_access_token calls self._http.post(...)
                # Client._request calls self._http.request(...)

                if f"Bearer {initial_token}" in auth_header:
                     return resp_401
                if f"Bearer {new_token_info['access_token']}" in auth_header:
                     return resp_200
                return resp_401

            mock_session.request.side_effect = request_side_effect
            mock_session.post.return_value = resp_refresh

            client = SpotifyClient(
                access_token=initial_token,
                refresh_token=refresh_token,
                on_token_refresh=callback_mock
            )

            # Action
            client.get_user_playlists()

            # Assert
            # Callback should be called
            callback_mock.assert_called_once_with(new_token_info)
            # Token should be updated
            self.assertEqual(client.access_token, "new_token")

if __name__ == '__main__':
    unittest.main()

"""
Main application file for the Flask server.
"""
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from asgiref.wsgi import WsgiToAsgi
from ytm import create_ytm_playlist, YTMError
from spotify import SpotifyError

load_dotenv()

# Step 1: Create the normal Flask WSGI app
wsgi_app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CORS(wsgi_app, resources={
    r"/*": {
        "origins": [os.getenv('FRONTEND_URL')],
        "methods": ["POST", "GET"],
    }
})

@wsgi_app.route('/create', methods=['POST'])
def create_playlist():
    """API endpoint for creating a YouTube Music playlist."""
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid request body."}), 400
    playlist_link = data.get('playlist_link')
    auth_headers = data.get('auth_headers')
    if not playlist_link or not auth_headers:
        return jsonify({"message": "Playlist link and authentication headers are required."}), 400

    try:
        missed_tracks = create_ytm_playlist(playlist_link, auth_headers)
        return jsonify({
            "message": "Playlist created successfully!",
            "missed_tracks": missed_tracks
        }), 200

    except SpotifyError as e:
        # Catch specific, "safe" errors from the Spotify API.
        logging.warning("A Spotify API error occurred: %s", e)
        return jsonify({"message": str(e)}), 422

    except YTMError as e:
        # Catch predictable, "safe" errors from the YTM logic.
        logging.warning("A predictable YTM error occurred: %s", e)
        return jsonify({"message": str(e)}), 422

    except Exception:
        # Catch unexpected internal server errors.
        logging.error("An unhandled error occurred:", exc_info=True)
        return jsonify({
            "message": "An internal server error occurred. Please try again later."
        }), 500

@wsgi_app.route('/')
def home():
    """Endpoint for the system health check."""
    return jsonify({"message": "Server Online"}), 200

# Step 2: Create an ASGI-compatible app by wrapping the WSGI app.
# Gunicorn will use this 'app' variable.
app = WsgiToAsgi(wsgi_app)

if __name__ == '__main__':
    # For direct debugging, run the original WSGI app.
    wsgi_app.run(port=8001)

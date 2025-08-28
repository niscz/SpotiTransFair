"""
Hauptanwendungsdatei für den Flask-Server.
"""
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from asgiref.wsgi import WsgiToAsgi
from ytm import create_ytm_playlist, YTMError

load_dotenv()

# Schritt 1: Erstelle die normale Flask WSGI-App
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
    # Der Inhalt dieser Funktion bleibt unverändert
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
    except YTMError as e:
        logging.warning("Ein vorhersehbarer YTM-Fehler ist aufgetreten: %s", e)
        return jsonify({"message": str(e)}), 422
    except Exception:
        logging.error("Ein unbehandelter Fehler ist aufgetreten:", exc_info=True)
        return jsonify({
            "message": "An internal server error occurred. Please try again later."
        }), 500

@wsgi_app.route('/')
def home():
    """Endpunkt für den Systemzustand (Health Check)."""
    return jsonify({"message": "Server Online"}), 200

# Schritt 2: Erstelle eine ASGI-kompatible App, indem du die WSGI-App umhüllst.
# Gunicorn wird diese 'app'-Variable verwenden.
app = WsgiToAsgi(wsgi_app)

if __name__ == '__main__':
    # Für direktes Debugging, starte die ursprüngliche WSGI-App.
    wsgi_app.run(port=8001)

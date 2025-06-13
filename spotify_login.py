from flask import Blueprint, redirect, request, session, jsonify, make_response
import logging
import os
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

load_dotenv()

spotify_login_bp = Blueprint('spotify', __name__)

def get_spotify_oauth():
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
    logging.info(f"Env vars loaded: ID={client_id[:4]}..., URI={redirect_uri}")
    if not all([client_id, client_secret, redirect_uri]):
        logging.error("Missing Spotify env variables")
        raise ValueError("Spotify env variables not set")
    try:
        oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope='user-read-private user-top-read playlist-modify-private'
        )
        logging.info("SpotifyOAuth created successfully")
        return oauth
    except Exception as e:
        logging.error(f"Failed to create SpotifyOAuth: {e}")
        raise

@spotify_login_bp.route('/login')
def login():
    try:
        mood = request.args.get('mood', 'happy')
        session['mood'] = mood
        logging.info(f"Login initiated with mood: {mood}, Session: {dict(session)}")
        sp_oauth = get_spotify_oauth()
        auth_url = sp_oauth.get_authorize_url()
        logging.info(f"Redirecting to Spotify auth URL: {auth_url}")
        return redirect(auth_url)
    except Exception as e:
        logging.error(f"Error in /login: {e}")
        return jsonify({"error": str(e)}), 500

@spotify_login_bp.route('/callback')
def callback():
    try:
        sp_oauth = get_spotify_oauth()
        code = request.args.get('code')
        if not code:
            logging.error("No code provided in callback")
            return jsonify({"error": "No code provided"}), 400
        token_info = sp_oauth.get_access_token(code)
        if not token_info or 'access_token' not in token_info:
            logging.error(f"Failed to get token_info: {token_info}")
            return jsonify({"error": "Failed to get token"}), 400
        session['token_info'] = token_info
        logging.info(token_info)
        logging.info(f"Token Info stored, Session: {dict(session)}")
        mood = session.get('mood', 'happy')
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        return redirect(f'{frontend_url}/select-artists?mood={mood}')
    except Exception as e:
        logging.error(f"Error in /callback: {e}")
        return jsonify({"error": str(e)}), 500
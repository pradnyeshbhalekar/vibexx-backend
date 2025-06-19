from flask import Blueprint, Flask, render_template, request, redirect, url_for, session, make_response
import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import urllib.parse
import json

spotify_login_bp = Blueprint('spotify', __name__)

def get_spotify_oauth(state=None):
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')

    if not all([client_id, client_secret, redirect_uri]):
        logging.error("Missing Spotify env variables: ID=%s, SECRET=%s, URI=%s",
                      client_id, client_secret, redirect_uri)
        raise ValueError("Spotify env variables not set")
    
    try:
        oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            cache_handler=None,
            scope='user-read-private user-top-read playlist-modify-private user-read-email playlist-modify-public',
            state=state  # Pass mood as state
        )
        logging.info("SpotifyOAuth created")
        return oauth
    except Exception as e:
        logging.error(f"Failed to create SpotifyOAuth: {e}")
        raise

@spotify_login_bp.route('/login')
def login():
    mood = request.args.get('mood')  # Capture mood from URL
    valid_moods = ['Happy', 'Sad', 'Neutral', 'Angry']
    if mood not in valid_moods:
        mood = 'Neutral'
    
    oauth = get_spotify_oauth(state=mood)  # Pass mood to OAuth state
    auth_url = oauth.get_authorize_url()
    return redirect(auth_url)

@spotify_login_bp.route("/callback")
def callback():
    oauth = get_spotify_oauth()
    code = request.args.get("code")
    state = request.args.get("state", "Neutral")  # Retrieve mood from state
    if not code:
        return redirect("http://127.0.0.1:3000/error")

    token_info = oauth.get_access_token(code)
    access_token = token_info.get("access_token")

    if not access_token:
        return redirect("http://127.0.0.1:3000/error")

    sp = spotipy.Spotify(auth=access_token)
    user_data = sp.current_user()
    email = user_data.get("email")
    logging.info(f"User authenticated: {email}")

    # Store token and mood in cookie
    response = make_response(redirect(f"http://127.0.0.1:3000/select-artists?mood={urllib.parse.quote(state)}"))
    response.set_cookie(
        "token",
        urllib.parse.quote(json.dumps(token_info)),
        httponly=True,
        samesite="Lax",
        max_age=3600
    )
    return response

@spotify_login_bp.route("/create-playlist")
def create_playlist():
    token = request.cookies.get("token")
    mood = request.args.get("mood", "Neutral")
    valid_moods = ['Happy', 'Sad', 'Neutral', 'Angry']
    if mood not in valid_moods:
        mood = 'Neutral'

    if not token:
        return redirect("http://127.0.0.1:3000/error")

    try:
        token_info = json.loads(urllib.parse.unquote(token))
        access_token = token_info.get("access_token")
        sp = spotipy.Spotify(auth=access_token)
        user_id = sp.current_user()['id']

        # Map mood to genres
        mood_genres = {
            "Happy": "pop,dance",
            "Sad": "acoustic,indie",
            "Neutral": "chill,lo-fi",
            "Angry": "rock,metal"
        }
        genres = mood_genres.get(mood, "chill")

        # Create playlist
        playlist = sp.user_playlist_create(
            user_id,
            f"Moodify: {mood} Playlist",
            public=False,
            description=f"Created based on your {mood} mood"
        )
        playlist_id = playlist['id']

        # Get recommendations
        recommendations = sp.recommendations(seed_genres=genres, limit=10)
        track_uris = [track['uri'] for track in recommendations['tracks']]

        # Add tracks to playlist
        sp.playlist_add_items(playlist_id, track_uris)

        # Redirect to frontend with playlist ID
        return redirect(f"http://127.0.0.1:3000/playlist?playlist_id={playlist_id}&mood={urllib.parse.quote(mood)}")
    except Exception as e:
        logging.error(f"Playlist creation failed: {e}")
        return redirect("http://127.0.0.1:3000/error")

@spotify_login_bp.route("/logout")
def logout():
    cache_path = ".cache"
    if os.path.exists(cache_path):
        os.remove(cache_path)

    response = make_response(redirect("http://127.0.0.1:3000"))
    response.set_cookie("token", "", expires=0, path="/")
    return response
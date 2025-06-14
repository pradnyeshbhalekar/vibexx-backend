from flask import Blueprint, Flask, render_template, request, redirect, url_for, session,make_response
import os
import logging
from spotipy.oauth2 import SpotifyOAuth
import urllib.parse
import json

spotify_login_bp = Blueprint('spotify', __name__)

def get_spotify_oauth():
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
            scope='user-read-private user-top-read playlist-modify-private'
        )
        logging.info("SpotifyOAuth created")
        return oauth
    except Exception as e:
        logging.error(f"Failed to create SpotifyfOAuth: {e}")
        raise

@spotify_login_bp.route('/login')
def login():
    oauth = get_spotify_oauth()
    auth_url = oauth.get_authorize_url()
    return redirect(auth_url)

@spotify_login_bp.route("/callback")
def callback():
    oauth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:5000/callback",  # Must match Spotify dashboard
        scope="user-read-private user-top-read playlist-modify-private"
    )
    
    code = request.args.get("code")
    if not code:
        return redirect("http://127.0.0.1:3000/error")

    token_info = oauth.get_access_token(code)

    # Create a response and set cookie
    response = make_response(redirect("http://127.0.0.1:3000/select-artists"))
    response.set_cookie(
        "token",
        urllib.parse.quote(json.dumps(token_info)), 
        httponly=True,
        samesite="Lax",
        max_age=3600 
    )

    return response
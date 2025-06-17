from flask import Blueprint, Flask, render_template, request, redirect, url_for, session,make_response
import os
import logging
import spotipy
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
            cache_handler=None,
            scope='user-read-private user-top-read playlist-modify-private user-read-email'
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
    oauth = get_spotify_oauth() 
    code = request.args.get("code")
    if not code:
        return redirect("http://127.0.0.1:3000/error")

    token_info = oauth.get_access_token(code)
    access_token = token_info.get("access_token")

    if not access_token:
        return redirect("http://127.0.0.1:3000/error")

    import spotipy
    sp = spotipy.Spotify(auth=access_token)
    user_data = sp.current_user()
    email = user_data.get("email")
    print("user email", email)

    response = make_response(redirect("http://127.0.0.1:3000/select-artists"))
    response.set_cookie(
        "token",
        urllib.parse.quote(json.dumps(token_info)), 
        httponly=True,
        samesite="Lax",
        max_age=3600 
    )

    return response

@spotify_login_bp.route("/logout")
def logout():
    # Delete token cache (safe if none exists)
    cache_path = ".cache"
    if os.path.exists(cache_path):
        os.remove(cache_path)

    # Clear cookie
    response = make_response(redirect("http://127.0.0.1:3000"))
    response.set_cookie("token", "", expires=0, path="/")
    return response

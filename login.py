from flask import Blueprint, Flask, render_template, request, redirect, url_for, session
import os
import logging
import streamlit as st
from spotipy.oauth2 import SpotifyOAuth

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
        logging.error(f"Failed to create SpotifyOAuth: {e}")
        raise

@spotify_login_bp.route('/login')
def login():
    oauth = get_spotify_oauth()
    auth_url = oauth.get_authorize_url()
    return redirect(auth_url)

@spotify_login_bp.route('/callback')
def callback():
    oauth = get_spotify_oauth()
    code = request.args.get('code')

    if code:
        token_info = oauth.get_access_token(code)
        st.session_state['token_info'] = token_info
        print(token_info)
        session.modified = True  # Force Flask to save session

        return redirect('http://localhost:3000/select-artists')  # Redirect to frontend home page
    else:
        logging.error("No code found in callback")
        return redirect(url_for('spotify.login'))

import os
import logging
from flask import Blueprint, request, redirect, session, url_for, render_template,jsonify,make_response
import spotipy
import streamlit as st
from spotipy.oauth2 import SpotifyOAuth
import urllib.parse

import traceback
import logging
import json
from spotipy.oauth2 import SpotifyOAuth
from flask_cors import CORS # Import CORS

top_artist_bp = Blueprint('top_artist', __name__)
# CORS(top_artist_bp, supports_credentials=True, origins=[

#     "http://localhost:3000",
#     "http://127.0.0.1:3000"
# ]) # Apply CORS to the blueprint with credentials and origins

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:5000/callback",  # Must match Spotify Dashboard
        scope="user-read-private user-top-read playlist-modify-private"
    )


def get_token():
    token_cookie = request.cookies.get("token")
    if not token_cookie:
        print("❌ No token cookie found.")
        return None

    try:
        decoded_token = urllib.parse.unquote(token_cookie)
        token_info = json.loads(decoded_token)
    except Exception as e:
        print("❌ Failed to parse token cookie:", e)
        return None

    oauth = get_spotify_oauth()

    if oauth.is_token_expired(token_info):
        print("🔁 Token expired, refreshing...")
        token_info = oauth.refresh_access_token(token_info['refresh_token'])

    print("✅ Token loaded successfully")
    return spotipy.Spotify(auth=token_info['access_token'])


@top_artist_bp.route('/top-artist') 
def top_artist():
    sp = get_token()
    if sp is None:
        return redirect(url_for('spotify.login'))  # also fixed: you missed return here

    try:
        top_artists_data = sp.current_user_top_artists(limit=30, time_range='medium_term')
        artists = [{
            'name': artist['name'],
            'image': artist['images'][0]['url'] if artist['images'] else '',
            'genres': artist['genres']
        } for artist in top_artists_data['items']]
        
        return render_template('top_artists.html', artists=artists)
    except Exception as e:
        logging.error("Error while fetching top artists:\n%s", traceback.format_exc())
        return "An error occurred while fetching top artists."


@top_artist_bp.route('/top-artist-json') 
def top_artist_json():
    sp = get_token()
    if sp is None:
        return jsonify({"error":"Authenticate again"})
    try:
        top_artists_data = sp.current_user_top_artists(limit=20,time_range='medium_term')
        artist = [{
            'name':artist['name'],
            'image':artist['images'][0]['url'] if artist['images'] else '',
            'genres':artist['genres']

        }for artist in top_artists_data['items']]
        return jsonify(artist)
    except Exception as e:
        logging.error("Error while fetching top artists:\n%s", traceback.format_exc())
        return jsonify({"error":"An error occurred while fetching top artists."})
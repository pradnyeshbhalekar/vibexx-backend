import os
import logging
from flask import Blueprint, request, redirect, session, url_for, render_template,jsonify
import spotipy
import streamlit as st
import traceback
import logging
from spotipy.oauth2 import SpotifyOAuth
from flask_cors import CORS # Import CORS

top_artist_bp = Blueprint('top_artist', __name__)
CORS(top_artist_bp, supports_credentials=True, origins=[

    "http://localhost:3000",
    "http://127.0.0.1:3000"
]) # Apply CORS to the blueprint with credentials and origins

def get_token():
    token_info = st.session_state.token_info
    print(token_info)
    
    if not token_info:
        logging.error("Token not found in session")
        return None
    
    oauth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope='user-read-private user-top-read playlist-modify-private'
    )
    
    if oauth.is_token_expired(token_info):
        token_info = oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
        
    sp = spotipy.Spotify(auth=token_info['access_token'])
    return sp


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
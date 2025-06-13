from flask import Blueprint, request, session, jsonify, redirect
import logging
from logging.handlers import RotatingFileHandler
import spotipy
import os
from flask_cors import CORS
import time
import random
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler('app.log', maxBytes=1000000, backupCount=5)
    ]
)

playlist_bp = Blueprint('playlist', __name__, url_prefix='/playlist')

CORS(playlist_bp, supports_credentials=True, origins=[

    "http://localhost:3000",
    "http://127.0.0.1:3000"
]) # Apply CORS to the blueprint with credentials and origins

def get_spotify_oauth():
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
    if not all([client_id, client_secret, redirect_uri]):
        logging.error("Missing Spotify env variables")
        raise ValueError("Spotify env variables not set")
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope='user-read-private user-top-read playlist-modify-private'
    )

def get_token():
    logging.debug(f"Checking session: {dict(session)}")
    if 'token_info' not in session:
        logging.error("No token_info found in session")
        return None
    token_info = session.get('token_info')
    required_keys = ['access_token', 'refresh_token', 'expires_at']
    if not all(key in token_info and token_info[key] for key in required_keys):
        logging.error(f"Invalid token_info: {token_info}")
        return None
    if not isinstance(token_info['expires_at'], (int, float)) or token_info['expires_at'] <= 0:
        logging.error(f"Invalid expires_at: {token_info['expires_at']}")
        return None
    if token_info['expires_at'] - int(time.time()) < 60:
        try:
            logging.debug("Refreshing token...")
            sp_oauth = get_spotify_oauth()
            new_token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            if not new_token_info or 'access_token' not in new_token_info:
                logging.error("Failed to refresh token")
                return None
            session['token_info'] = new_token_info
            session.modified = True
            logging.info("Token refreshed")
            return new_token_info
        except Exception as e:
            logging.error(f"Error refreshing token: {str(e)}")
            return None
    return token_info

@playlist_bp.route('/top-artists', methods=['GET'])
def get_top_artists():
    print(f"Session at get_top_artists: {dict(session)}")
    token_info = session.get('token_info')
    
    if not token_info:
        logging.error("Token not found in session")
        return jsonify({"error": "No token found in session"}), 401
    
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
    
    # Fetch top artists
    try:
        results = sp.current_user_top_artists(limit=10, time_range='medium_term')
        artists = [
            {
                'name': artist['name'],
                'id': artist['id'],
                'genres': artist['genres'],
                'popularity': artist['popularity']
            }for artist in results['items']
        ]
        return jsonify(artists), 200
    except Exception as e:
        logging.error(f"Error fetching top artists: {str(e)}")
        return jsonify({"error": "Failed to fetch top artists"}), 500



@playlist_bp.route('/create', methods=['POST', 'OPTIONS'])
def create_playlist():
    """Create a playlist based on mood and up to 5 selected artists"""
    if request.method == 'OPTIONS':
        return '', 200

    logging.debug(f"Session at create_playlist: {dict(session)}")
    mood = request.json.get('mood', 'unknown')
    artist_names = request.json.get('artists', [])[:5]  # Limit to 5 artists
    logging.info(f"User provided mood: {mood}, artists: {artist_names}")

    token_info = get_token()
    if not token_info:
        logging.error("No user authenticated")
        return redirect('/login')

    try:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_profile = safe_api_call(sp.current_user)
        if not user_profile or 'id' not in user_profile:
            logging.error(f"Failed to retrieve user profile: {user_profile}")
            return jsonify({"error": "Cannot access user profile"}), 403
        user_id = user_profile['id']

        # Map mood to recommendation parameters
        mood_params = {
            'happy': {'min_valence': 0.7, 'min_energy': 0.6},
            'sad': {'max_valence': 0.3, 'min_energy': 0.1},
            'energetic': {'min_energy': 0.8, 'min_danceability': 0.6}
        }
        params = mood_params.get(mood.lower(), {})

        # Search for artist IDs
        seed_artists = []
        for artist_name in artist_names:
            result = safe_api_call(sp.search, q=f'artist:{artist_name}', type='artist', limit=1)
            if result and 'artists' in result and 'items' in result['artists'] and result['artists']['items']:
                seed_artists.append(result['artists']['items'][0]['id'])
            if len(seed_artists) >= 5:
                break

        # Generate recommendations
        track_uris = set()
        sample_tracks = []
        if seed_artists:
            logging.info(f"Generating recommendations with seed artists: {seed_artists}")
            results = safe_api_call(sp.recommendations, seed_artists=seed_artists, limit=30, **params)
            if results and 'tracks' in results:
                for track in results['tracks']:
                    if len(track_uris) < 30:
                        track_uris.add(track['uri'])
                        artist_names = ', '.join([artist['name'] for artist in track.get('artists', [])])
                        sample_tracks.append(f"{track['name']} - {artist_names}")

        # Fallback if not enough tracks
        if len(track_uris) < 30:
            logging.info("Not enough recommended tracks, using top tracks...")
            top_tracks = safe_api_call(sp.current_user_top_tracks, limit=30 - len(track_uris), time_range='short_term')
            if top_tracks and 'items' in top_tracks:
                for track in top_tracks['items']:
                    if len(track_uris) < 30:
                        track_uris.add(track['uri'])
                        artist_names = ', '.join([artist['name'] for artist in track.get('artists', [])])
                        sample_tracks.append(f"{track['name']} - {artist_names}")

        if len(track_uris) < 5:
            logging.error(f"Only found {len(track_uris)} tracks")
            return jsonify({"error": f"Could not find enough tracks. Found {len(track_uris)} tracks."}), 400

        # Create or update playlist
        playlist_name = f"My Playlist - {mood.capitalize()}"
        playlist = None
        playlists = safe_api_call(sp.current_user_playlists)
        if playlists and 'items' in playlists:
            for pl in playlists['items']:
                if pl.get('name') == playlist_name:
                    playlist = pl
                    break

        if not playlist:
            playlist = safe_api_call(sp.user_playlist_create,
                                    user=user_id,
                                    name=playlist_name,
                                    public=False,
                                    description=f"Playlist for mood: {mood}, artists: {', '.join(artist_names)}")
            if not playlist:
                logging.error("Failed to create playlist")
                return jsonify({"error": "Cannot create playlist"}), 403

        safe_api_call(sp.playlist_replace_items, playlist_id=playlist['id'], items=list(track_uris))
        logging.info(f"Playlist created/updated with {len(track_uris)} tracks")
        return jsonify({
            "message": "Playlist created or updated successfully",
            "playlist_url": playlist.get('external_urls', {}).get('spotify', ''),
            "track_count": len(track_uris),
            "sample_tracks": sample_tracks[:5],
            "mood": mood.capitalize()
        })

    except Exception as e:
        logging.error(f"Unexpected error in create_playlist: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

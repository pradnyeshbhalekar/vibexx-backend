import os
import logging
import random
from flask import Blueprint, request, redirect, url_for, render_template, jsonify
import urllib.parse
import traceback
import json
from flask_cors import CORS
from ytmusicapi import YTMusic
from transformers import pipeline
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import torch

playlist_bp = Blueprint('FMplaylist', __name__)
CORS(playlist_bp, supports_credentials=True, origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000"
], methods=['GET', 'POST'])

yt = YTMusic()
mood_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", top_k=1, framework="pt")

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="http://127.0.0.1:5000/callback",
        scope="playlist-modify-private playlist-modify-public user-read-private user-top-read"
    )

def get_token():
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            print(" Token from Authorization header")
            return spotipy.Spotify(auth=access_token)

        token_cookie = request.cookies.get("token")
        print("🔍 Raw cookie:", token_cookie)

        if not token_cookie:
            print(" No token cookie found.")
            return None

        try:
            decoded_token = urllib.parse.unquote(token_cookie)
            token_info = json.loads(decoded_token)
        except Exception as e:
            print(" Failed to parse token cookie:", e)
            return None

        oauth = get_spotify_oauth()
        if oauth.is_token_expired(token_info):
            try:
                token_info = oauth.refresh_access_token(token_info['refresh_token'])
            except Exception as e:
                print(" Failed to refresh token:", e)
                return None

        return spotipy.Spotify(auth=token_info['access_token'])
    except Exception as e:
        print(f"Error in get_token: {e}")
        return None

def analyze_mood_transformer(text, genres=None):
    if not text and not genres:
        return "Neutral"
    try:

        if genres:
            genres = [g.lower() for g in genres]
            print(f" Mood analysis (genres): Genres={genres}")
            happy_genres = ['pop', 'dance', 'upbeat', 'happy', 'bollywood', 'hip hop', 'r&b']
            sad_genres = ['blues', 'ballad', 'acoustic', 'sad']
            angry_genres = ['rock', 'metal', 'punk']
            for genre in genres:
                if any(hg in genre for hg in happy_genres):
                    return "Happy"
                elif any(sg in genre for sg in sad_genres):
                    return "Sad"
                elif any(ag in genre for ag in angry_genres):
                    return "Angry"


        if text:
            result = mood_classifier(text[:512])[0][0]
            label = result['label'].lower()
            score = result['score']
            print(f"🎭 Mood analysis (text): Label={label}, Score={score}, Text={text[:100]}...")
            if score >= 0.4:
                if label in ['joy', 'happiness', 'love']:
                    return "Happy"
                elif label in ['sadness', 'grief']:
                    return "Sad"
                elif label == 'anger':
                    return "Angry"
                else:
                    return "Neutral"
        return "Neutral"
    except Exception as e:
        print(f"Mood analysis error: {e}")
        return "Neutral"

def get_youtube_tracks(artist_name, mood, allowed_artists):
    try:
        mood_keywords = {
            "Happy": ["happy", "upbeat", "joyful", "dance"],
            "Sad": ["sad", "melancholy", "ballad", "slow"],
            "Angry": ["angry", "rock", "intense", "punk"],
            "Neutral": [""]
        }
        keyword = random.choice(mood_keywords[mood])
        query = f"from:{artist_name} {keyword}".strip()  
        search_results = yt.search(query, filter="songs", limit=30)
        print(f"🔍 Searching YouTube Music for: {query}, Results: {len(search_results)}")
        random.shuffle(search_results)
        tracks = []
        for result in search_results:
            if result['resultType'] == 'song' and 'title' in result and 'artists' in result:
                result_artist = result['artists'][0]['name'] if result['artists'] else artist_name

                if any(result_artist.lower() == allowed.lower() for allowed in allowed_artists):
                    tracks.append({
                        "title": result['title'],
                        "artist": result_artist,
                        "videoId": result.get('videoId')
                    })
        return tracks[:15]
    except Exception as e:
        print(f"Failed to search YouTube Music for {artist_name}: {e}")
        return []

def map_youtube_to_spotify(sp, youtube_track):
    try:

        query = f"track:{youtube_track['title']} artist:{youtube_track['artist']}"
        results = sp.search(q=query, type="track", limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            return {
                "title": track['name'],
                "artist": track['artists'][0]['name'],
                "spotify_uri": track['uri']
            }

        query = f"{youtube_track['title']} {youtube_track['artist']}"
        results = sp.search(q=query, type="track", limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            return {
                "title": track['name'],
                "artist": track['artists'][0]['name'],
                "spotify_uri": track['uri']
            }
        print(f" No Spotify match for {youtube_track['title']} by {youtube_track['artist']}")
        return None
    except Exception as e:
        print(f" Failed to map YouTube track to Spotify: {e}")
        return None

@playlist_bp.route('/top-artist')
def top_artist():
    sp = get_token()
    if sp is None:
        return redirect(url_for('spotify.login'))

    try:
        top_artists_data = sp.current_user_top_artists(limit=30, time_range='medium_term')
        artists = [{
            'name': artist['name'],
            'image': artist['images'][0]['url'] if artist['images'] else '',
            'genres': artist['genres'],
            'id': artist['id']
        } for artist in top_artists_data['items']]

        return render_template('top_artists.html', artists=artists)
    except Exception as e:
        logging.error("Error while fetching top artists:\n%s", traceback.format_exc())
        return "An error occurred while fetching top artists."

@playlist_bp.route('/top-artist-json')
def top_artist_json():
    sp = get_token()
    if sp is None:
        return jsonify({"error": "Authenticate again"}), 401

    try:
        top_artists_data = sp.current_user_top_artists(limit=20, time_range='medium_term')
        artists = [{
            'id': artist['id'],
            'name': artist['name'],
            'image': artist['images'][0]['url'] if artist['images'] else '',
            'genres': artist['genres'],
        } for artist in top_artists_data['items']]
        return jsonify(artists)
    except Exception as e:
        logging.error("Error while fetching top artists:\n%s", traceback.format_exc())
        return jsonify({"error": "An error occurred while fetching top artists."}), 500

@playlist_bp.route('/user-top', methods=['POST'])
def user_top():
    try:
        sp = get_token()
        if sp is None:
            return jsonify({"error": "Please authenticate again"}), 401

        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        print("Received data:", data)

        mood = data.get('mood')
        selected_artists = data.get('artists', [])

        valid_moods = ['Happy', 'Sad', 'Angry', 'Neutral']
        if not mood or mood not in valid_moods:
            return jsonify({"error": f"Invalid mood. Must be one of: {valid_moods}"}), 400

        if not selected_artists or not isinstance(selected_artists, list):
            return jsonify({"error": "No artists provided or invalid format"}), 400

        if len(selected_artists) == 0:
            return jsonify({"error": "At least one artist must be selected"}), 400

        matched_tracks = []
        seen_uris = set()  
        tracks_per_artist = 5
        allowed_artists = [artist['name'].lower() for artist in selected_artists]

        random.shuffle(selected_artists)
        valid_artist_ids = []
        for artist in selected_artists:
            artist_id = artist.get('id')
            try:
                artist_data = sp.artist(artist_id)
                valid_artist_ids.append({
                    'id': artist_id,
                    'name': artist_data['name'],
                    'genres': artist_data['genres']
                })
            except Exception as e:
                print(f" Invalid artist ID {artist_id}: {e}")


        for artist in valid_artist_ids:
            artist_id = artist['id']
            artist_name = artist['name']
            genres = artist['genres']
            youtube_tracks = get_youtube_tracks(artist_name, mood, allowed_artists)
            track_count = 0
            for yt_track in youtube_tracks:
                if track_count >= tracks_per_artist:
                    break
                spotify_track = map_youtube_to_spotify(sp, yt_track)
                if not spotify_track or spotify_track['spotify_uri'] in seen_uris:
                    continue
                detected_mood = analyze_mood_transformer(
                    f"{spotify_track['title']} by {spotify_track['artist']}", genres
                )
                print(f"🎵 Track: {spotify_track['title']}, Artist: {spotify_track['artist']}, "
                      f"Detected Mood: {detected_mood}, Target Mood: {mood}")
                if detected_mood == mood:
                    matched_tracks.append({
                        "title": spotify_track['title'],
                        "artist": spotify_track['artist'],
                        "spotify_uri": spotify_track['spotify_uri'],
                        "mood": detected_mood
                    })
                    seen_uris.add(spotify_track['spotify_uri'])
                    track_count += 1


        if len(matched_tracks) < 20:
            print(f" Only {len(matched_tracks)} tracks matched for {mood}. Fetching more from YouTube...")
            for artist in valid_artist_ids:
                youtube_tracks = get_youtube_tracks(artist['name'], mood, allowed_artists)
                for yt_track in youtube_tracks[:10]:
                    spotify_track = map_youtube_to_spotify(sp, yt_track)
                    if not spotify_track or spotify_track['spotify_uri'] in seen_uris:
                        continue
                    detected_mood = analyze_mood_transformer(
                        f"{spotify_track['title']} by {spotify_track['artist']}", artist['genres']
                    )
                    if detected_mood == mood:
                        matched_tracks.append({
                            "title": spotify_track['title'],
                            "artist": spotify_track['artist'],
                            "spotify_uri": spotify_track['spotify_uri'],
                            "mood": detected_mood
                        })
                        seen_uris.add(spotify_track['spotify_uri'])

        if not matched_tracks:
            return jsonify({"error": f"No tracks found matching the {mood} mood"}), 400

        random.shuffle(matched_tracks)
        matched_tracks = matched_tracks[:30]

        playlist_name = data.get('playlist_name', f"Top Artist Mood - {mood}")
        user_id = sp.me()['id']
        playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=False)

        track_uris = [track['spotify_uri'] for track in matched_tracks]
        if track_uris:
            sp.playlist_add_items(playlist_id=playlist['id'], items=track_uris)

        return jsonify({
            "playlist_url": playlist['external_urls']['spotify'],
            "matched": matched_tracks
        })

    except Exception as e:
        logging.error("Error in user_top: %s", traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500
    
    
@playlist_bp.route('/playlist/<playlist_id>', methods=['GET'])
def get_playlist(playlist_id):
    try:
        sp = get_token()
        if sp is None:
            return jsonify({"error": "Please authenticate again"}), 401


        playlist = sp.playlist(playlist_id, fields="name,external_urls,tracks(items(track(name,artists(name),uri)))")
        tracks = [
            {
                "title": item['track']['name'],
                "artist": item['track']['artists'][0]['name'],
                "spotify_uri": item['track']['uri']
            }
            for item in playlist['tracks']['items']
        ]
        return jsonify({
            "name": playlist['name'],
            "playlist_url": playlist['external_urls']['spotify'],
            "tracks": tracks
        })
    except Exception as e:
        logging.error("Error fetching playlist: %s", traceback.format_exc())
        return jsonify({"error": f"Failed to fetch playlist: {str(e)}"}), 500
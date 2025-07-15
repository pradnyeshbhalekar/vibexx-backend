from flask import Blueprint,request,jsonify
from flask_cors import CORS
from spotipy.oauth2 import SpotifyOAuth
import os
from extension import mongo 
import spotipy
from datetime import date,datetime
import json
import requests
import urllib.parse


# db
def get_audio_feature_collection():
    return mongo.db.audio_features

def get_usage_collection():
    return mongo.db.usage



vibeplaylist_bp = Blueprint('vibeplaylist',__name__, url_prefix='/vibeplaylist')


CORS(vibeplaylist_bp,supports_credentials=True,origins=[
    'http://localhost:3000'
])


# rapid api keys
spotify_audio_feature_host = os.getenv('RAPID_API_HOST')
spotify_audio_feature_url = os.getenv('RAPID_SPOTIFY_AUDIO_FEATURE_ENDPOINT')
spotify_audio_feature_key = os.getenv('RAPID_API_KEY')

# mongo uri keys
mongo_uri_keys = os.getenv('MONGO_URI')


def get_spotify_oauth():
    return(
        SpotifyOAuth(
            client_id = os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret = os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')  
        )
    )

def get_token():
    try:

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            sp = spotipy.Spotify(auth=access_token)
            try:
                sp.current_user()
                print(" Token is valid via Authorization header")
                return sp
            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 401:
                    print(" Access token expired")
                    return None
                raise


        token_cookie = request.cookies.get("token")
        print("Raw Cookie:", token_cookie)  
        if not token_cookie:
            print("❌ No token cookie found")
            return None

        decoded_token = urllib.parse.unquote(token_cookie)
        print("Decoded Token:", decoded_token)  

        token_info = json.loads(decoded_token)

        oauth = get_spotify_oauth()
        if oauth.is_token_expired(token_info):
            token_info = oauth.refresh_access_token(token_info['refresh_token'])

        print(" Token is valid via Cookie")
        return spotipy.Spotify(auth=token_info['access_token'])

    except Exception as e:
        print(f" Error in get_token: {e}")
        return None


def can_make_rapid_api_call():
    usage_collection = get_usage_collection()
    today = date.today().isoformat()
    usage = usage_collection.find_one({"date": today})
    print(f"[USAGE CHECK] Usage today: {usage}")

    if not usage:
        print("[USAGE] No usage today, creating entry.")
        usage_collection.insert_one({"date": today, "count": 1})
        return True
    elif usage["count"] < 20:
        print(f"[USAGE] Current count: {usage['count']}, incrementing.")
        usage_collection.update_one({"date": today}, {"$inc": {"count": 1}})
        return True
    print("[USAGE] Daily limit reached.")
    return False


def match_mood(mood,audio_feature):

    try:
        valence = float(audio_feature.get("valence"))
        danceability = float(audio_feature.get("danceability"))
        energy = float(audio_feature.get("energy"))
        speechiness = float(audio_feature.get("speechiness"))
        loudness = float(audio_feature.get("loudness"))
        acousticness = float(audio_feature.get("acousticness"))
        instrumentalness = float(audio_feature.get("instrumentalness"))
        liveness = float(audio_feature.get("liveness"))
        mode = float(audio_feature.get("mode"))
        tempo = float(audio_feature.get("tempo"))

        mood_creteria = {

            "Roadtrip": [
                liveness >= 0.9,
                tempo >= 100,
                loudness >= -5,
                valence >= 0.5,
                acousticness <= 0.4,
                danceability >= 0.6,
                energy >= 0.7,
                mode == 1
            ],

            "Romantic": [
                danceability >= 0.5,
                energy <= 0.7,
                loudness <= -5,
                speechiness >= 0.05,
                acousticness >= 0.08,
                instrumentalness > 0,
                valence >= 0.5,
                tempo <= 100,
                mode == 0
            ],
            "Inspirational" : [
                danceability >= 0.4,
                energy >= 0.6,
                valence >= 0.4,
                instrumentalness >= 0.3,
                acousticness >= 0.2,
                speechiness <= 0.1,
                loudness >= -6,
                tempo >= 90,
                mode == 1
            ],
            "Energetic" : [
                danceability >= 0.75,
                energy >= 0.85,
                valence >= 0.6,
                tempo >= 120,
                loudness >= -5,
                speechiness <= 0.1,
                mode == 1
            ],
            "Focus" : [
                instrumentalness >= 0.6,
                energy <= 0.5,
                speechiness <=0.05,
                acousticness >= 0.4,
                loudness <= -7,
                tempo <=90,
                valence <=0.5,
                mode == 0
            ],
            "Cozy":[
                acousticness >= 0.6,
                energy <=0.5,
                valence >=0.4,
                tempo <=100,
                speechiness <=0.08,
                instrumentalness >=0.2,
                liveness <=0.2,
                danceability >=0.5,
                mode == 0
            ],
            "Party":[
                danceability >= 0.8,
                energy >=0.85,
                valence >=0.75,
                speechiness >=0.05,
                liveness >= 0.3,
                acousticness <=0.3,
                loudness >= -5,
                mode == 1 
            ]
         }
        
        if mood in mood_creteria:
            return all(mood_creteria[mood])
        else:
            return False
        
    except Exception as e:
        return False
    



def get_audio_features(track_id, artist_id=None):
    audio_feature_collection = get_audio_feature_collection()
    

    cached = audio_feature_collection.find_one({"track_id": track_id, "artist_id": artist_id})
    if cached:
        return cached.get("audio_features")


    url = spotify_audio_feature_url
    headers = {
        "x-rapidapi-host": spotify_audio_feature_host,
        "x-rapidapi-key": spotify_audio_feature_key
    }
    params = {
        "spotify_track_id": track_id
    }


    features = None  
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            raw_features = data.get("audio_feature")
            if raw_features:
                features = {
                    k: float(v) if k not in ['key', 'duration'] else v
                    for k, v in raw_features.items()
                }


                audio_feature_collection.insert_one({
                    "track_id": track_id,
                    "artist_id": artist_id,
                    "audio_features": features,
                    "created_at": datetime.utcnow()
                })
            else:
                print(f" No audio features found in response for track {track_id}")
        else:
            print(f"Failed to fetch features for track {track_id}: {response.status_code}")
    except Exception as e:
        print(f" Exception in get_audio_features: {e}")
    
    return features  



@vibeplaylist_bp.route('/create',methods=['POST'])
def create_playlist():
    sp = get_token()
    audio_feature_collection = get_audio_feature_collection()
    if sp is None:
        return jsonify({"error":"Authentication failed"},401)
    
    try:
        data = request.get_json()
        selected_artists = data.get('artists', [])
        vibe = data.get("vibe","")

        if not selected_artists or not vibe:
            return jsonify({'error':"No artist was selected or no vibe was selected, Please try again!"},400)
        
        matched_tracks = []

        artists_id = selected_artists.get('id', []) if isinstance(selected_artists, dict) else selected_artists


        for artist_id in artists_id:
            try:

                top_tracks = sp.artist_top_tracks(artist_id)["tracks"]
                for track in top_tracks:
                    track_id = track["id"]

                    cached = audio_feature_collection.find_one({
                        "artist_id":artist_id,
                        "track_id":track_id

                    })

                    features = cached.get("audio_features") if cached else None
                    print(features)

                    if not features:
                        print(f"Checking API usage for track {track_id}")
                        if can_make_rapid_api_call():
                            features = get_audio_features(track_id, artist_id)
                        else:
                            print("skipping track due to api limit")
                            continue


                   
                    if features and match_mood(vibe,features):
                        matched_tracks.append({
                            "id":track_id,
                            "name":track["name"],
                            "artist_name": track["artists"][0]['name'],
                            "track_cover": track['album']["images"][0]['url'] if track['album']['images'] else None
                        })
            except Exception as e:
                print(f"Error with artist {artist_id}: {e}")
        return jsonify({"matched_tracks":matched_tracks})
    except Exception as e:
        print(f"Error while creating playlist: {e} ")
        return jsonify({"error":"something went wrong"}),500


import essentia.standard as es
import os

def extract_audio_features(wav_path,song_name='unknowm',track_id=None):
    if not os.path.exists(wav_path):
        return None
    
    try:
        audio = es.MonoLoader(filename=wav_path)()
        features, _ = es.MusicExtractor(
            lowlevelStats = ['mean'],
            rhythmStats = ['mean'],
            tonalStats = ['mean'],
            highlevelStats= ['mean']
        )(audio)

        return{
            "track_id":track_id or song_name,
            "song": song_name,
            "tempo": round(float(features['rhythm.bpm']),3),
            "valence": round(float(features['highlevel']['valence']['mean']),3),
            "energy": round(float(features['highlevel']['energy']['mean']),3),
            "loudness": round(float(features['highlevel']['loudness']['mean'],3)),
            "speechiness": round(float(features['highlevel']['speechiness'],3)),
            "acoustiness": round(float(features['highlevel']['acoustiness'],3)),
            "instrumental": round(float(features['highlevel']['instrumental'],3)),
            "liveness": round(float(features['highlevel']['liveness'],3)),
            "danceability":round(float(features['highlevel']['danceability'],3)),
            "loudness":round(float(features['highlevel']['loudness'],3)),
            "key":features['tonal.key_key'],
            "mode": 1.0 if features["tonal.key_scale"] == "major" else 0.0

        }
    except Exception as e:
        print(f'Error: Feature extraction failed {e}')
        return None
    
import concurrent.futures
import os
from audio_feature.extracter import extract_audio_features
from audio_feature.downloader import download_song
from extension import mongo

db = mongo.cx['vibexx']
collection = mongo.db['audio_features']

def process_songs(song_list, output_dir = "downloads",max_thread=4):
    os.makedirs(output_dir,exist_ok=True)

    def process_single(song_info):
        song_name,track_id,artist_name = song_info
        full_name = f"{song_name} - {artist_name}"

        exisiting = collection.find_one({'track_id':track_id})
        if exisiting:
            print (f"Found in DB: {track_id}")
            return exisiting
        
        wav_path = download_song(song_name,artist_name,output_dir)
        if wav_path:
            try:
                extracted_audio_feature = extract_audio_features(wav_path,song_name,track_id)

                if extracted_audio_feature:
                    collection.insert_one(extracted_audio_feature)
                    return extracted_audio_feature
            finally:
                try:
                    os.remove(wav_path)
                    os.remove(wav_path.replace(".wav",".mp3"))

                except Exception as e:
                    print(f"Cleanin up failed: {e}")

        return None
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_thread) as extractor :
        futures = [extractor.submit(process_single,song) for song in song_list]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    return results
        
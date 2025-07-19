import subprocess
import re
import os
import yt_dlp


def slugify(text):
    return re.sub(r'[^\w\-]','_',text)

def get_song_filename(song_name,artist_name):
    base = slugify(f"{song_name}_{artist_name}")
    return f"{base}.wav", f"{base}.mp3"

def get_youtube_url(query):
    try:
       ydl_opts = {
           'quiet' : True,
           'default_search':'ytsearch1',
           'skip_download' : True,
           'extract_flat' : 'in_playlist'
       }
       with yt_dlp.YoutubeDL(ydl_opts) as ydl:
           info = ydl.extract_info(query,download=False)
           return info['entries'][0]['url'] if 'entries' in info else info['url']
    except Exception as e:
        print(f"Error: youtube url cannot be fetched for {query} : {e}")
        return None
    
def download_song(song_name,artist_name,output_dir = "downloads"):
    os.mkdir(output_dir,exist_ok = True)
    query = f"{song_name} {artist_name}"
    mp3_name,wav_name =  get_song_filename(song_name,artist_name)
    mp3_path = os.path.join(output_dir,mp3_name)
    wav_path = os.path.join(output_dir,wav_name)

    try:
        url = get_youtube_url(query)
        if not url:
            return None
        
        ydl_opts = {
            'format': "bestaudio/best",
            'outtmpl': mp3_path,
            'postprocessors':[{
                'key':'FFmpegExtractAudio',
                'prefferedcodec':'mp3',
                'prefferedquality':'192'
            }],
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        subprocess.run(['ffmpeg','-y','-i',mp3_path,wav_path],check=True)
        return wav_path
    
    except Exception as e:
        print(f'Error: Problem while downloading {e}')
        return None

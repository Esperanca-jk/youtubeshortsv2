import os
import random
import subprocess
from datetime import datetime
import wikipediaapi
from gtts import gTTS
from pexels_api import API
import requests
from mutagen.mp3 import MP3
import youtube_uploader

# --- AYARLAR ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # GitHub Actions Ubuntu'da varsayılan font yolu

# --- DOSYA İSİMLERİ ---
AUDIO_FILE = "audio.mp3"
BACKGROUND_VIDEO = "background.mp4"
FINAL_VIDEO = "output.mp4"

def get_todays_event():
    """Wikipedia'dan günün olayını çeker."""
    # HATA DÜZELTMESİ: Wikipedia API için user_agent eklendi.
    wiki = wikipediaapi.Wikipedia(user_agent='WhatHappenedTodayBot/1.0', language='en')
    
    today = datetime.now()
    # İngilizce Wikipedia sayfa formatı farklı olabilir, bu en yaygın olanıdır
    page_title = f"Portal:Current events/On this day/{today.strftime('%B')} {today.day}"
    
    page = wiki.page(page_title)
    if not page.exists():
        # Fallback to a different common format if the first one fails
        page_title = f"Wikipedia:Selected anniversaries/{today.strftime('%B')} {today.day}"
        page = wiki.page(page_title)
        if not page.exists():
            return "No notable event could be found for today."
        
    # İçerik işlemesi İngilizce yapıya göre daha basit olabilir
    events = page.text.split('Events\n')[1].split('\n') if 'Events\n' in page.text else page.text.split('\n')

    valid_events = [e.strip() for e in events if e.strip() and e.startswith('*')]
    
    if not valid_events:
        return "No notable event could be found for today."

    # Baştaki '*' karakterini temizle
    return random.choice(valid_events).lstrip('* ').strip()

def generate_audio(text, filename=AUDIO_FILE):
    """Verilen metni ses dosyasına çevirir."""
    print("Ses dosyası oluşturuluyor...")
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(filename)
    audio = MP3(filename)
    print(f"Ses dosyası oluşturuldu. Süre: {audio.info.length:.2f} saniye")
    return filename, audio.info.length

def get_background_video(query="history abstract", filename=BACKGROUND_VIDEO):
    """Pexels API kullanarak dikey bir arkaplan videosu bulur ve indirir."""
    print("Arka plan videosu aranıyor...")
    api_key = os.environ.get('PEXELS_API_KEY')
    if not api_key:
        raise ValueError("PEXELS_API_KEY ortam değişkeni bulunamadı.")
        
    headers = {'Authorization': api_key}
    params = {'query': query, 'orientation': 'portrait', 'per_page': 15}
    url = 'https://api.pexels.com/videos/search'
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # HTTP hatalarını kontrol et
        data = response.json()
        
        videos = data.get('videos')
        if not videos:
            raise Exception(f"Pexels'ta '{query}' için uygun arkaplan videosu bulunamadı.")

        video_data = random.choice(videos)
        
        # En uygun video dosyasını bul (genellikle 'hd' kalitesinde olan iyidir)
        video_url = None
        for file_info in video_data.get('video_files', []):
            if 'hd' in file_info.get('quality', ''):
                video_url = file_info.get('link')
                break
        
        # Eğer HD kalitede bulamazsa ilk bulduğunu alsın
        if not video_url:
            video_url = video_data.get('video_files', [])[0].get('link')

        print(f"Video indiriliyor: {video_url}")
        video_response = requests.get(video_url)
        video_response.raise_for_status()
        
        with open(filename, 'wb') as f:
            f.write(video_response.content)
            
        print("Arka plan videosu indirildi.")
        return filename
    
    except requests.exceptions.RequestException as e:
        print(f"Pexels API'ye bağlanırken hata oluştu: {e}")
        raise

def create_video(event_text, audio_duration, bg_video=BACKGROUND_VIDEO, output_file=FINAL_VIDEO):
    """FFmpeg kullanarak son videoyu oluşturur."""
    print("FFmpeg ile video sentezleniyor...")
    
    # Metni ekranda daha iyi göstermek için satırlara böl
    # Her satırda yaklaşık 30 karakter olacak şekilde ayarla
    words = event_text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) < 30:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())
    formatted_text = "\\\n".join(lines)


    command = [
        'ffmpeg', '-y',
        '-i', bg_video,
        '-i', AUDIO_FILE,
        '-filter_complex', f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1[bg];"
                         f"[bg]drawtext=fontfile='{FONT_PATH}':text='{formatted_text}':fontcolor=white:fontsize=70:box=1:boxcolor=black@0.6:boxborderw=15:x=(w-text_w)/2:y=(h-text_h)/2[video]",
        '-map', '[video]',
        '-map', '1:a',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        '-t', str(audio_duration + 0.5), # Ses süresinden biraz uzun
        '-r', str(VIDEO_FPS),
        output_file
    ]

    subprocess.run(command, check=True)
    print(f"Video başarıyla oluşturuldu: {output_file}")
    return output_file
    
def cleanup_files():
    """Oluşturulan geçici dosyaları siler."""
    print("Geçici dosyalar siliniyor...")
    for file in [AUDIO_FILE, BACKGROUND_VIDEO, FINAL_VIDEO]:
        if os.path.exists(file):
            os.remove(file)
    print("Temizlik tamamlandı.")


if __name__ == "__main__":
    try:
        # 1. Veri Çek
        event = get_todays_event()
        print(f"Bugünün olayı: {event}")
        
        # 2. Ses Üret
        audio_file, duration = generate_audio(event)
        
        # 3. Arka Plan Videosu Bul
        # Olay metninden anahtar kelime çıkarmak yerine genel bir arama yapalım
        background_video_file = get_background_video(query="history abstract")
        
        # 4. Videoyu Oluştur
        final_video_file = create_video(event, duration)
        
        # 5. YouTube'a Yükle
        today_str = datetime.now().strftime("%B %d, %Y")
        title = f"On This Day - {today_str} #shorts"
        description = f"{event}\n\n#onthisday #history #todayinhistory #shorts"
        tags = ["onthisday", "history", "education", "shorts"]
        
        youtube_uploader.upload_video(final_video_file, title, description, tags)
        
    except Exception as e:
        print(f"Ana işlem sırasında bir hata oluştu: {e}")
    finally:
        # 6. Temizlik
        cleanup_files()
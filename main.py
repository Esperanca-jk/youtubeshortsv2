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
FONT_PATH = "./Roboto-Bold.ttf" # GitHub Actions Ubuntu'da varsayılan font yolu

# --- DOSYA İSİMLERİ ---
AUDIO_FILE = "audio.mp3"
BACKGROUND_VIDEO = "background.mp4"
FINAL_VIDEO = "output.mp4"

def get_todays_event():
    """
    Wikipedia (EN) 'Selected anniversaries' sayfasının Events bölümünden,
    bugünün (UTC) rastgele bir olayını döndürür. Harici kütüphane gerekmez.
    """
    import re
    import requests
    from datetime import datetime, timezone


    USER_AGENT = "WhatHappenedTodayBot/1.0 (contact: you@example.com)"
    API_URL = "https://en.wikipedia.org/w/api.php"
    MONTHS_EN = ["","January","February","March","April","May","June",
                 "July","August","September","October","November","December"]

    now = datetime.now(timezone.utc)
    page_title = f"Wikipedia:Selected anniversaries/{MONTHS_EN[now.month]} {now.day}"

    def mw_get(params):
        r = requests.get(API_URL, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        return r.json()

    # 1) 'Events' bölüm indexini bul
    sec = mw_get({"action":"parse","page":page_title,"prop":"sections","format":"json"})
    if "error" in sec:
        return "No notable event could be found for today."

    events_index = None
    for s in sec.get("parse", {}).get("sections", []):
        if s.get("line","").strip().lower() == "events":
            events_index = s.get("index")
            break

    # 2) Events wikitext (varsa), yoksa tüm sayfa wikitext
    if events_index is not None:
        part = mw_get({"action":"parse","page":page_title,
                       "prop":"wikitext","section":events_index,"format":"json"})
        wt = (part.get("parse", {}).get("wikitext", {}) or {}).get("*")
    else:
        whole = mw_get({"action":"parse","page":page_title,
                        "prop":"wikitext","format":"json"})
        wt = (whole.get("parse", {}).get("wikitext", {}) or {}).get("*")

    if not wt:
        # Fallback: bazen başka sayfa formatı
        alt_title = page_title.replace("Wikipedia:Selected anniversaries/", "Portal:Current events/On this day/")
        whole = mw_get({"action":"parse","page":alt_title,"prop":"wikitext","format":"json"})
        wt = (whole.get("parse", {}).get("wikitext", {}) or {}).get("*")
        if not wt:
            return "No notable event could be found for today."

    # 3) Bullet maddeleri çek
    lines = [ln.strip() for ln in wt.splitlines() if ln.strip().startswith("*")]
    if not lines:
        return "No notable event could be found for today."

    # 4) Temizlik
    def clean(text):
        # {{...}} şablonları (basit)
        for _ in range(5):
            text = re.sub(r"\{\{[^{}]*\}\}", "", text)
        # [[Hedef|Etiket]] -> Etiket; [[Hedef]] -> Hedef
        text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        # <ref>…</ref>, <ref .../>, diğer HTML etiketleri
        text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
        text = re.sub(r"<ref[^>]*/>", "", text)
        text = re.sub(r"</?[^>]+>", "", text)
        # HTML entity'ler ve boşluklar
        text = text.replace("&nbsp;"," ").replace("&amp;","&")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    bullets = [clean(ln.lstrip("* ").strip()) for ln in lines]
    bullets = [b for b in bullets if b]

    if not bullets:
        return "No notable event could be found for today."

    # 5) Rastgele bir olay döndür
    import random
    return random.choice(bullets)


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
        response.raise_for_status()
        data = response.json()
        
        videos = data.get('videos')
        if not videos:
            raise Exception(f"Pexels'ta '{query}' için uygun arkaplan videosu bulunamadı.")

        video_data = random.choice(videos)
        
        video_url = None
        video_files = video_data.get('video_files', [])
        
        # --- GÜNCELLENEN GÜVENLİ KONTROL ---
        # Önce 'hd' kalitesinde video arayalım
        for file_info in video_files:
            quality = file_info.get('quality') # Kalite bilgisini al (None olabilir)
            # Kalite boş değilse VE 'hd' içeriyorsa linki al
            if quality and 'hd' in quality:
                video_url = file_info.get('link')
                break
        
        # Eğer 'hd' kalitede video bulunamazsa veya liste boşsa, mevcut ilk videoyu al
        if not video_url and video_files:
            video_url = video_files[0].get('link')

        if not video_url:
            raise Exception("Videoya ait indirilebilir bir link bulunamadı.")

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

    sanitized_text = formatted_text.replace("'", "").replace(":", "-")

    command = [
        'ffmpeg', '-y',
        '-i', bg_video,
        '-i', AUDIO_FILE,
        '-filter_complex', f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1[bg];"
                         f"[bg]drawtext=fontfile='{FONT_PATH}':text='{sanitized_text}':fontcolor=white:fontsize=70:box=1:boxcolor=black@0.6:boxborderw=15:x=(w-text_w)/2:y=(h-text_h)/2[video]",
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
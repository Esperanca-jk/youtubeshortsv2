import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# API bilgileri
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

def get_credentials():
    """
    GitHub Actions'daki environment variables (ortam değişkenleri) üzerinden
    kimlik bilgilerini alır ve Credentials nesnesi oluşturur.
    """
    client_secrets_str = os.environ.get('YOUTUBE_CLIENT_SECRETS')
    refresh_token = os.environ.get('YOUTUBE_REFRESH_TOKEN')

    if not client_secrets_str or not refresh_token:
        raise ValueError("Kimlik bilgileri (YOUTUBE_CLIENT_SECRETS veya YOUTUBE_REFRESH_TOKEN) bulunamadı.")

    client_config = json.loads(client_secrets_str)['installed']
    
    credentials = Credentials(
        None,  # Access token boş, çünkü refresh token ile yenilenecek
        refresh_token=refresh_token,
        token_uri=client_config['token_uri'],
        client_id=client_config['client_id'],
        client_secret=client_config['client_secret'],
        scopes=['https://www.googleapis.com/auth/youtube.upload']
    )
    return credentials

def upload_video(video_file_path, title, description, tags):
    """
    Verilen videoyu YouTube'a yükler.
    """
    try:
        credentials = get_credentials()
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

        request_body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22' # Kategori ID'si (22: People & Blogs)
            },
            'status': {
                'privacyStatus': 'public',  # 'private', 'unlisted' veya 'public'
                'selfDeclaredMadeForKids': False
            }
        }

        media_file = MediaFileUpload(video_file_path, chunksize=-1, resumable=True)

        print(f"'{video_file_path}' YouTube'a yükleniyor...")
        
        response_upload = youtube.videos().insert(
            part='snippet,status',
            body=request_body,
            media_body=media_file
        ).execute()
        
        video_id = response_upload.get('id')
        print(f"Video başarıyla yüklendi! Video ID: {video_id}")
        print(f"İzleme linki: https://www.youtube.com/watch?v={video_id}")

        return video_id

    except Exception as e:
        print(f"Video yüklenirken bir hata oluştu: {e}")
        return None
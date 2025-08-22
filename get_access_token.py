import os
import google_auth_oauthlib.flow

# Bu script'i YEREL MAKİNENİZDE bir kez çalıştırarak
# GitHub Actions'a eklemeniz gereken YOUTUBE_REFRESH_TOKEN'ı alacaksınız.

# Gerekli API yetki kapsamı
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = "s.json"

def get_refresh_token():
    """
    Kullanıcıyı tarayıcıya yönlendirerek yetkilendirme yapar ve
    gelecekteki otomatik işlemler için bir refresh token üretir.
    """
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"HATA: '{CLIENT_SECRETS_FILE}' dosyası bu dizinde bulunamadı!")
        print("Lütfen Google Cloud Console'dan indirip bu script ile aynı yere koyun.")
        return

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)
    
    # Bu fonksiyon tarayıcıda bir yetkilendirme sayfası açacak.
    # Google hesabınızla giriş yapıp izin vermeniz gerekiyor.
    credentials = flow.run_local_server(port=0)

    print("\n" + "="*50)
    print("YETKİLENDİRME BAŞARILI!")
    print("Aşağıdaki 'refresh_token' değerini kopyalayın.")
    print("Bu değeri GitHub reponuzdaki Actions Secrets bölümüne")
    print("'YOUTUBE_REFRESH_TOKEN' adıyla ekleyin.")
    print("="*50)
    print(f"\n{credentials.refresh_token}\n")
    print("="*50)

if __name__ == '__main__':
    get_refresh_token()
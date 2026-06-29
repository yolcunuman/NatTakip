"""
============================================================
  Gazi Üniversitesi Tıp Fakültesi - Duyuru Takip Botu
  (GitHub Actions + E-posta Bildirimi Versiyonu)
============================================================
  Bu bot, GitHub Actions tarafından her 15 dakikada bir
  otomatik olarak çalıştırılır. Yeni duyuru tespit edildiğinde
  Gmail üzerinden e-posta bildirimi gönderir.

  ÖNEMLİ: Bu kodu kendi bilgisayarında çalıştırman gerekmez.
  GitHub Actions bulutta otomatik çalıştırır.

  Gerekli kütüphaneler:
    pip install requests beautifulsoup4
============================================================
"""

# ============================================================
# 1. BÖLÜM: Gerekli Kütüphanelerin İçe Aktarılması
# ============================================================
import requests                  # Web sayfasına HTTP isteği göndermek için
from bs4 import BeautifulSoup    # HTML içeriğini ayrıştırmak (parse etmek) için
import os                        # Dosya işlemleri ve ortam değişkenleri için
import sys                       # Çıkış kodları için (GitHub Actions hata tespiti)
import smtplib                   # E-posta göndermek için (Python'un yerleşik kütüphanesi)
from email.mime.text import MIMEText          # E-posta içeriği oluşturmak için
from email.mime.multipart import MIMEMultipart  # Çok parçalı e-posta için
from datetime import datetime    # Zaman damgası (log mesajları) için


# ============================================================
# 2. BÖLÜM: Sabit Değişkenler (Ayarlar)
# ============================================================

# Takip edilecek duyuru sayfasının URL'si
DUYURU_URL = "https://med.gazi.edu.tr/view/announcement-list"

# Son kontrol edilen duyurunun ID'sini saklayacağımız dosya.
# Bu dosya repo içinde tutulur ve GitHub Actions her çalışmada
# güncellerse değişikliği repo'ya geri commit eder.
HAFIZA_DOSYASI = "son_duyuru_id.txt"

# Gerçekçi bir tarayıcı gibi görünmek için User-Agent başlığı.
# Bazı siteler, User-Agent olmadan gelen istekleri bot olarak algılayıp engelleyebilir.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ============================================================
# 3. BÖLÜM: E-posta Ayarları (GitHub Secrets'tan Okunur)
# ============================================================
# Bu değerler GitHub Secrets'a eklenir ve GitHub Actions
# tarafından ortam değişkeni (environment variable) olarak
# koda aktarılır. Kodun içine asla şifre yazmıyoruz!
#
# Gerekli GitHub Secrets:
#   GMAIL_ADRES    → Gönderici Gmail adresi (örn: benimadim@gmail.com)
#   GMAIL_SIFRE    → Gmail Uygulama Şifresi (16 haneli, boşluksuz)
#   ALICI_EMAIL    → Bildirimin gönderileceği e-posta adresi

GMAIL_ADRES = os.environ.get("GMAIL_ADRES", "")
GMAIL_SIFRE = os.environ.get("GMAIL_SIFRE", "")
ALICI_EMAIL = os.environ.get("ALICI_EMAIL", "")


# ============================================================
# 4. BÖLÜM: E-posta Bildirim Fonksiyonu
# ============================================================
def email_bildirim_gonder(konu, icerik):
    """
    Gmail SMTP sunucusu üzerinden e-posta bildirimi gönderir.

    Parametreler:
        konu (str)   : E-postanın konu başlığı
        icerik (str) : E-postanın gövde metni

    Gmail Uygulama Şifresi Nasıl Alınır:
    ─────────────────────────────────────
    1. Google hesabına gir: https://myaccount.google.com
    2. "Güvenlik" sekmesine git
    3. "2 Adımlı Doğrulama"yı aç (zaten açıksa atla)
    4. "2 Adımlı Doğrulama" sayfasının en altında "Uygulama şifreleri" bölümünü bul
       Veya doğrudan: https://myaccount.google.com/apppasswords
    5. Uygulama adı olarak "DuyuruBot" yaz ve "Oluştur"a tıkla
    6. Google sana 16 haneli bir şifre verecek (örn: abcd efgh ijkl mnop)
    7. Bu şifreyi boşluksuz olarak GitHub Secrets'a GMAIL_SIFRE olarak ekle
    """
    # E-posta bilgileri eksikse uyarı ver
    if not GMAIL_ADRES or not GMAIL_SIFRE or not ALICI_EMAIL:
        print("⚠️ E-posta ayarları eksik! GitHub Secrets'ı kontrol edin.")
        print("   Gerekli: GMAIL_ADRES, GMAIL_SIFRE, ALICI_EMAIL")
        return False

    try:
        # E-posta mesajını oluştur
        mesaj = MIMEMultipart()
        mesaj["From"] = GMAIL_ADRES       # Gönderen
        mesaj["To"] = ALICI_EMAIL         # Alıcı
        mesaj["Subject"] = konu           # Konu başlığı

        # E-posta gövdesini ekle (düz metin olarak)
        mesaj.attach(MIMEText(icerik, "plain", "utf-8"))

        # Gmail SMTP sunucusuna bağlan ve e-postayı gönder
        # Gmail SMTP: smtp.gmail.com, Port: 587 (TLS şifreli)
        with smtplib.SMTP("smtp.gmail.com", 587) as sunucu:
            sunucu.starttls()                          # Şifreli bağlantı başlat
            sunucu.login(GMAIL_ADRES, GMAIL_SIFRE)     # Giriş yap
            sunucu.send_message(mesaj)                 # E-postayı gönder

        print("✅ E-posta bildirimi başarıyla gönderildi!")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail giriş hatası! Uygulama şifresini kontrol edin.")
        print("   (Normal Gmail şifresi değil, 'Uygulama Şifresi' gereklidir)")
        return False
    except Exception as hata:
        print(f"❌ E-posta gönderim hatası: {hata}")
        return False


# ============================================================
# 5. BÖLÜM: Hafıza Dosyası İşlemleri
# ============================================================
def son_kaydedilen_id_oku():
    """
    Hafıza dosyasından (son_duyuru_id.txt) en son kaydedilen
    duyuru ID'sini okur.

    Eğer dosya henüz yoksa (ilk çalıştırma), None döndürür.
    """
    if os.path.exists(HAFIZA_DOSYASI):
        with open(HAFIZA_DOSYASI, "r", encoding="utf-8") as dosya:
            icerik = dosya.read().strip()  # Boşlukları temizle
            return icerik if icerik else None
    return None


def id_kaydet(duyuru_id):
    """
    Verilen duyuru ID'sini hafıza dosyasına (son_duyuru_id.txt) yazar.
    Bir sonraki kontrolde bu ID ile karşılaştırma yapılacaktır.
    """
    with open(HAFIZA_DOSYASI, "w", encoding="utf-8") as dosya:
        dosya.write(duyuru_id)


# ============================================================
# 6. BÖLÜM: Duyuru Sayfasını Kontrol Etme
# ============================================================
def duyurulari_kontrol_et():
    """
    Duyuru sayfasına istek atar, HTML içeriğini parse eder ve
    en güncel duyuruyu döndürür.

    Döndürdüğü değer bir sözlük (dict):
      {
        "id": "listAnnouncement320075",
        "baslik": "YDUS Sınav Sonuçları",
        "tarih": "28.06.2026",
        "link": "https://..."
      }

    Hata durumunda None döndürür.
    """
    try:
        # Sayfaya GET isteği gönder (10 saniye zaman aşımı ile)
        yanit = requests.get(DUYURU_URL, headers=HEADERS, timeout=10)

        # HTTP durum kodunu kontrol et (200 = Başarılı)
        if yanit.status_code != 200:
            print(f"⚠️ Sayfa yüklenemedi. HTTP Durum Kodu: {yanit.status_code}")
            return None

        # HTML içeriğini BeautifulSoup ile parse et
        soup = BeautifulSoup(yanit.text, "html.parser")

        # Duyuru div'lerini bul
        # Her duyurunun class'ı: "row subpage-ann-single flex-nowrap"
        duyuru_divleri = soup.find_all(
            "div",
            class_="row subpage-ann-single flex-nowrap"
        )

        # Hiç duyuru bulunamadıysa
        if not duyuru_divleri:
            print("⚠️ Sayfada hiç duyuru bulunamadı. HTML yapısı değişmiş olabilir.")
            return None

        # İlk duyuru = en güncel duyuru (sayfada en üstte olan)
        ilk_duyuru = duyuru_divleri[0]

        # Duyurunun benzersiz 'id' niteliğini al
        # Örnek: id="listAnnouncement320075"
        duyuru_id = ilk_duyuru.get("id", "bilinmiyor")

        # --------------------------------------------------------
        # Duyurudan ek bilgileri çıkarmaya çalışıyoruz.
        # Sitenin HTML yapısı değişirse bu kısımlar None dönebilir,
        # ama botun temel çalışması (ID karşılaştırması) etkilenmez.
        # --------------------------------------------------------

        # Duyurunun başlığını bulmaya çalış
        baslik_elementi = ilk_duyuru.find("a")
        baslik = baslik_elementi.get_text(strip=True) if baslik_elementi else "Başlık bulunamadı"

        # Duyurunun linkini bulmaya çalış
        link = ""
        if baslik_elementi and baslik_elementi.get("href"):
            href = baslik_elementi["href"]
            # Göreceli linkleri tam URL'ye çevir
            if href.startswith("/"):
                link = "https://med.gazi.edu.tr" + href
            else:
                link = href

        # Duyurunun tarihini bulmaya çalış
        tarih_elementi = ilk_duyuru.find("span")
        tarih = tarih_elementi.get_text(strip=True) if tarih_elementi else "Tarih bulunamadı"

        # Sonuçları sözlük olarak döndür
        return {
            "id": duyuru_id,
            "baslik": baslik,
            "tarih": tarih,
            "link": link
        }

    except requests.exceptions.ConnectionError:
        print("❌ Bağlantı hatası!")
        return None
    except requests.exceptions.Timeout:
        print("❌ İstek zaman aşımına uğradı.")
        return None
    except Exception as hata:
        print(f"❌ Beklenmeyen bir hata oluştu: {hata}")
        return None


# ============================================================
# 7. BÖLÜM: Zaman Damgası Yardımcı Fonksiyonu
# ============================================================
def simdi():
    """Şu anki zamanı okunabilir formatta döndürür."""
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


# ============================================================
# 8. BÖLÜM: Ana Fonksiyon (Tek Seferlik Kontrol)
# ============================================================
def ana():
    """
    Botun ana fonksiyonu.
    GitHub Actions tarafından her 15 dakikada bir çağrılır.
    Tek bir kontrol yapar ve sonlanır (döngü yok).
    """
    print("=" * 60)
    print("  🏥 Gazi Tıp Fakültesi Duyuru Takip Botu")
    print(f"  📅 Kontrol zamanı: {simdi()}")
    print("=" * 60)

    # Sayfayı kontrol et ve en güncel duyuruyu al
    guncel_duyuru = duyurulari_kontrol_et()

    # Eğer sayfa okunamadıysa hata kodu ile çık
    if guncel_duyuru is None:
        print("❌ Sayfa kontrol edilemedi!")
        sys.exit(1)  # Hata kodu: GitHub Actions bunu "başarısız" olarak işaretler

    # Sayfadaki en güncel duyurunun ID'si
    guncel_id = guncel_duyuru["id"]

    # Hafıza dosyasından daha önce kaydedilmiş ID'yi oku
    kayitli_id = son_kaydedilen_id_oku()

    # ---- İlk Çalıştırma Durumu ----
    if kayitli_id is None:
        print("📝 İlk çalıştırma! Mevcut en güncel duyuru kaydediliyor.")
        print(f"   ID    : {guncel_duyuru['id']}")
        print(f"   Başlık: {guncel_duyuru['baslik']}")
        id_kaydet(guncel_id)
        print(f"   ✅ '{HAFIZA_DOSYASI}' dosyasına kaydedildi.")

    # ---- Yeni Duyuru Var! ----
    elif guncel_id != kayitli_id:
        print("🚨 YENİ DUYURU TESPİT EDİLDİ!")
        print(f"   📌 Başlık : {guncel_duyuru['baslik']}")
        print(f"   📅 Tarih  : {guncel_duyuru['tarih']}")
        print(f"   🔗 Link   : {guncel_duyuru['link']}")
        print(f"   🏷️  ID     : {guncel_duyuru['id']}")

        # E-posta bildirimi gönder
        email_konu = f"🆕 Gazi Tıp - Yeni Duyuru: {guncel_duyuru['baslik']}"
        email_icerik = (
            f"Gazi Üniversitesi Tıp Fakültesi'nde yeni bir duyuru yayınlandı!\n"
            f"\n"
            f"📌 Başlık : {guncel_duyuru['baslik']}\n"
            f"📅 Tarih  : {guncel_duyuru['tarih']}\n"
            f"🔗 Link   : {guncel_duyuru['link']}\n"
            f"\n"
            f"Bu e-posta otomatik olarak Duyuru Takip Botu tarafından gönderilmiştir."
        )
        email_bildirim_gonder(email_konu, email_icerik)

        # Hafıza dosyasını yeni ID ile güncelle
        id_kaydet(guncel_id)
        print(f"   💾 Hafıza dosyası güncellendi: {guncel_id}")

    # ---- Yeni Duyuru Yok ----
    else:
        print(f"✅ Yeni duyuru yok. Son duyuru ID: {guncel_id}")

    print("\n✔️ Kontrol tamamlandı.")


# ============================================================
# 9. BÖLÜM: Programın Başlatılması
# ============================================================
if __name__ == "__main__":
    ana()

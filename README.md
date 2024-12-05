# Binance PNL Tracker

Binance Futures hesabınızdaki pozisyonların PNL (Kar/Zarar) değerlerini gerçek zamanlı takip etmenizi sağlayan bir masaüstü uygulaması.

## 📋 Özellikler

- Gerçek zamanlı PNL takibi
- Grafiksel gösterim
- Pozisyon bazlı alarmlar
- Özelleştirilebilir bildirimler
- Kullanıcı dostu arayüz
- Karanlık tema

## 🚀 Kurulum Rehberi

### 1. Python Kurulumu

1. [Python'un resmi sitesine](https://www.python.org/downloads/) gidin
2. En son Python 3.x sürümünü indirin (3.7 veya üstü)
3. İndirilen kurulum dosyasını çalıştırın
4. Kurulum sırasında "Add Python to PATH" seçeneğini işaretleyin
5. Kurulumu tamamlayın

Kurulumu kontrol etmek için:
```bash
python --version
```

### 2. Git Kurulumu (İsteğe Bağlı)

1. [Git'in resmi sitesinden](https://git-scm.com/downloads) Git'i indirin
2. Kurulum dosyasını çalıştırın ve varsayılan ayarlarla kurulumu tamamlayın

### 3. Uygulamayı İndirme

**A. Git ile (Önerilen):**
```bash
git clone https://github.com/yourusername/binance-pnl-tracker.git
cd binance-pnl-tracker
```

**B. ZIP olarak:**
1. GitHub'dan projeyi ZIP olarak indirin
2. İndirilen ZIP dosyasını çıkartın
3. Komut satırında çıkartılan klasöre gidin

### 4. Sanal Ortam Oluşturma (Önerilen)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate
```

### 5. Bağımlılıkların Kurulumu

```bash
pip install -e .
```

### 6. Binance API Ayarları

1. [Binance](https://www.binance.com/)'a giriş yapın
2. API Management sayfasına gidin
3. Yeni API anahtarı oluşturun
   - "Enable Futures" seçeneğini işaretleyin
   - IP kısıtlaması ekleyin (önerilen)
4. API Key ve Secret Key'i kopyalayın
5. `config.ini` dosyasını oluşturun:

```ini
[DEFAULT]
API_KEY = sizin_api_keyiniz
API_SECRET = sizin_api_secretiniz
CheckInterval = 30
AlertThreshold = 5
```

### 7. Uygulamayı Çalıştırma

```bash
python main.py
```

## 💡 Kullanım

1. Uygulama başlatıldığında, Binance API bağlantısı otomatik olarak kurulacaktır
2. Ana ekranda:
   - "Başlat" butonuna tıklayarak PNL takibini başlatın
   - Kontrol aralığını ayarlayın (saniye cinsinden)
   - Bildirim eşiğini belirleyin (USDT cinsinden)
3. Pozisyonlar sekmesinde:
   - Aktif pozisyonlarınızı görüntüleyin
   - Pozisyon bazlı alarmlar oluşturun
4. Alarmlar sekmesinde:
   - Yeni alarmlar ekleyin
   - Mevcut alarmları yönetin

## 🔧 Sorun Giderme

1. **API Bağlantı Hatası:**
   - API anahtarlarınızın doğruluğunu kontrol edin
   - IP kısıtlamalarını kontrol edin
   - Futures API yetkilerinin açık olduğundan emin olun

2. **Grafik Görüntüleme Sorunu:**
   - Matplotlib kütüphanesinin doğru kurulduğundan emin olun
   - Uygulamayı yeniden başlatın

3. **Bildirim Sorunu:**
   - İşletim sistemi bildirim ayarlarını kontrol edin
   - Plyer kütüphanesini yeniden yükleyin

## 📝 Notlar

- Uygulama, Binance Futures hesabınızdaki tüm pozisyonları otomatik olarak takip eder
- Gerçek zamanlı PNL takibi için internet bağlantınızın stabil olması önemlidir
- API anahtarlarınızı kimseyle paylaşmayın
- Önemli PNL değişimlerinde masaüstü bildirimleri alacaksınız

## 🔒 Güvenlik

- API anahtarlarınızı güvenli bir şekilde saklayın
- Sadece okuma yetkisi olan API anahtarları kullanın
- IP kısıtlaması eklemeniz önerilir
- `config.ini` dosyasını gizli tutun

## 🤝 Katkıda Bulunma

1. Bu depoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/yeniözellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik: XYZ'`)
4. Branch'inizi push edin (`git push origin feature/yeniözellik`)
5. Bir Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

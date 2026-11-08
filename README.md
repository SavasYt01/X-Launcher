# X-Launcher

GTK4 ve Python ile geliştirilen, Linux masaüstü için koyu temalı uygulama
başlatıcısı. Uygulama keşfi, bulanık arama, hesap makinesi, web araması,
isteğe bağlı kullanım geçmişi ve kullanıcı tanımlı takma adlar sunar.

## Özellikler

- **Uygulama arama:** Gio/XDG uygulama veritabanındaki görünür `.desktop`
  girdilerini bulanık eşleştirme ile arar.
- **Hesap makinesi:** `= 5 * (12 + 4)` gibi ifadeleri güvenli AST
  değerlendiricisiyle hesaplar; Python `eval()` kullanılmaz.
- **Web araması:** `g python GTK4` sorgusunu URL-kodlayıp varsayılan tarayıcıda
  açar.
- **Son kullanılanlar:** Başarıyla başlatılan son 20 farklı uygulamanın
  kimliğini yerel JSON dosyasında saklar ve arama sonuçlarında öne çıkarır.
- **Takma adlar:** `yt` gibi tek kelimelik takma adları uygulama masaüstü
  kimliklerine veya HTTP(S) adreslerine bağlar.
- **Klavye kullanımı:** `↑` / `↓` ile sonuç seçme, `Enter` ile çalıştırma,
  `Escape` ile pencereyi gizleme.
- **Wayland için toggle daemon:** Özel GNOME klavye kısayollarından tetiklenmek
  üzere kullanıcıya özel Unix socket kullanır.
- **Koyu GTK4 arayüzü:** Başlıksız pencere, siyah yüzey ve SF Pro Display
  bulunmadığında sistem sans-serif yazı tipi.

## Teknoloji ve mimari

| Modül | Sorumluluk |
|---|---|
| `main.py` | GTK4 penceresi, arama yönlendirme, sonuçlar ve klavye etkileşimi |
| `desktop_parser.py` | Gio ile XDG uygulama keşfi ve görünürlük filtreleme |
| `fuzzy_search.py` | Bağımlılıksız bulanık eşleştirme ve geçmiş puan katkısı |
| `history_manager.py` | Son kullanılan uygulamaları atomik JSON kaydıyla saklama |
| `alias_manager.py` | Kullanıcı takma adlarını yükleme ve tam sorgu eşleştirme |
| `calculator.py` | İzinli AST işlemleriyle güvenli aritmetik |
| `web_search.py` | Google sorgusu ve doğrulanmış HTTP(S) adreslerini açma |
| `app_launcher.py` | `.desktop` girdilerini shell kullanmadan başlatma |
| `toggle_daemon.py` | Kullanıcıya özel Unix socket daemon'ı ve kontrolü |
| `xlauncher-toggle` | Daemon'ı başlatma veya pencereyi açıp kapatma komutu |
| `install.sh` | Kullanıcı kapsamlı kurulum |

Uygulama Python'un standart kütüphanesini ve sistemden sağlanan GTK4,
PyGObject, Gio/GioUnix bileşenlerini kullanır. Python paket bağımlılığı
eklenmemiştir.

## Kurulum

### Gereksinimler

- Linux masaüstü oturumu
- Python 3.10 veya üzeri
- GTK4 ve PyGObject

Ubuntu/Debian üzerinde GTK bileşenlerini kurun:

```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-4.0
```

Depoyu klonlayıp kullanıcı hesabına kurun:

```bash
git clone https://github.com/SavasYt01/X-Launcher.git
cd X-Launcher
./install.sh
```

Kurulum `~/.local/share/xlauncher` altına uygulama dosyalarını, `~/.local/bin`
altına komutu ve kullanıcı uygulama menüsü için `.desktop` girdisini yerleştirir.
Sistem dizinlerini değiştirmez. Gerekirse `~/.local/bin` klasörünü `PATH`'e
ekleyin. Uygulamayı doğrudan proje klasöründen `/usr/bin/python3 main.py` ile
de başlatabilirsiniz.

## Kullanım

| Girdi | Sonuç |
|---|---|
| `firefox` | Kurulu uygulamaları arar |
| `= (5 + 3) * 2` | Hesaplar; seçili sonucu `Enter` ile panoya kopyalar |
| `g python GTK Wayland` | Google aramasını varsayılan tarayıcıda açar |
| `yt` | Yapılandırılmış bir web takma adını açar |
| `vs` | Yapılandırılmış bir uygulama takma adını başlatır |

### GNOME klavye kısayolu

Wayland'de global kısayol masaüstü ortamı tarafından yönetilir. **Ayarlar →
Klavye → Klavye Kısayolları → Özel Kısayollar** bölümünde `xlauncher` komutunu
istediğiniz kısayola (ör. `Super+Space`) atayın. Uygulama kendi başına global
tuş dinlemez; komut ilk kullanımda daemon'ı başlatır, sonraki çağrılarda
pencereyi açıp kapatır.

Daemon'ı elle durdurmak için:

```bash
xlauncher --stop
```

## Geçmiş ve takma ad ayarları

İki ayar dosyası da kullanıcı veri dizininde bulunur; varsayılan konumlar:

- Geçmiş: `~/.local/share/xlauncher/history.json`
- Takma adlar: `~/.local/share/xlauncher/aliases.json`

`XDG_DATA_HOME` tanımlıysa bu dosyalar `$XDG_DATA_HOME/xlauncher/` altında
oluşturulur. Geçmişte en son çalıştırılan 20 farklı uygulamanın desktop ID'si ve
UTC zaman damgası saklanır. Aynı uygulama tekrar çalıştırıldığında en başa
taşınır. Geçmiş dosyası okunamaz veya bozuksa başlatıcı çalışmaya devam eder;
geçmiş kaydı ayrı bir atomik yazma işlemiyle güncellenir.

Takma ad dosyası isteğe bağlıdır. Örnek içerik:

```json
{
  "yt": {
    "type": "web",
    "value": "https://youtube.com"
  },
  "vs": {
    "type": "app",
    "value": "code.desktop"
  }
}
```

Takma ad sorgusu tam eşleşir ve büyük/küçük harf duyarsızdır. `app` değeri
uygulamanın desktop ID'si olmalıdır; örneğin sistemdeki dosya
`code.desktop`. `web` türü yalnızca HTTP(S) adreslerini kabul eder. Eksik veya
geçersiz JSON normal aramaya geri dönülmesine neden olur; geçersiz takma ad
tanımları yok sayılır.

Takma adlar başlatıcı açılırken yüklenir. Daemon çalışıyorsa dosyayı
düzenledikten sonra `xlauncher --stop` çalıştırın; sonraki kısayol çağrısı yeni
ayarlarla daemon'ı yeniden başlatır.

## Güvenlik ve tasarım kararları

- Hesap makinesi yalnızca izin verilen AST düğümlerini değerlendirir; `eval()`
  ve Python kodu çalıştırma yoktur. İfade uzunluğu, AST boyutu ve sayı
  büyüklüğü sınırlandırılmıştır.
- Uygulamalar `GioUnix.DesktopAppInfo.launch()` ile açılır; `.desktop`
  `Exec` metni shell'e verilmez.
- Web sorguları URL-kodlanır. Web takma adları yalnızca HTTP(S) URL'lerine
  gidebilir; `javascript:`, `file:` ve kimlik bilgisi içeren URL'ler reddedilir.
- Geçmiş ve takma adlar kullanıcı veri dizininde saklanır; üçüncü taraf
  kütüphane veya uzaktaki servise gönderilmez.

## Test ve tanılama

Tüm birim testlerini çalıştırın:

```bash
python3 -m unittest discover -s tests -v
```

Statik proje taramasını ve testleri birlikte çalıştırın:

```bash
python3 scan_bugs.py
```

Testler hesap makinesini, arama sıralamasını, geçmişi, takma adları, web
adreslerini, kurulumu ve daemon socket yaşam döngüsünü kapsar.

## Platform notları

Wayland pencerenin konumunu ve odak alıp almayacağını yönetir; X-Launcher ekran
ortasında açılmayı veya odak almayı garanti edemez. AppImage paketleme tarifi
bulunmasına rağmen henüz doğrulanmış bir AppImage çıktısı yoktur. Mevcut tarif
Ubuntu Jammy amd64 hedeflidir ve yeni dağıtımlarda test edilmemiştir; önerilen
yöntem `./install.sh` ile kullanıcı kapsamlı kurulumdur.

## Lisans

Bu depoda henüz bir lisans dosyası bulunmuyor. Yeniden dağıtım veya katkı için
lisans koşulları belirlenene kadar depo sahibinden izin alın.

# X-Launcher

GTK4 ve Python ile geliştirilen, Linux masaüstü için hızlı uygulama başlatıcısı.
X-Launcher; kurulu uygulamaları arar, güvenli hesaplama yapar, web araması ve
yerel yardımcı komutlar sunar. Wayland'de global kısayolları masaüstü ortamı
yönetir; X-Launcher, GNOME kısayolundan tetiklenen kullanıcı daemon'ı sağlar.

## Özellikler

- **Bulanık uygulama araması:** Uygulama adı, çalıştırılabilir dosya, anahtar
  sözcük ve kategorilerde Unicode/aksan toleranslı eşleştirme; kısa aramalarda
  birden fazla sonuç.
- **Güvenli hesap makinesi:** `5*3` veya `= (5 + 3) * 2` girdilerini izinli
  AST düğümleriyle değerlendirir; `eval()` ve shell çalıştırma yoktur.
- **Yerel dosya araması:** `f fotoğraf.png` veya `file indirilenler` ile ev
  dizinindeki dosya/klasörleri arar ve varsayılan uygulamayla açar.
- **Web araması:** Google, DuckDuckGo, Brave Search, YouTube ve GitHub için
  sorgu önekleri; varsayılan motor ayarlanabilir.
- **Yardımcı komutlar:** Tarih/saat, birim dönüştürme ve X-Launcher içinden
  açıkça kopyalanan metinlerin pano geçmişi.
- **Geçmiş ve favoriler:** Seçime bağlı olarak son kullanılanları öne çıkarır;
  favoriler boş aramada gösterilebilir.
- **Takma adlar:** Uygulama desktop ID'lerine veya HTTP(S) adreslerine kişisel
  kısayollar.
- **GTK4 tema sistemi:** Kullanıcı temaları harici CSS dosyalarından yüklenir;
  geçersiz veya bulunamayan temalarda yerleşik koyu tema kullanılır.
- **GTK4 ayar penceresi:** Arama motoru, sonuç sayısı, tema, yenileme, alias,
  geçmiş, favori ve pano geçmişi seçeneklerini kategorilere ayırır; tema
  değişikliği kaydetmeden önce canlı önizlenir.
- **Daemon ve yenileme:** Kullanıcıya özel Unix socket; ayarları ve uygulama
  kataloğunu komutla yenileme, isteğe bağlı otomatik tarama.
- **Yardım ve tanılama:** `help`, `xlauncher --help` ve GTK penceresi açmadan
  çalışan, ağ kullanmayan `xlauncher --doctor`.
- **AppImage entegrasyonu:** İsteğe bağlı, native kurulumdan ayrı masaüstü
  girdisi; AppImage taşınırsa yeniden bütünleştirme gerekir.

## Teknoloji ve dosya yapısı

| Modül | Sorumluluk |
|---|---|
| `main.py` | GTK4 uygulama, arama yönlendirme, sonuç etkileşimleri ve daemon entegrasyonu |
| `desktop_parser.py` | Gio/XDG uygulama keşfi ve görünürlük filtreleme |
| `fuzzy_search.py` | Unicode-aware fuzzy ranking, geçmiş ve favori katkısı |
| `file_search.py` | Sınırlı ev dizini taraması ve dosya/klasör sıralaması |
| `command_router.py` | Alias, calculator, web, clipboard ve yerel sağlayıcı yönlendirmesi |
| `calculator.py` | Kısıtlı AST ile güvenli aritmetik |
| `providers.py` | Yerel tarih/saat ve Decimal tabanlı birim dönüştürme |
| `web_search.py` | URL-kodlanmış web araması ve HTTP(S) URI doğrulaması |
| `app_launcher.py` | `.desktop` uygulamalarını shell kullanmadan başlatma |
| `app_launch_context.py` | AppImage ortam değişkenlerini host uygulamalardan yalıtma |
| `config_manager.py` | Merkezi, doğrulanmış ayarlar ve atomik JSON kaydı |
| `history_manager.py`, `favorites_manager.py` | Kullanıcıya özel geçmiş ve favoriler |
| `clipboard_history.py` | Yalnızca X-Launcher'ın açıkça kopyaladığı metinleri saklama |
| `alias_manager.py`, `theme_manager.py` | Alias ve CSS tema yükleme |
| `preferences_window.py` | GTK4 ayarlar penceresi |
| `toggle_daemon.py` | Unix socket daemon, toggle ve reload komutları |
| `launcher_cli.py`, `doctor.py` | GTK yüklemeden CLI yardım, sürüm ve çevrimdışı tanılama |
| `appimage_integration.py` | Kullanıcı düzeyinde, native girdiyi koruyan AppImage entegrasyonu |
| `help_content.py` | Launcher içindeki Türkçe yardım satırları |

Python ek bağımlılığı yoktur. GTK4, PyGObject, Gio/GioUnix ve ilgili GI
typelib'leri işletim sisteminin paketlerinden sağlanır.

## Kurulum

### Önerilen: kullanıcı kapsamlı yerel kurulum

`./install.sh` birincil, bakımı yapılan ve önerilen kurulum yoludur. Sistem
dizinlerini değiştirmeden dosyaları kullanıcı hesabına yerleştirir.

Ubuntu/Debian'da GTK bağımlılıklarını kurun:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0
```

Ardından:

```bash
git clone https://github.com/SavasYt01/X-Launcher.git
cd X-Launcher
./install.sh
```

Varsayılan komut `~/.local/bin/xlauncher`, ayarlar ve uygulama dosyaları
`~/.local/share/xlauncher/` altındadır. `~/.local/bin` `PATH` içinde değilse
tam yolunu kullanın veya bu klasörü `PATH`'e ekleyin.

Kurulumu kaldırmak için:

```bash
xlauncher-uninstall
```

Kaldırıcı uygulama kodu ve masaüstü kısayolunu siler; `config.json`,
`history.json`, `favorites.json`, alias'lar, pano geçmişi ve özel temalar
korunur. Kaldırıcı bulunamıyorsa proje dizinindeki `./uninstall.sh` dosyasını
çalıştırabilirsiniz.

### GNOME / Wayland klavye kısayolu

**Ayarlar → Klavye → Klavye Kısayolları → Özel Kısayollar** bölümünde
`~/.local/bin/xlauncher` komutunu istediğiniz tuş bileşimine (ör. `Super+Space`)
atayın. İlk çağrı daemon'ı başlatır ve pencereyi açar; sonraki çağrılar
pencereyi açıp kapatır. Wayland pencere yerleşimini ve odağı yönettiği için
ekran ortasında görünme veya odağı alma garantisi verilemez.

Daemon komutları:

```bash
xlauncher --toggle
xlauncher --reload        # Ayarları ve uygulama kataloğunu yenile
xlauncher --reload-apps   # Yalnızca uygulama listesini yenile
xlauncher --stop
xlauncher --version
xlauncher --help
xlauncher --doctor
```

`--integrate` ve `--unintegrate` yalnızca AppImage içinden çalışır. Bu
komutlar `xlauncher-appimage.desktop` adlı ayrı bir girdi yönetir; native
kurulumun `xlauncher.desktop` girdisine dokunmaz.

## Kullanım

| Girdi | İşlem |
|---|---|
| `firefox` | Kurulu uygulamaları fuzzy arar |
| `u` | İsmi veya metaverisi eşleşen birden fazla uygulamayı gösterebilir |
| `5*3`, `(10+2)/3` | Hesaplar; Enter sonucu panoya kopyalar (`=` isteğe bağlı) |
| `f fotoğraf.png`, `file indirilenler` | Ev dizininde dosya/klasör arar; Enter açar |
| `g python GTK` | Google'da arar |
| `ddg python GTK` | DuckDuckGo'da arar |
| `br GTK4`, `yt GTK4`, `gh GTK4` | Brave, YouTube veya GitHub'da arar |
| `s GTK4` | Ayarlardaki varsayılan motorda arar |
| `25 km to mile` | Birim dönüştürür |
| `time`, `today`, `date` | Yerel saat veya tarihi gösterir |
| `cb` | X-Launcher'dan kopyalanan metin geçmişini gösterir |
| `cb clear` | Pano geçmişini onay isteyerek siler |
| `yt` | Tanımlı alias'ı çözer (alias varsa komut önekinden önce gelir) |
| `help` | Launcher içindeki Türkçe kullanım ipuçlarını gösterir |

Klavye: `↑` / `↓` ile sonuç seçme, `Enter` ile çalıştırma/açma, `Escape` ile
pencereyi gizleme, `Ctrl+D` ile seçili uygulamayı favoriye alma/kaldırma,
`Ctrl+R` ile uygulama ve dosya dizinlerini yenileme ve `Ctrl+,` ile ayarları
açma. `help` komutu kullanılabilir komutları ve kısayolları gösterir; `cb`
X-Launcher içinde kopyalanan metinlerin yerel geçmişini açar. Boş aramada
hızlı komut ipuçları favori ve son kullanılan uygulamalarla birlikte görünür.

## Ayarlar ve yerel veriler

Tüm JSON dosyaları `$XDG_DATA_HOME/xlauncher/` içinde, `XDG_DATA_HOME`
tanımlı değilse `~/.local/share/xlauncher/` altında tutulur:

- `config.json`: aktif tema, varsayılan arama motoru, sonuç sayısı, yenileme
  aralığı, geçmiş/favori görünürlüğü ve pano ayarları.
- `aliases.json`: kullanıcının app/web takma adları.
- `history.json`: desktop ID, son kullanım zamanı ve kullanım sayacı.
- `favorites.json`: favori desktop ID'leri.
- `clipboard_history.json`: sadece uygulama içindeki açık kopyalama
  eylemlerinden gelen metinler; sistem panosu arka planda dinlenmez.
- `themes/<ad>/theme.css`: kullanıcı GTK4 CSS temaları.

İlk kez açınca veya menüdeki kısayolla ayarlar penceresini kullanın. `Ctrl+,`
ile açılabilir. Bozuk ayar dosyalarında başlatıcı çalışmaya devam eder;
varsayılan değerler kullanılır ve hata loga kaydedilir. JSON yazımı atomiktir
ve kullanıcı dosyaları `0600` izniyle saklanır.

## Güvenlik ve gizlilik

- Hesap makinesi yalnızca izinli AST düğümlerini çalıştırır; `eval()` yoktur.
- `.desktop` girdileri `GioUnix.DesktopAppInfo.launch()` ile açılır, shell'e
  verilmez.
- Web araması URL-kodlanır. Takma adlar yalnızca doğrulanmış HTTP(S) adresleri
  veya kurulu desktop ID'leri kabul eder.
- Pano geçmişi sistem panosunu izlemez ve dış servise veri göndermez.
- Geçmiş, ayarlar ve alias'lar yerel kullanıcı verisidir; kod bu verileri
  üçüncü taraf sunuculara göndermez.

## Geliştirme ve test

```bash
python3 -m unittest discover -s tests -v
python3 scan_bugs.py
bash -n install.sh
bash -n uninstall.sh
```

GitHub Actions, Ubuntu 24.04 üzerinde GTK4 introspection bağlamalarıyla aynı
test ve tanılama taramasını çalıştırır.

## Deneysel AppImage

AppImage için özel AppDir derleyicisi GTK4, PyGObject, Python, typelib'leri ve
gerekli dinamik kütüphaneleri paketler. Derleme hedefi Ubuntu 24.04 x86_64'tür;
bu, daha eski glibc sürümlerinde çalışacağı anlamına gelmez. Build aracı URL ve
SHA-256 ile sabitlenmiştir. AppImage, native kurulumdan ayrı tutulur.

Ubuntu 24.04 üzerinde AppImage geliştirme araçları ve GTK bağımlılıkları:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 libgtk-4-dev libglib2.0-bin desktop-file-utils
```

AppImage oluşturmak ve çıkarılmış çıktının başlangıç testini çalıştırmak:

```bash
bash scripts/build-appimage.sh
bash scripts/test-appimage.sh
```

GitHub Actions, Ubuntu 24.04 üzerinde AppImage oluşturup `--version`, `--help`,
`--doctor`, masaüstü entegrasyonunu ve kaldırılmasını, ayrıca yerel kurulumun
masaüstü girdisinin korunmasını doğrular. Workflow başarıyla tamamlanana kadar
AppImage üretime hazır veya tüm sistemlerde doğrulanmış kabul edilmemelidir.
Paketlenen bileşenlerin sürüm ve telif bildirimleri AppImage içindeki
`usr/share/doc/xlauncher/THIRD_PARTY_NOTICES.md` dosyasındadır. Günlük
kullanımda `./install.sh` yerel kurulumu önerilir.

## Lisans

Depoda şu anda `LICENSE` dosyası yoktur. Lisans eklenene kadar yeniden
dağıtım koşulları belirlenmiş değildir.

# X-Launcher

GTK4 ve Python ile geliştirilen, Linux masaüstü için hızlı uygulama başlatıcısı.
X-Launcher; kurulu uygulamaları arar, güvenli hesaplama yapar, web araması ve
yerel yardımcı komutlar sunar. Wayland'de global kısayolları masaüstü ortamı
yönetir; X-Launcher, GNOME kısayolundan tetiklenen kullanıcı daemon'ı sağlar.

## Özellikler

- **Bulanık uygulama araması:** Uygulama adı, çalıştırılabilir dosya, anahtar
  sözcük ve kategorilerde Unicode/aksan toleranslı eşleştirme.
- **Güvenli hesap makinesi:** `= (5 + 3) * 2` girdilerini izinli AST düğümleriyle
  değerlendirir; `eval()` ve shell çalıştırma yoktur.
- **Web araması:** Google, DuckDuckGo, Brave Search, YouTube ve GitHub için
  sorgu önekleri; varsayılan motor ayarlanabilir.
- **Yardımcı komutlar:** Tarih/saat, birim dönüştürme ve X-Launcher içinden
  açıkça kopyalanan metinlerin pano geçmişi.
- **Geçmiş ба фаворит:** Сонголтоор хэрэглээний давтамж, сүүлийн хэрэглээг
  эрэмбэлж, дуртай програмуудыг хоосон хайлтад харуулна.
- **Takma adlar:** Uygulama desktop ID'lerine veya HTTP(S) adreslerine kişisel
  kısayollar.
- **GTK4 tema sistemi:** Kullanıcı temaları harici CSS dosyalarından yüklenir;
  geçersiz veya bulunamayan temalarda yerleşik koyu tema kullanılır.
- **GTK4 ayar penceresi:** Arama motoru, sonuç sayısı, tema, yenileme, alias,
  geçmiş, favori ve pano geçmişi seçenekleri.
- **Daemon ve yenileme:** Kullanıcıya özel Unix socket; ayarları ve uygulama
  kataloğunu komutla yenileme, isteğe bağlı otomatik tarama.

## Teknoloji ve dosya yapısı

| Modül | Sorumluluk |
|---|---|
| `main.py` | GTK4 uygulama, arama yönlendirme, sonuç etkileşimleri ve daemon entegrasyonu |
| `desktop_parser.py` | Gio/XDG uygulama keşfi ve görünürlük filtreleme |
| `fuzzy_search.py` | Unicode-aware fuzzy ranking, geçmiş ve favori katkısı |
| `command_router.py` | Alias, calculator, web, clipboard ve yerel sağlayıcı yönlendirmesi |
| `calculator.py` | Kısıtlı AST ile güvenli aritmetik |
| `providers.py` | Yerel tarih/saat ve Decimal tabanlı birim dönüştürme |
| `web_search.py` | URL-kodlanmış web araması ve HTTP(S) URI doğrulaması |
| `app_launcher.py` | `.desktop` uygulamalarını shell kullanmadan başlatma |
| `config_manager.py` | Merkezi, doğrulanmış ayarlar ve atomik JSON kaydı |
| `history_manager.py`, `favorites_manager.py` | Kullanıcıya özel geçmiş ve favoriler |
| `clipboard_history.py` | Yalnızca X-Launcher'ın açıkça kopyaladığı metinleri saklama |
| `alias_manager.py`, `theme_manager.py` | Alias ve CSS tema yükleme |
| `preferences_window.py` | GTK4 ayarlar penceresi |
| `toggle_daemon.py` | Unix socket daemon, toggle ve reload komutları |

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
```

## Kullanım

| Girdi | İşlem |
|---|---|
| `firefox` | Kurulu uygulamaları fuzzy arar |
| `= (5 + 3) * 2` | Hesaplar; Enter sonucu panoya kopyalar |
| `g python GTK` | Google'da arar |
| `ddg python GTK` | DuckDuckGo'da arar |
| `br GTK4`, `yt GTK4`, `gh GTK4` | Brave, YouTube veya GitHub'da arar |
| `s GTK4` | Ayarlardaki varsayılan motorda arar |
| `25 km to mile` | Birim dönüştürür |
| `time`, `today`, `date` | Yerel saat veya tarihi gösterir |
| `cb` | X-Launcher'dan kopyalanan metin geçmişini gösterir |
| `cb clear` | Pano geçmişini onay isteyerek siler |
| `yt` | Tanımlı alias'ı çözer (alias varsa komut önekinden önce gelir) |

Klavye: `↑` / `↓` ile sonuç seçme, `Enter` ile çalıştırma, `Escape` ile
pencereyi gizleme, `Ctrl+D` ile seçili uygulamayı favoriye alma/kaldırma,
`Ctrl+R` ile uygulamaları yenileme ve `Ctrl+,` ile ayarları açma.

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

## Deneysel / bakımı yapılmayan AppImage

AppImage tarifi (`packaging/AppImageBuilder.yml`) Ubuntu Jammy amd64 hedefler;
başka sürümlerde, özellikle Ubuntu 26.04 / GNOME 50.1 gibi daha yeni
ortamlarda Python/GTK sürüm uyumluluğu doğrulanmamıştır. AppImage mevcut
haliyle deneysel ve bakımı yapılmayan seçenektir. Üretim veya günlük kullanım
için `./install.sh` yerel kurulumu tercih edin.

## Lisans

Depoda şu anda `LICENSE` dosyası yoktur. Lisans eklenene kadar yeniden
dağıtım koşulları belirlenmiş değildir.

# X-Launcher

GTK4 uygulama başlatıcısı; arayüz, uygulama keşfi, bulanık arama, başlatma ve
Wayland oturumları için yerel toggle daemon'ı içerir.

Başka bir yapay zekâya projeyi tanıtmak veya kod değişikliği için bağlam
sağlamak üzere [AI proje brifini](./AI_PROJECT_BRIEF.md) kullanın. Brif,
mimarinin yanı sıra doğrulanmış davranışları ve henüz test edilmemiş AppImage
sınırlarını da açıklar.

## Önerilen kurulum: yerel kullanıcı kurulumu

`./install.sh`, X-Launcher için doğrulanmış ana kurulum yöntemidir ve
önerilir. Kurulum yalnızca kullanıcı hesabını değiştirir.

Ubuntu üzerinde Python için GTK4 ve PyGObject sistem paketlerini kurun:

```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-4.0
```

Kullanıcı hesabına kurmak için proje klasöründe:

```bash
./install.sh
```

Kurulum, uygulama dosyalarını `~/.local/share/xlauncher`, komutu
`~/.local/bin/xlauncher`, simgeyi ve GNOME masaüstü girdisini XDG kullanıcı
klasörlerine yerleştirir. Sistem dosyalarını değiştirmez ve `sudo` istemez.
GTK4/PyGObject sistemde kurulu değilse kurulum eksik bağımlılığı bildirerek
durdurulur. `~/.local/bin` terminal PATH'inde yoksa komutu tam yoluyla çağırın
veya bu klasörü kabuk PATH'inize ekleyin. GNOME özel kısayolu için `xlauncher`
yerine kurulum betiğinin yazdırdığı tam komut yolunu kullanabilirsiniz.

Kod ve testleri doğrulamak için:

```bash
python3 scan_bugs.py
```

Tarayıcı statik kontrollerin yanında unittest paketini de çalıştırır.
Uygulamaları listelerken `Gio.AppInfo.should_show()` kullanılır; bu nedenle
`NoDisplay`/görünürlük filtresini elle tekrar uygulamak gerekmez. Pencere
açılışında `present()` ve arama alanında `grab_focus()` çağrılır. GTK4'te
`Gtk.get_current_event_time()` bulunmadığından GTK3 odak örneği kullanılmaz;
Wayland'de pencerenin odak alması yine compositor politikasına bağlıdır.

## Deneysel / bakımı yapılmayan AppImage

AppImage oluşturma tarifi **deneyseldir ve doğrulanmamıştır**. Proje için
çalışan bir `.AppImage` çıktısı henüz üretilip test edilmedi; bu nedenle
önerilen dağıtım yöntemi değildir. Mevcut `packaging/AppImageBuilder.yml`
Ubuntu Jammy amd64 paketlerini hedefler ve Ubuntu 26.04/GNOME 50.1 gibi yeni
sürümlerde Python, GTK4 ve PyGObject uyumluluğu doğrulanmamıştır.

AppImage oluşturma betiği `scripts/build-appimage.sh` içindedir. GTK4 ve
PyGObject için GTK kütüphaneleri ile GI typelib dosyalarının da paketlenmesi
gerekir. Paylaşılan `linuxdeploy/linuxdeploy-plugin-python` indirme adresi 404
döndürüyor; bulunan `niess/linuxdeploy-plugin-python` eklentisi artık bakım
yapılmayan eski bir Python sürümünü hedefliyor. Aşağıdaki tarif Ubuntu Jammy
paketlerini indirir; derleme internet erişimi ve disk alanı gerektirir.

```bash
wget -O appimage-builder-x86_64.AppImage https://github.com/AppImageCrafters/appimage-builder/releases/download/v1.1.0/appimage-builder-1.1.0-x86_64.AppImage
chmod +x appimage-builder-x86_64.AppImage
chmod +x scripts/build-appimage.sh
APPIMAGE_BUILDER=./appimage-builder-x86_64.AppImage ./scripts/build-appimage.sh
```

AppImageBuilder PATH içindeyse doğrudan `./scripts/build-appimage.sh`
çalıştırılabilir. Çıktı dosya adını araç kendi belirler. Bir imaj
oluşturulduktan sonra çalıştırmak için:

```bash
chmod +x X-Launcher-x86_64.AppImage
./X-Launcher-x86_64.AppImage
```

AppImage'ın Wayland/X11 oturumları, glibc ve sistem entegrasyonlarıyla
uyumluluğu hedef dağıtımlarda ayrıca test edilmelidir.

## Hesap makinesi

Arama kutusuna `=` ile başlayan bir ifade yazılabilir:

```text
= (5 + 3) * 2
```

Sonuç listede görünür; seçiliyken `Enter` sonucu panoya kopyalar. Hesaplama
`calculator.py` içinde AST düğümlerini izin verilen işlemlerle tek tek
değerlendirir; Python `eval()` kullanılmaz. Sayılar, parantezler, tekli `+/-`,
`+`, `-`, `*`, `/`, `//`, `%` ve tam sayı üsleri desteklenir. Üs mutlak değeri
100 ile, ifade uzunluğu 128 karakterle, AST boyutu 64 düğümle ve sayı büyüklüğü
4.096 bit ile sınırlandırılır. Sonuçlar tam kesir olarak gösterilebilir; ör.
`= 1 / 3` sonucu `1/3` olur. Fonksiyon çağrıları ve Python ifadeleri
reddedilir.

SF Pro Display yazı tipi kurulu değilse GTK `sans-serif` yazı tipini kullanır.

## Web araması

Arama kutusuna `g ` öneki ve arama terimini yaz:

```text
g python GTK Wayland
```

Sonuç satırında Google araması görünür. `Enter` seçiliyken sorguyu URL
parametresi olarak kodlar ve sistemin varsayılan tarayıcısında Google aramasını
açar. Arama metni shell komutu olarak çalıştırılmaz. `g` tek başına uygulama
aramasıdır; web araması için önekten sonra en az bir terim gerekir.

## Kullanım

Arayüzü tek başına açmak için:

```bash
/usr/bin/python3 main.py
```

Toggle komutu daemon'ı ilk çalıştırmada arka planda başlatır; sonraki
çağrılarda pencereyi açar/kapatır:

```bash
./xlauncher-toggle
```

Komutu PATH üzerinden kullanmak isterseniz proje klasöründeyken kişisel bin
klasörüne sembolik bağlantı oluşturun:

```bash
mkdir -p ~/.local/bin
ln -s "$(pwd)/xlauncher-toggle" ~/.local/bin/xlauncher-toggle
```

`~/.local/bin` PATH içinde değilse kabuk ayarınıza ekleyin. GNOME'da **Ayarlar
→ Klavye → Klavye Kısayolları → Özel Kısayollar** bölümünde çalıştırılacak
komut olarak `xlauncher-toggle` girip istediğiniz kısayolu atayın. Wayland'de
global kısayolu masaüstü ortamı yönetir; uygulama kendi başına global tuş
dinlemez.

Arayüz `Escape` ile gizlenir; `↑` ve `↓` ile sonuç seçilir, `Enter` seçili
uygulamayı başlatır. Daemon'ı kapatmak için:

```bash
/usr/bin/python3 main.py --stop
```

Daemon hata çıktısı `$XDG_RUNTIME_DIR/xlauncher/daemon.log` dosyasına yazılır.

## Uygulama keşfi ve başlatma

`Gio.AppInfo.get_all()` masaüstünün XDG uygulama veritabanını kullanır; böylece
`~/.local/share/applications` ve `/usr/share/applications` dahil kurulu
uygulamalar, kullanıcı geçersiz kılmaları ve gizli girdiler freedesktop
kurallarına göre ele alınır. `Gio.DesktopAppInfo` girdileri `Name`, `Exec`,
`Icon` ve açıklama bilgileriyle alınır. Başlatma, `Exec` metnini shell'e
vermek yerine GLib'in desktop-entry desteğiyle yapılır.

## Wayland notu

Wayland istemcileri güvenlik nedeniyle ekran koordinatlarını belirleyemez;
pencerenin tam ekran ortasında açılması Mutter tarafından yönetilir ve garanti
edilemez. `present()` ile odak talep edilir ancak odak değişimini compositor
reddedebilir. Pencere 600×60 varsayılan boyutundadır; arama sonuçları
göründüğünde pencere içerik için büyüyebilir.

## Modüller

- `main.py`: GTK4 arayüzü, klavye etkileşimi ve uygulama akışı
- `desktop_parser.py`: XDG masaüstü uygulamalarını keşfetme
- `fuzzy_search.py`: bağımlılıksız bulanık eşleştirme ve sıralama
- `calculator.py`: izinli AST aritmetiği ve güvenli hesaplama
- `web_search.py`: URL-kodlu Google aramasını varsayılan tarayıcıda açma
- `app_launcher.py`: desktop-entry kurallarına göre uygulama başlatma
- `toggle_daemon.py`: kullanıcıya özel Unix socket kontrolü
- `xlauncher-toggle`: daemon'ı başlatan/aç-kapat yapan komut
- `install.sh`: kullanıcı kapsamlı yerel kurulum
- `scan_bugs.py`: statik kontroller ve test çalıştırıcısı

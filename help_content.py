"""Short Turkish help entries shown inside the launcher."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpEntry:
    title: str
    description: str


QUICK_HELP_ENTRIES = (
    HelpEntry("Hesap makinesi", "5*3 yazın; Enter sonucu panoya kopyalar."),
    HelpEntry(
        "Dosya ara",
        "f fotoğraf.png yazın; Enter varsayılan uygulamada açar.",
    ),
    HelpEntry("Pano geçmişi", "cb ile X-Launcher içinde kopyalanan metinleri görün."),
    HelpEntry("Komutlar ve kısayollar", "help yazın; tüm komutlar listelenir."),
)

HELP_ENTRIES = (
    HelpEntry("Uygulama ara", "Uygulama adını yazın; ör. firefox veya code."),
    *QUICK_HELP_ENTRIES[:2],
    HelpEntry("Web araması", "g, ddg, br, yt, gh veya s önekiyle arayın."),
    HelpEntry("Birim dönüştürme", "25 km to mile gibi bir ifade yazın."),
    HelpEntry("Tarih ve saat", "time, today veya date yazın."),
    QUICK_HELP_ENTRIES[2],
    HelpEntry(
        "Takma ad",
        "Ayarlar'da ör. yt → web adresi veya vs → code.desktop tanımlayın.",
    ),
    HelpEntry("Favoriler ve son kullanılanlar", "Ctrl+D ile favori; boş aramada favori ve geçmiş."),
    HelpEntry("Ayarlar", "Ctrl+, ile tercihleri açın."),
    HelpEntry("Klavye", "↑/↓ seçer · Enter çalıştırır · Escape gizler."),
    QUICK_HELP_ENTRIES[3],
    HelpEntry(
        "Kısayollar",
        "Ctrl+D favori · Ctrl+R uygulama/dosya dizinini yenile · "
        "Ctrl+, ayarlar · Ctrl+L temizle.",
    ),
)

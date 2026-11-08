"""Short Turkish help entries shown inside the launcher."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpEntry:
    title: str
    description: str


HELP_ENTRIES = (
    HelpEntry("Uygulama ara", "Uygulama adını yazın; ör. firefox veya code."),
    HelpEntry("Hesap makinesi", "= (5 + 3) * 2 biçiminde güvenli hesaplama yapın."),
    HelpEntry("Google", "g arama ifadesi"),
    HelpEntry("DuckDuckGo", "ddg arama ifadesi"),
    HelpEntry("Brave Search", "br arama ifadesi"),
    HelpEntry("YouTube", "yt arama ifadesi"),
    HelpEntry("GitHub", "gh arama ifadesi"),
    HelpEntry("Varsayılan arama motoru", "s arama ifadesi; motoru Ayarlar'dan seçin."),
    HelpEntry("Birim dönüştürme", "25 km to mile gibi bir ifade yazın."),
    HelpEntry("Tarih ve saat", "time, today veya date yazın."),
    HelpEntry("Pano geçmişi", "cb geçmişi gösterir; cb clear silme onayı ister."),
    HelpEntry("Takma ad", "Ayarlar'da yt → web adresi veya vs → code.desktop tanımlayın."),
    HelpEntry("Favoriler ve son kullanılanlar", "Ctrl+D ile favori; boş aramada favori ve geçmiş."),
    HelpEntry("Ayarlar", "Ctrl+, ile tercihleri açın."),
    HelpEntry("Klavye", "↑/↓ seçer · Enter çalıştırır · Escape gizler."),
    HelpEntry("Kısayollar", "Ctrl+D favori · Ctrl+R yenile · Ctrl+, ayarlar · Ctrl+L temizle."),
)

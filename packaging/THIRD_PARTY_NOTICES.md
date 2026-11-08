# AppImage üçüncü taraf bildirimleri

AppImage, hedef Linux dağıtımından Python, PyGObject, GTK4, GObject
Introspection ve bunların dinamik kütüphanelerini içerir. AppDir oluşturucusu,
derleme makinesinde bu dosyaların sahibi olan Debian paketlerini ve sürümlerini
`usr/share/doc/xlauncher/THIRD_PARTY_NOTICES.md` içine kaydeder; ilgili paket
`copyright` belgelerini de `usr/share/doc/third-party/` altına kopyalar.

AppImage runtime'ı ve `appimagetool` ayrı AppImageKit bileşenleridir. Derleme
aracı resmi AppImageKit sürümünden indirilir ve SHA-256 ile doğrulanır. Bu
bileşenlerin lisans ve telif bilgileri için AppImageKit'in ilgili sürüm
belgelerine başvurun.

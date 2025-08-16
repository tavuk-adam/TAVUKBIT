# TAVUKBIT Simülasyon Uygulaması (Flask)
# Bu uygulama, TAVUKBIT adlı sanal bir varlığın fiyatını simüle eder.
# Kullanıcılar, simülasyonu başlatabilir, durdurabilir ve fiyatın
# düşme veya yükselme olasılığını "meilleştirme" (optimize etme) seviyelerini ayarlayabilirler.

# Gerekli Flask modüllerini ve diğer kütüphaneleri içe aktarma
import random
import threading
import time
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify

# Flask uygulamasını başlatma ve oturum yönetimi için gizli bir anahtar belirleme
# NOT: Gerçek bir uygulamada daha karmaşık ve güvenli bir anahtar kullanılmalıdır.
app = Flask(__name__)
app.secret_key = "gizli_tavuk"

# Ortak kaynaklara eş zamanlı erişimi yönetmek için bir kilit nesnesi oluşturma
# Bu, birden fazla thread aynı anda veri değiştirmeye çalıştığında
# oluşabilecek hataları önler.
lock = threading.Lock()

# TAVUKBIT simülasyonu için genel değişkenler
fiyat = 0  # Mevcut fiyat
log_kaydi = []  # Olay günlüğünü tutan liste
simulasyon_aktif = False  # Simülasyonun aktif olup olmadığını belirten bayrak
kalan_sure = 0  # Simülasyon için kalan süre (saniye)

# Meilleştirme seviyeleri (0-5 arasında)
# Bu seviyeler, fiyat değişimlerinin olasılıklarını etkiler.
dusme_meille_seviye = 0
yukselme_meille_seviye = 0

# HTML şablonu bir Python dizesi olarak tanımlanır
HTML = '''
<!doctype html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <title>💰TAVUKBIT💰</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background:#121212; color:#eee; }
        pre { background:#111; color:#0f0; padding:10px; height:200px; overflow:auto; font-family:monospace; }
        .fiyat { font-size:2rem; color:lime; }
    </style>
</head>
<body class="container py-4">
    <h1>💰TAVUKBIT💰</h1>

    {% if not session.get("giris_tavuk") %}
        <h2>🐔 TAVUKBIT</h2>
        <div>Fiyat: <span class="fiyat">{{ fiyat }}</span> elmas</div>
        <form method="post" action="/login" class="mt-4">
            <label>🔑 Şifre: <input type="password" name="password" class="form-control" required></label><br>
            <button class="btn btn-primary">Giriş Yap</button>
        </form>
    {% else %}
        <a href="/logout" class="btn btn-warning mb-4">🚪 Çıkış Yap</a>
        <h2>🐔 TAVUKBIT</h2>
        <label>⏳ Süre (sn): 
            <input type="number" id="sure_input" class="form-control mb-2" value="20" min="5" max="120">
        </label>
        <label>💰 Başlangıç Fiyatı (opsiyonel): 
            <input type="number" id="baslangic_input" class="form-control mb-2" placeholder="Boş bırakılırsa eski fiyatla devam" min="1">
        </label>
        <div>Fiyat: <span class="fiyat" id="fiyat">{{ fiyat }}</span> elmas</div>
        <div>Durum: <span id="durum">{{ durum }}</span></div>
        <div>Kalan Süre: <span id="kalan_sure">{{ kalan_sure }}</span> saniye</div>
        <div class="mb-3">
            <button id="dusme_arti" class="btn btn-danger">⬇️ Düşmeye Meilleştir (+)</button>
            <button id="dusme_eksi" class="btn btn-secondary">⬇️ Düşmeye Meilleştir (-)</button>
            <span>Düşme Seviyesi: <span id="dusme_seviye">{{ dusme_meille_seviye }}</span> / 5</span>
        </div>
        <div class="mb-3">
            <button id="yukselme_arti" class="btn btn-success">⬆️ Yükselmeye Meilleştir (+)</button>
            <button id="yukselme_eksi" class="btn btn-secondary">⬆️ Yükselmeye Meilleştir (-)</button>
            <span>Yükselme Seviyesi: <span id="yukselme_seviye">{{ yukselme_meille_seviye }}</span> / 5</span>
        </div>
        <button id="devamBtn" class="btn btn-success my-1">▶ Devam</button>
        <button id="durdurBtn" class="btn btn-danger my-1">⏹ Durdur</button>
        <button id="temizleBtn" class="btn btn-secondary my-1">🧹 Temizle</button>
        <pre id="log">{{ log }}</pre>
    {% endif %}
    <script>
        // Her saniye sunucudan güncel verileri getiren fonksiyon
        function update() {
            fetch('/status').then(r => r.json()).then(data => {
                // DOM elementlerini gelen verilerle güncelleme
                if(document.getElementById("fiyat")) document.getElementById("fiyat").textContent = data.fiyat;
                if(document.getElementById("durum")) document.getElementById("durum").textContent = data.durum;
                if(document.getElementById("log")) document.getElementById("log").textContent = data.log;
                if(document.getElementById("kalan_sure")) document.getElementById("kalan_sure").textContent = data.kalan_sure;
                if(document.getElementById("dusme_seviye")) document.getElementById("dusme_seviye").textContent = data.dusme_meille_seviye;
                if(document.getElementById("yukselme_seviye")) document.getElementById("yukselme_seviye").textContent = data.yukselme_meille_seviye;
            });
        }
        // Güncelleme fonksiyonunu her saniye çağırma
        setInterval(update, 1000);
        update();
        // Butonlara tıklama olayları ekleyerek sunucuya POST istekleri gönderme
        if (document.getElementById("devamBtn")) {
            document.getElementById("devamBtn").onclick = () => {
                const sure = parseInt(document.getElementById("sure_input")?.value) || 20;
                const baslangic = parseInt(document.getElementById("baslangic_input")?.value);
                fetch('/devam', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ sure: sure, baslangic: baslangic })
                });
            };
        }
        if (document.getElementById("durdurBtn")) {
            document.getElementById("durdurBtn").onclick = () => fetch('/durdur', { method: 'POST' });
        }
        if (document.getElementById("temizleBtn")) {
            document.getElementById("temizleBtn").onclick = () => fetch('/temizle', { method: 'POST' });
        }
        if(document.getElementById("dusme_arti")) {
            document.getElementById("dusme_arti").onclick = () => {
                fetch('/meille_dusme_artir', { method: 'POST' });
            };
        }
        if(document.getElementById("dusme_eksi")) {
            document.getElementById("dusme_eksi").onclick = () => {
                fetch('/meille_dusme_azalt', { method: 'POST' });
            };
        }
        if(document.getElementById("yukselme_arti")) {
            document.getElementById("yukselme_arti").onclick = () => {
                fetch('/meille_yukselme_artir', { method: 'POST' });
            };
        }
        if(document.getElementById("yukselme_eksi")) {
            document.getElementById("yukselme_eksi").onclick = () => {
                fetch('/meille_yukselme_azalt', { method: 'POST' });
            };
        }
    </script>
</body>
</html>
'''

# Fiyat simülasyonunu ayrı bir thread'de çalıştıran fonksiyon
def simulasyonu_baslat(sure, baslangic=None):
    """
    Simülasyonu başlatan fonksiyon. Belirtilen süre boyunca her saniye fiyatı günceller.
    Başlangıç fiyatı belirtilirse onu kullanır, aksi takdirde mevcut fiyattan devam eder.
    """
    global fiyat, log_kaydi, simulasyon_aktif, kalan_sure
    global dusme_meille_seviye, yukselme_meille_seviye

    with lock:
        # Başlangıç fiyatı ayarlanmışsa uygula
        if baslangic and isinstance(baslangic, int) and baslangic > 0:
            fiyat = baslangic
        simulasyon_aktif = True
        kalan_sure = sure

    # Belirlenen süre boyunca döngü
    for saniye in range(1, sure + 1):
        # 1 saniye bekle
        time.sleep(1)
        with lock:
            # Durdurma isteği gelmişse döngüyü sonlandır
            if not simulasyon_aktif:
                log_kaydi.append("⏹ Simülasyon erken durduruldu.")
                break

            # Olası fiyat değişimleri
            olasiliklar = [-2, -1, 0, 1, 2]
            # Başlangıç ağırlıkları
            agirliklar = [1, 1, 1, 1, 1]

            # Düşme optimizasyon seviyesine göre ağırlıkları artır
            if dusme_meille_seviye > 0:
                agirliklar[0] += dusme_meille_seviye  # -2
                agirliklar[1] += dusme_meille_seviye  # -1

            # Yükselme optimizasyon seviyesine göre ağırlıkları artır
            if yukselme_meille_seviye > 0:
                agirliklar[3] += yukselme_meille_seviye  # 1
                agirliklar[4] += yukselme_meille_seviye  # 2

            # Ağırlıklara göre rastgele bir fiyat değişimi seç
            secim = random.choices(olasiliklar, weights=agirliklar, k=1)[0]
            
            # Yeni fiyatı hesapla, en az 1 olmasını sağla
            fiyat = max(1, fiyat + secim)

            # Günlüğe yeni bir kayıt ekle
            log_kaydi.append(
                f"{saniye}. saniye - fiyat: {fiyat} elmas (Düşme Meille: {dusme_meille_seviye}, Yükselme Meille: {yukselme_meille_seviye})")

            # Kalan süreyi azalt
            kalan_sure -= 1

    # Döngü bittiğinde veya erken durdurulduğunda
    with lock:
        simulasyon_aktif = False
        kalan_sure = 0
        log_kaydi.append("⏹ Simülasyon durdu.")

# Ana sayfa rotası
@app.route("/")
def index():
    """Ana sayfa. HTML şablonunu değişkenlerle işler."""
    return render_template_string(HTML,
                                  fiyat=fiyat, log="\n".join(log_kaydi), durum="🟢" if simulasyon_aktif else "🔴",
                                  kalan_sure=kalan_sure,
                                  dusme_meille_seviye=dusme_meille_seviye,
                                  yukselme_meille_seviye=yukselme_meille_seviye,
                                  session=session)

# Durum güncelleme rotası (AJAX istekleri için)
@app.route("/status")
def status():
    """Mevcut simülasyon durumunu JSON formatında döndürür."""
    return jsonify({
        "fiyat": fiyat,
        # Son 50 kaydı göster
        "log": "\n".join(log_kaydi[-50:]),
        "durum": "🟢" if simulasyon_aktif else "🔴",
        "kalan_sure": kalan_sure,
        "simulasyon_aktif": simulasyon_aktif,
        "dusme_meille_seviye": dusme_meille_seviye,
        "yukselme_meille_seviye": yukselme_meille_seviye,
    })

# Simülasyonu başlatma rotası (POST)
@app.route("/devam", methods=["POST"])
def devam():
    """Simülasyonu başlatır ve bir thread içinde çalıştırır."""
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    data = request.get_json(force=True)
    sure = data.get("sure", 20)
    baslangic = data.get("baslangic")
    try:
        sure = int(sure)
    except (ValueError, TypeError):
        sure = 20
    if not (5 <= sure <= 120):
        sure = 20
    try:
        baslangic = int(baslangic)
    except (ValueError, TypeError):
        baslangic = None
    threading.Thread(target=simulasyonu_baslat, args=(sure, baslangic)).start()
    return ('', 204)

# Simülasyonu durdurma rotası (POST)
@app.route("/durdur", methods=["POST"])
def durdur():
    """Simülasyonun aktif bayrağını yanlış (False) olarak ayarlar."""
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    global simulasyon_aktif
    with lock:
        simulasyon_aktif = False
    return ('', 204)

# Günlükleri temizleme rotası (POST)
@app.route("/temizle", methods=["POST"])
def temizle():
    """Simülasyon günlüğünü temizler."""
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    global log_kaydi
    with lock:
        log_kaydi.clear()
        log_kaydi.append("🧹 Log temizlendi.")
    return ('', 204)

# Düşme optimizasyonu artırma rotası (POST)
@app.route("/meille_dusme_artir", methods=["POST"])
def meille_dusme_artir():
    """Düşme optimizasyon seviyesini artırır."""
    global dusme_meille_seviye, yukselme_meille_seviye
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    with lock:
        if dusme_meille_seviye < 5:
            dusme_meille_seviye += 1
        # Yükselme optimizasyonunu sıfırla
        if yukselme_meille_seviye != 0:
            yukselme_meille_seviye = 0
    return ('', 204)

# Düşme optimizasyonu azaltma rotası (POST)
@app.route("/meille_dusme_azalt", methods=["POST"])
def meille_dusme_azalt():
    """Düşme optimizasyon seviyesini azaltır."""
    global dusme_meille_seviye
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    with lock:
        if dusme_meille_seviye > 0:
            dusme_meille_seviye -= 1
    return ('', 204)

# Yükselme optimizasyonu artırma rotası (POST)
@app.route("/meille_yukselme_artir", methods=["POST"])
def meille_yukselme_artir():
    """Yükselme optimizasyon seviyesini artırır."""
    global yukselme_meille_seviye, dusme_meille_seviye
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    with lock:
        if yukselme_meille_seviye < 5:
            yukselme_meille_seviye += 1
        # Düşme optimizasyonunu sıfırla
        if dusme_meille_seviye != 0:
            dusme_meille_seviye = 0
    return ('', 204)

# Yükselme optimizasyonu azaltma rotası (POST)
@app.route("/meille_yukselme_azalt", methods=["POST"])
def meille_yukselme_azalt():
    """Yükselme optimizasyon seviyesini azaltır."""
    global yukselme_meille_seviye
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    with lock:
        if yukselme_meille_seviye > 0:
            yukselme_meille_seviye -= 1
    return ('', 204)

# Giriş yapma rotası (POST)
@app.route("/login", methods=["POST"])
def login():
    """Kullanıcı girişi kontrolünü yapar."""
    sifre = request.form.get("password")
    # NOT: Gerçek bir uygulamada şifre güvenli bir şekilde saklanmalı ve karşılaştırılmalıdır.
    if sifre == "chicken123":
        session["giris_tavuk"] = True
        log_kaydi.append("✅ TAVUKBIT giriş yapıldı.")
    else:
        log_kaydi.append("🚫 Hatalı şifre denemesi!")
    return redirect(url_for("index"))

# Çıkış yapma rotası
@app.route("/logout")
def logout():
    """Kullanıcı oturumunu sonlandırır."""
    session.pop("giris_tavuk", None)
    log_kaydi.append("👋 Çıkış yapıldı.")
    return redirect(url_for("index"))

# Uygulamayı çalıştırma
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
import random
import threading
import time

app = Flask(__name__)
app.secret_key = "gizli_tavuk"

lock = threading.Lock()

# TAVUKBIT verileri
fiyat = 14
log_kaydi = []
simulasyon_aktif = False
kalan_sure = 0

# ATL COIN verileri
fiyat_atl = 30
log_kaydi_atl = []
simulasyon_aktif_atl = False
kalan_sure_atl = 0

HTML = '''
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <title>💰 Coin Simülasyonu</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background:#121212; color:#eee; }
    pre { background:#111; color:#0f0; padding:10px; height:200px; overflow:auto; font-family:monospace; }
    .fiyat { font-size:2rem; color:lime; }
  </style>
</head>
<body class="container py-4">
  <h1>💰 Coin Simülasyonu</h1>

  {% if not session.get("giris_tavuk") and not session.get("giris_atl") %}
    <h2>🐔 TAVUKBIT</h2>
    <div>Fiyat: <span class="fiyat">{{ fiyat }}</span> elmas</div>

    <h2>🐴 ATL COIN</h2>
    <div>Fiyat: <span class="fiyat">{{ fiyat_atl }}</span> elmas</div>

    <form method="post" action="/login" class="mt-4">
      <label>🔑 Şifre: <input type="password" name="password" class="form-control" required></label><br>
      <button class="btn btn-primary">Giriş Yap</button>
    </form>
  {% else %}

    <a href="/logout" class="btn btn-warning mb-4">🚪 Çıkış Yap</a>

    {% if session.get("giris_tavuk") %}
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
      <button id="devamBtn" class="btn btn-success my-1">▶ Devam</button>
      <button id="durdurBtn" class="btn btn-danger my-1">⏹ Durdur</button>
      <button id="temizleBtn" class="btn btn-secondary my-1">🧹 Temizle</button>
      <pre id="log">{{ log }}</pre>
    {% endif %}

    {% if session.get("giris_atl") %}
      <h2>🐴 ATL COIN</h2>
      <label>⏳ Süre (sn): 
        <input type="number" id="sure_input_atl" class="form-control mb-2" value="20" min="5" max="120">
      </label>
      <label>💰 Başlangıç Fiyatı (opsiyonel): 
        <input type="number" id="baslangic_input_atl" class="form-control mb-2" placeholder="Boş bırakılırsa eski fiyatla devam" min="1">
      </label>
      <div>Fiyat: <span class="fiyat" id="fiyat_atl">{{ fiyat_atl }}</span> elmas</div>
      <div>Durum: <span id="durum_atl">{{ durum_atl }}</span></div>
      <div>Kalan Süre: <span id="kalan_sure_atl">{{ kalan_sure_atl }}</span> saniye</div>
      <button id="devamBtn_atl" class="btn btn-success my-1">▶ Devam</button>
      <button id="durdurBtn_atl" class="btn btn-danger my-1">⏹ Durdur</button>
      <button id="temizleBtn_atl" class="btn btn-secondary my-1">🧹 Temizle</button>
      <pre id="log_atl">{{ log_atl }}</pre>
    {% endif %}

  {% endif %}

<script>
  function update() {
    fetch('/status').then(r => r.json()).then(data => {
      if(document.getElementById("fiyat")) document.getElementById("fiyat").textContent = data.fiyat;
      if(document.getElementById("durum")) document.getElementById("durum").textContent = data.durum;
      if(document.getElementById("log")) document.getElementById("log").textContent = data.log;
      if(document.getElementById("kalan_sure")) document.getElementById("kalan_sure").textContent = data.kalan_sure;

      if(document.getElementById("fiyat_atl")) document.getElementById("fiyat_atl").textContent = data.fiyat_atl;
      if(document.getElementById("durum_atl")) document.getElementById("durum_atl").textContent = data.durum_atl;
      if(document.getElementById("log_atl")) document.getElementById("log_atl").textContent = data.log_atl;
      if(document.getElementById("kalan_sure_atl")) document.getElementById("kalan_sure_atl").textContent = data.kalan_sure_atl;
    });
  }

  setInterval(update, 1000);
  update();

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

  if (document.getElementById("devamBtn_atl")) {
    document.getElementById("devamBtn_atl").onclick = () => {
      const sure = parseInt(document.getElementById("sure_input_atl")?.value) || 20;
      const baslangic = parseInt(document.getElementById("baslangic_input_atl")?.value);
      fetch('/devam_atl', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ sure: sure, baslangic: baslangic })
      });
    };
  }

  if (document.getElementById("durdurBtn_atl")) {
    document.getElementById("durdurBtn_atl").onclick = () => fetch('/durdur_atl', { method: 'POST' });
  }

  if (document.getElementById("temizleBtn_atl")) {
    document.getElementById("temizleBtn_atl").onclick = () => fetch('/temizle_atl', { method: 'POST' });
  }

</script>
</body>
</html>
'''

def simulasyonu_baslat(sure, baslangic=None):
    global fiyat, log_kaydi, simulasyon_aktif, kalan_sure
    with lock:
        if baslangic and isinstance(baslangic, int) and baslangic > 0:
            fiyat = baslangic
        simulasyon_aktif = True
        kalan_sure = sure
    for saniye in range(1, sure + 1):
        time.sleep(1)
        with lock:
            if not simulasyon_aktif:
                log_kaydi.append("⏹ Simülasyon erken durduruldu.")
                break
            degisim = random.randint(-2, 2)
            fiyat = max(1, fiyat + degisim)
            log_kaydi.append(f"{saniye}. saniyede fiyat: {fiyat} elmas")
            kalan_sure -= 1
    with lock:
        simulasyon_aktif = False
        kalan_sure = 0
        log_kaydi.append("⏹ Simülasyon durdu.")

def simulasyonu_baslat_atl(sure, baslangic=None):
    global fiyat_atl, log_kaydi_atl, simulasyon_aktif_atl, kalan_sure_atl
    with lock:
        if baslangic and isinstance(baslangic, int) and baslangic > 0:
            fiyat_atl = baslangic
        simulasyon_aktif_atl = True
        kalan_sure_atl = sure
    for saniye in range(1, sure + 1):
        time.sleep(1)
        with lock:
            if not simulasyon_aktif_atl:
                log_kaydi_atl.append("⏹ ATL simülasyon erken durduruldu.")
                break
            degisim = random.randint(-2, 2)
            fiyat_atl = max(1, fiyat_atl + degisim)
            log_kaydi_atl.append(f"{saniye}. saniyede ATL fiyatı: {fiyat_atl} elmas")
            kalan_sure_atl -= 1
    with lock:
        simulasyon_aktif_atl = False
        kalan_sure_atl = 0
        log_kaydi_atl.append("⏹ ATL simülasyon durdu.")

@app.route("/")
def index():
    return render_template_string(HTML,
        fiyat=fiyat, log="\n".join(log_kaydi), durum="🟢" if simulasyon_aktif else "🔴", kalan_sure=kalan_sure,
        fiyat_atl=fiyat_atl, log_atl="\n".join(log_kaydi_atl), durum_atl="🟢" if simulasyon_aktif_atl else "🔴", kalan_sure_atl=kalan_sure_atl,
        session=session)

@app.route("/status")
def status():
    return jsonify({
        "fiyat": fiyat,
        "log": "\n".join(log_kaydi[-50:]),
        "durum": "🟢" if simulasyon_aktif else "🔴",
        "kalan_sure": kalan_sure,
        "simulasyon_aktif": simulasyon_aktif,

        "fiyat_atl": fiyat_atl,
        "log_atl": "\n".join(log_kaydi_atl[-50:]),
        "durum_atl": "🟢" if simulasyon_aktif_atl else "🔴",
        "kalan_sure_atl": kalan_sure_atl,
        "simulasyon_aktif_atl": simulasyon_aktif_atl,
    })

@app.route("/devam", methods=["POST"])
def devam():
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    data = request.get_json()
    sure = data.get("sure", 20)
    baslangic = data.get("baslangic")
    if not isinstance(sure, int) or sure < 5 or sure > 120:
        sure = 20
    threading.Thread(target=simulasyonu_baslat, args=(sure, baslangic)).start()
    return ('', 204)

@app.route("/durdur", methods=["POST"])
def durdur():
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    global simulasyon_aktif
    with lock:
        simulasyon_aktif = False
    return ('', 204)

@app.route("/temizle", methods=["POST"])
def temizle():
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    global log_kaydi
    with lock:
        log_kaydi.clear()
        log_kaydi.append("🧹 Log temizlendi.")
    return ('', 204)

@app.route("/devam_atl", methods=["POST"])
def devam_atl():
    if not session.get("giris_atl"):
        return "Yetkisiz", 403
    data = request.get_json()
    sure = data.get("sure", 20)
    baslangic = data.get("baslangic")
    if not isinstance(sure, int) or sure < 5 or sure > 120:
        sure = 20
    threading.Thread(target=simulasyonu_baslat_atl, args=(sure, baslangic)).start()
    return ('', 204)

@app.route("/durdur_atl", methods=["POST"])
def durdur_atl():
    if not session.get("giris_atl"):
        return "Yetkisiz", 403
    global simulasyon_aktif_atl
    with lock:
        simulasyon_aktif_atl = False
    return ('', 204)

@app.route("/temizle_atl", methods=["POST"])
def temizle_atl():
    if not session.get("giris_atl"):
        return "Yetkisiz", 403
    global log_kaydi_atl
    with lock:
        log_kaydi_atl.clear()
        log_kaydi_atl.append("🧹 ATL Log temizlendi.")
    return ('', 204)

@app.route("/login", methods=["POST"])
def login():
    sifre = request.form.get("password")
    if sifre == "tavuk123":
        session["giris_tavuk"] = True
        log_kaydi.append("✅ TAVUKBIT girişi yapıldı.")
    elif sifre == "ATL123":
        session["giris_atl"] = True
        log_kaydi_atl.append("✅ ATL COIN girişi yapıldı.")
    else:
        log_kaydi.append("🚫 Hatalı şifre denemesi.")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("giris_tavuk", None)
    session.pop("giris_atl", None)
    log_kaydi.append("👋 TAVUKBIT çıkış yapıldı.")
    log_kaydi_atl.append("👋 ATL COIN çıkış yapıldı.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

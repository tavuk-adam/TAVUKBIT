# -*- coding: utf-8 -*-
"""
TAVUKBIT Elmas Fiyat Simülasyonu
Bu script, bir Python Flask uygulamasıdır.
Bir arka plan thread'i içinde TAVUKBIT Elmas fiyat simülasyonunu çalıştırır.
Kullanıcıların web arayüzü üzerinden fiyatı başlatmasına, durdurmasına ve
fiyat değişim eğilimini değiştirmesine olanak tanır.
"""

import threading
import time
import random
import secrets
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import atexit

# Global variables and lock for thread-safe access
price = 0
is_running = False
thread_stop_event = threading.Event()
price_lock = threading.Lock()
log_data = []
announcement = ""
meille_dusme_seviye = 0
meille_yukselme_seviye = 0
price_history_for_stats = []

# Flask App configuration
app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

# Admin password
ADMIN_PASSWORD = "chicken123"


def price_simulation():
    """
    Arka plan fiyat simülasyonunu çalıştıran thread fonksiyonu.
    """
    global price, log_data, announcement, price_lock, meille_dusme_seviye, meille_yukselme_seviye, price_history_for_stats

    while not thread_stop_event.is_set():
        with price_lock:
            if is_running:
                # Determine price change probability based on 'meille' levels
                weights = [1, 1, 1, 1, 1]
                if meille_dusme_seviye > 0:
                    weights[0] += meille_dusme_seviye * 2
                    weights[1] += meille_dusme_seviye
                elif meille_yukselme_seviye > 0:
                    weights[3] += meille_yukselme_seviye
                    weights[4] += meille_yukselme_seviye * 2

                change = random.choices([-2, -1, 0, 1, 2], weights=weights, k=1)[0]
                price += change

                # Fiyatın negatif olmasını engelleme
                if price <= 0:
                    price = 1
                    log_data.append("UYARI: Fiyat sıfırın altına düştüğü için 1'e yükseltildi.")

                # Add log entry
                log_data.append(f"Fiyat değişimi: {change:+} (Güncel Fiyat: {price})")
                if len(log_data) > 50:
                    log_data.pop(0)

                # Store prices in an in-memory list for stats
                price_history_for_stats.append(price)
                if len(price_history_for_stats) > 60:
                    price_history_for_stats.pop(0)

        thread_stop_event.wait(1)


@app.route('/')
def index():
    """
    Ana sayfayı render eder.
    """
    return render_template_string(HTML_TEMPLATE)


@app.route('/login', methods=['POST'])
def login():
    """
    Admin şifresini kontrol eder ve oturum açar.
    """
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['giris_tavuk'] = True
        return redirect(url_for('index'))
    return jsonify({"error": "Geçersiz şifre"}), 401


@app.route('/logout')
def logout():
    """
    Oturumu sonlandırır.
    """
    session.pop('giris_tavuk', None)
    return redirect(url_for('index'))


@app.route('/status')
def status():
    """
    Web arayüzü için güncel durumu JSON formatında döner.
    """
    with price_lock:
        return jsonify({
            "price": price,
            "isRunning": is_running,
            "log": "\n".join(log_data),
            "announcement": announcement,
            "meille_dusme": meille_dusme_seviye,
            "meille_yukselme": meille_yukselme_seviye,
            "is_admin": session.get('giris_tavuk', False)
        })


@app.route('/stats')
def get_stats():
    """
    Returns real-time statistics for the admin panel.
    """
    with price_lock:
        if price_history_for_stats:
            max_price = max(price_history_for_stats)
            min_price = min(price_history_for_stats)
            avg_price = sum(price_history_for_stats) / len(price_history_for_stats)
        else:
            max_price, min_price, avg_price = price, price, price

        return jsonify({
            "max_price": max_price,
            "min_price": min_price,
            "avg_price": avg_price
        })


@app.route('/devam', methods=['POST'])
def start_simulation():
    """
    Simülasyonu başlatır ve isteğe bağlı olarak başlangıç fiyatını ayarlar.
    """
    global is_running, price
    if not session.get('giris_tavuk'):
        return "Yetkisiz Erişim", 403

    data = request.json
    new_price_str = data.get('new_price')

    with price_lock:
        if new_price_str:
            try:
                new_price = float(new_price_str)
                if new_price > 0:
                    price = new_price
                    log_data.append(f"Admin simülasyonu {int(price)} Elmas'tan başlattı.")
                else:
                    log_data.append("Uyarı: Geçersiz başlangıç fiyatı. Mevcut fiyattan devam ediliyor.")
            except (ValueError, TypeError):
                log_data.append("Uyarı: Geçersiz başlangıç fiyatı formatı. Mevcut fiyattan devam ediliyor.")

        is_running = True

    return "OK"


@app.route('/durdur')
def stop_simulation():
    """
    Simülasyonu durdurur. Sadece admin erişimi.
    """
    global is_running
    if not session.get('giris_tavuk'):
        return "Yetkisiz Erişim", 403
    with price_lock:
        is_running = False
    return "OK"


@app.route('/temizle')
def clear_log():
    """
    Log kaydını temizler. Sadece admin erişimi.
    """
    global log_data
    if not session.get('giris_tavuk'):
        return "Yetkisiz Erişim", 403
    with price_lock:
        log_data = []
    return "OK"


@app.route('/duyuru_yap', methods=['POST'])
def make_announcement():
    """
    Yeni bir duyuru ekler. Sadece admin erişimi.
    """
    global announcement
    if not session.get('giris_tavuk'):
        return "Yetkisiz Erişim", 403
    new_announcement = request.json.get('text', '')
    with price_lock:
        announcement = new_announcement
    return "OK"


@app.route('/meille_dusme_artir')
def increase_meille_dusme():
    """
    Düşüş optimizasyon seviyesini artırır. Sadece admin erişimi.
    """
    global meille_dusme_seviye, meille_yukselme_seviye
    if not session.get('giris_tavuk'):
        return "Yetkisiz Erişim", 403
    with price_lock:
        if meille_dusme_seviye < 15:
            meille_dusme_seviye += 1
            meille_yukselme_seviye = 0
    return "OK"


@app.route('/meille_dusme_azalt')
def decrease_meille_dusme():
    """
    Düşüş optimizasyon seviyesini azaltır. Sadece admin erişimi.
    """
    global meille_dusme_seviye
    if not session.get('giris_tavuk'):
        return "Yetkisiz Erişim", 403
    with price_lock:
        if meille_dusme_seviye > 0:
            meille_dusme_seviye -= 1
    return "OK"


@app.route('/meille_yukselme_artir')
def increase_meille_yukselme():
    """
    Yükseliş optimizasyon seviyesini artırır. Sadece admin erişimi.
    """
    global meille_dusme_seviye, meille_yukselme_seviye
    if not session.get('giris_tavuk'):
        return "Yetkisiz Erişim", 403
    with price_lock:
        if meille_yukselme_seviye < 15:
            meille_yukselme_seviye += 1
            meille_dusme_seviye = 0
    return "OK"


@app.route('/meille_yukselme_azalt')
def decrease_meille_yukselme():
    """
    Yükseliş optimizasyon seviyesini azaltır. Sadece admin erişimi.
    """
    global meille_yukselme_seviye
    if not session.get('giris_tavuk'):
        return "Yetkisiz Erişim", 403
    with price_lock:
        if meille_yukselme_seviye > 0:
            meille_yukselme_seviye -= 1
    return "OK"


@app.route('/schedule_price_change', methods=['POST'])
def schedule_price_change():
    # Bu özellik veritabanı olmadan çalışmaz, bu nedenle kaldırıldı veya işlevsiz hale getirildi
    return "Bu özellik veritabanı olmadan kullanılamaz.", 400


@app.route('/get_announcement_templates')
def get_announcement_templates():
    """Returns a list of predefined announcement templates."""
    templates = [
        "Fiyatlar fırladı! Büyük yükseliş başladı!",
        "İndirim başladı! TAVUKBIT elmasları şimdi daha ucuz!",
        "Piyasada dalgalanma var, dikkatli olun.",
        "Yeni güncelleme geliyor, fiyatlar etkilenebilir."
    ]
    return jsonify(templates)


# HTML/CSS/JS content as a Python string
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TAVUKBIT Simülasyonu</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/luxon@3.4.3/build/global/luxon.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-luxon@1.3.1/dist/chartjs-adapter-luxon.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            background-color: #f8f9fa;
            color: #212529;
            transition: background-color 0.3s, color 0.3s;
        }
        .dark-mode {
            background-color: #212529;
            color: #f8f9fa;
        }
        .dark-mode .card, .dark-mode .form-control, .dark-mode .list-group-item, .dark-mode .btn-secondary, .dark-mode .btn-outline-dark {
            background-color: #343a40 !important;
            color: #f8f9fa !important;
            border-color: #6c757d !important;
        }
        .dark-mode .card-header {
            background-color: #454d55 !important;
        }
        .dark-mode .btn-primary {
            background-color: #0069d9 !important;
            border-color: #0062cc !important;
        }
        .card {
            border-radius: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .btn-meille {
            font-size: 1.5rem;
            width: 40px;
            height: 40px;
            padding: 0;
            line-height: 1;
        }
        .status-icon {
            font-size: 1.5rem;
            vertical-align: middle;
        }
        #price-display {
            font-size: 3rem;
            font-weight: bold;
        }
        .theme-switch {
            cursor: pointer;
            font-size: 1.5rem;
            position: absolute;
            top: 1rem;
            right: 1rem;
        }
        .stat-card {
            font-size: 1.2rem;
            font-weight: bold;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container my-5">
        <div class="row justify-content-center">
            <div class="col-lg-10">
                <div class="text-center mb-4">
                    <h1 class="display-4 fw-bold">TAVUKBIT Elmas Fiyat Simülasyonu</h1>
                    <span class="theme-switch" onclick="toggleTheme()"><i id="theme-icon" class="fa-solid fa-moon"></i></span>
                </div>

                <div class="card p-4 mb-4">
                    <div class="card-header bg-primary text-white text-center">
                        <h4 class="mb-0">Güncel TAVUKBIT Fiyatı</h4>
                    </div>
                    <div class="card-body text-center">
                        <h2 id="price-display" class="my-3">Yükleniyor...</h2>
                        <h4 class="mt-4">Duyuru: <span id="announcement-display" class="fw-light"></span></h4>
                    </div>
                </div>

                <div class="card p-4 mb-4">
                    <div class="card-header bg-success text-white text-center">
                        <h4 class="mb-0">Canlı Fiyat Grafiği</h4>
                    </div>
                    <div class="card-body">
                        <canvas id="priceChart"></canvas>
                    </div>
                </div>

                <div id="login-panel" class="card p-4 mb-4">
                    <div class="card-header bg-secondary text-white text-center">
                        <h4 class="mb-0">Admin Girişi</h4>
                    </div>
                    <div class="card-body">
                        <form id="login-form">
                            <div class="input-group mb-3">
                                <input type="password" id="password-input" class="form-control" placeholder="Şifre" required>
                                <button type="submit" class="btn btn-primary">Giriş Yap</button>
                            </div>
                            <div id="login-message" class="text-danger mt-2"></div>
                        </form>
                    </div>
                </div>

                <div id="admin-panel" class="card p-4" style="display: none;">
                    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">Admin Kontrol Paneli</h4>
                        <button id="logout-btn" class="btn btn-sm btn-outline-light">Çıkış Yap</button>
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">Simülasyon Kontrolleri</h5>
                        <hr>
                        <div class="d-flex align-items-center mb-3">
                            <span id="status-icon" class="status-icon me-2"></span>
                            <span id="status-text" class="fw-bold">Durum:</span>
                        </div>
                        <div class="d-flex align-items-center gap-2 mb-4">
                            <input type="number" id="start-price-input" class="form-control" placeholder="Başlangıç Fiyatı (Opsiyonel)">
                            <button id="start-btn" class="btn btn-success fw-bold text-nowrap"><i class="fa-solid fa-play"></i> Devam</button>
                            <button id="stop-btn" class="btn btn-danger fw-bold text-nowrap"><i class="fa-solid fa-stop"></i> Durdur</button>
                        </div>

                        <h5 class="card-title mt-4">Piyasa İstatistikleri</h5>
                        <hr>
                        <div class="row text-center mb-4">
                            <div class="col-4">
                                <div class="stat-card">
                                    <p class="mb-0">En Yüksek Fiyat</p>
                                    <h4 id="max-price">...</h4>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="stat-card">
                                    <p class="mb-0">En Düşük Fiyat</p>
                                    <h4 id="min-price">...</h4>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="stat-card">
                                    <p class="mb-0">Ortalama Fiyat</p>
                                    <h4 id="avg-price">...</h4>
                                </div>
                            </div>
                        </div>

                        <h5 class="card-title mt-4">Meilleştirme Kontrolleri</h5>
                        <hr>
                        <div class="row mb-3">
                            <div class="col-6">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <h6 class="card-subtitle mb-2">Düşüş Optimisazyonu</h6>
                                        <div class="d-flex justify-content-center align-items-center my-2">
                                            <button id="decrease-down-btn" class="btn btn-outline-danger btn-meille">-</button>
                                            <span id="meille-down-level" class="mx-3 fw-bold">0</span>
                                            <button id="increase-down-btn" class="btn btn-outline-success btn-meille">+</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="card">
                                    <div class="card-body text-center">
                                        <h6 class="card-subtitle mb-2">Yükseliş Optimisazyonu</h6>
                                        <div class="d-flex justify-content-center align-items-center my-2">
                                            <button id="decrease-up-btn" class="btn btn-outline-danger btn-meille">-</button>
                                            <span id="meille-up-level" class="mx-3 fw-bold">0</span>
                                            <button id="increase-up-btn" class="btn btn-outline-success btn-meille">+</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <h5 class="card-title mt-4">Duyuru Yönetimi</h5>
                        <hr>
                        <div id="announcement-alert" class="alert d-none" role="alert"></div>
                        <div class="input-group mb-3">
                            <input type="text" id="announcement-input" class="form-control" placeholder="Yeni duyuru yazın...">
                            <button id="announce-btn" class="btn btn-primary">Duyur</button>
                        </div>
                        <div class="dropdown">
                            <button class="btn btn-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                                Duyuru Şablonları
                            </button>
                            <ul id="announcement-templates" class="dropdown-menu">
                                </ul>
                        </div>
                        <h5 class="card-title mt-4">Otomatik Fiyat Değişimi Planla</h5>
                        <hr>
                        <div class="alert alert-info" role="alert">Bu özellik, veritabanı olmadan kullanılamaz.</div>
                        <form id="schedule-form" onsubmit="return false;">
                            <div class="row g-3">
                                <div class="col-md-5">
                                    <input type="datetime-local" id="schedule-time" class="form-control" required disabled>
                                </div>
                                <div class="col-md-4">
                                    <select id="schedule-action" class="form-select" required disabled>
                                        <option value="">İşlem Seç...</option>
                                        <option value="increase_price">Fiyat Arttır</option>
                                        <option value="decrease_price">Fiyat Azalt</option>
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <input type="number" id="schedule-value" class="form-control" placeholder="Değer" required disabled>
                                </div>
                                <div class="col-12">
                                    <button type="submit" class="btn btn-info w-100" disabled>Planla</button>
                                </div>
                            </div>
                        </form>

                        <h5 class="card-title mt-4">Log Kaydı</h5>
                        <hr>
                        <button id="clear-log-btn" class="btn btn-secondary btn-sm mb-2">Log Kaydını Temizle</button>
                        <textarea id="log-display" class="form-control" rows="10" readonly></textarea>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const loginPanel = document.getElementById('login-panel');
        const adminPanel = document.getElementById('admin-panel');
        const priceDisplay = document.getElementById('price-display');
        const announcementDisplay = document.getElementById('announcement-display');
        const statusIcon = document.getElementById('status-icon');
        const statusText = document.getElementById('status-text');
        const logDisplay = document.getElementById('log-display');
        const themeIcon = document.getElementById('theme-icon');
        const chartCanvas = document.getElementById('priceChart').getContext('2d');
        const maxPriceEl = document.getElementById('max-price');
        const minPriceEl = document.getElementById('min-price');
        const avgPriceEl = document.getElementById('avg-price');

        let chart;
        let priceHistory = [];
        const maxDataPoints = 60; // Keep the last 60 seconds of data
        const alertThreshold = 500; // Price threshold for the alert

        // Initialize theme based on localStorage
        const currentTheme = localStorage.getItem('theme') || 'light';
        document.body.classList.toggle('dark-mode', currentTheme === 'dark');
        themeIcon.classList.toggle('fa-moon', currentTheme === 'light');
        themeIcon.classList.toggle('fa-sun', currentTheme === 'dark');

        function toggleTheme() {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            themeIcon.classList.toggle('fa-moon', !isDark);
            themeIcon.classList.toggle('fa-sun', isDark);
            updateChartTheme(isDark);
        }

        function updateChartTheme(isDark) {
            const textColor = isDark ? '#f8f9fa' : '#212529';
            const gridColor = isDark ? 'rgba(248, 249, 250, 0.2)' : 'rgba(33, 37, 41, 0.2)';
            if (chart) {
                chart.options.scales.x.ticks.color = textColor;
                chart.options.scales.y.ticks.color = textColor;
                chart.options.scales.x.grid.color = gridColor;
                chart.options.scales.y.grid.color = gridColor;
                chart.update();
            }
        }

        // Fetch and update status every second
        setInterval(async () => {
            try {
                const response = await fetch('/status');
                const data = await response.json();

                // Public View Update
                priceDisplay.innerText = `${data.price.toFixed(0)} Elmas`;
                announcementDisplay.innerText = data.announcement;

                // Chart Update
                const now = new Date();
                priceHistory.push({ x: now.getTime(), y: data.price });
                if (priceHistory.length > maxDataPoints) {
                    priceHistory.shift();
                }

                if (chart) {
                    chart.data.labels = priceHistory.map(item => item.x);
                    chart.data.datasets[0].data = priceHistory.map(item => item.y);
                    chart.update();
                }

                // Admin Panel Update (if logged in)
                if (data.is_admin) {
                    loginPanel.style.display = 'none';
                    adminPanel.style.display = 'block';
                    logDisplay.value = data.log;
                    document.getElementById('meille-down-level').innerText = data.meille_dusme;
                    document.getElementById('meille-up-level').innerText = data.meille_yukselme;

                    if (data.isRunning) {
                        statusIcon.innerHTML = '<i class="fa-solid fa-circle text-success"></i>';
                        statusText.innerText = "Durum: Aktif";
                    } else {
                        statusIcon.innerHTML = '<i class="fa-solid fa-circle text-danger"></i>';
                        statusText.innerText = "Durum: Durduruldu";
                    }

                    // Price Alerts
                    const alertDiv = document.getElementById('announcement-alert');
                    if (data.price > alertThreshold) {
                        alertDiv.innerText = `Uyarı: Fiyat çok yüksek (${data.price})! Düşüş başlatmayı düşünebilirsiniz.`;
                        alertDiv.classList.remove('d-none');
                        alertDiv.classList.remove('alert-info');
                        alertDiv.classList.add('alert-warning');
                    } else {
                        alertDiv.classList.add('d-none');
                    }
                } else {
                    loginPanel.style.display = 'block';
                    adminPanel.style.display = 'none';
                }
            } catch (error) {
                console.error("Durum verisi alınırken hata oluştu:", error);
            }
        }, 1000);

        // Fetch and update stats
        setInterval(async () => {
            const response = await fetch('/stats');
            const data = await response.json();
            maxPriceEl.innerText = data.max_price.toFixed(2);
            minPriceEl.innerText = data.min_price.toFixed(2);
            avgPriceEl.innerText = data.avg_price.toFixed(2);
        }, 5000);

        // Fetch and populate announcement templates
        async function fetchTemplates() {
            const response = await fetch('/get_announcement_templates');
            const templates = await response.json();
            const templateList = document.getElementById('announcement-templates');
            templateList.innerHTML = ''; // Clear existing templates
            templates.forEach(template => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.className = 'dropdown-item';
                a.href = '#';
                a.innerText = template;
                a.onclick = () => {
                    document.getElementById('announcement-input').value = template;
                };
                li.appendChild(a);
                templateList.appendChild(li);
            });
        }
        fetchTemplates();

        // Event Listeners for Buttons
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const password = document.getElementById('password-input').value;
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `password=${encodeURIComponent(password)}`
            });
            if (!response.ok) {
                document.getElementById('login-message').innerText = "Hatalı şifre. Lütfen tekrar deneyin.";
            } else {
                document.getElementById('login-message').innerText = "";
            }
        });

        document.getElementById('logout-btn').addEventListener('click', () => {
            window.location.href = '/logout';
        });

        document.getElementById('start-btn').addEventListener('click', () => {
            const newPrice = document.getElementById('start-price-input').value;
            fetch('/devam', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_price: newPrice })
            });
        });

        document.getElementById('stop-btn').addEventListener('click', () => fetch('/durdur'));
        document.getElementById('clear-log-btn').addEventListener('click', () => fetch('/temizle'));

        document.getElementById('announce-btn').addEventListener('click', () => {
            const text = document.getElementById('announcement-input').value;
            fetch('/duyuru_yap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
        });

        document.getElementById('increase-down-btn').addEventListener('click', () => fetch('/meille_dusme_artir'));
        document.getElementById('decrease-down-btn').addEventListener('click', () => fetch('/meille_dusme_azalt'));
        document.getElementById('increase-up-btn').addEventListener('click', () => fetch('/meille_yukselme_artir'));
        document.getElementById('decrease-up-btn').addEventListener('click', () => fetch('/meille_yukselme_azalt'));

        // Schedule Price Change form is disabled as it requires a database
        document.getElementById('schedule-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            alert('Bu özellik veritabanı olmadan kullanılamaz.');
        });

        // Initialize Chart
        function initChart() {
            chart = new Chart(chartCanvas, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'TAVUKBIT Elmas Fiyatı',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'second'
                            },
                            title: {
                                display: true,
                                text: 'Zaman'
                            }
                        },
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Fiyat (Elmas)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // Initial chart setup and theme update
        initChart();
        updateChartTheme(document.body.classList.contains('dark-mode'));

    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # Start the simulation thread
    thread = threading.Thread(target=price_simulation)
    thread.daemon = True
    thread.start()

    # Register a cleanup function to stop the thread gracefully on exit
    def shutdown_server():
        thread_stop_event.set()
        thread.join()

    atexit.register(shutdown_server)

    # Run the application on all available public IPs
    app.run(host='0.0.0.0', debug=True, use_reloader=False)

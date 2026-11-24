"""Uygulamanın giriş noktası. Çalıştırmak için:  python app.py"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from pymysql import MySQLError

from routes.auth import bp as auth_bp
from routes.kds import bp as kds_bp
from routes.kullanicilar import bp as kullanicilar_bp
from routes.satis import bp as satis_bp
from routes.stok import bp as stok_bp
from routes.tanimlar import kategoriler_bp, markalar_bp
from routes.urunler import bp as urunler_bp

load_dotenv()

# Frontend dosyaları reponun frontend/ klasöründen sunulur -> tek adres, tek sunucu
FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND, static_url_path="")
app.secret_key = os.getenv("SECRET_KEY", "gelistirme-icin-gecici-anahtar")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.json.ensure_ascii = False  # Türkçe karakterler JSON'da düzgün görünsün
CORS(app, supports_credentials=True)

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(kullanicilar_bp, url_prefix="/api/kullanicilar")
app.register_blueprint(kategoriler_bp, url_prefix="/api/kategoriler")
app.register_blueprint(markalar_bp, url_prefix="/api/markalar")
app.register_blueprint(urunler_bp, url_prefix="/api/urunler")
app.register_blueprint(stok_bp, url_prefix="/api/stok")
app.register_blueprint(satis_bp, url_prefix="/api/satis")
app.register_blueprint(kds_bp, url_prefix="/api/kds")


@app.get("/")
def ana_sayfa():
    if os.path.exists(os.path.join(FRONTEND, "index.html")):
        return send_from_directory(FRONTEND, "index.html")
    return jsonify({"mesaj": "Backend çalışıyor. frontend/index.html henüz yok."})


@app.get("/api/saglik")
def saglik():
    return jsonify({"durum": "calisiyor"})


@app.errorhandler(MySQLError)
def db_hatasi(e):
    return jsonify({"hata": "Veritabanı hatası", "detay": str(e)}), 500


@app.errorhandler(404)
def bulunamadi(e):
    return jsonify({"hata": "Adres bulunamadı"}), 404


@app.errorhandler(405)
def yanlis_metot(e):
    return jsonify({"hata": "Bu adres bu metotla (GET/POST...) kullanılamaz"}), 405


if __name__ == "__main__":
    app.run(debug=True, port=5000)

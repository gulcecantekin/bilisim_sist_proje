"""Giriş / çıkış / oturum bilgisi / şifre değiştirme."""
from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from db import calistir, sorgu
from yetki import giris_gerekli

bp = Blueprint("auth", __name__)


@bp.post("/giris")
def giris():
    """Gövde: {"kullanici_adi": "yonetici", "sifre": "yonetici123"}"""
    veri = request.get_json(silent=True) or {}
    k = sorgu("SELECT * FROM kullanicilar WHERE kullanici_adi=%s AND aktif=1",
              (veri.get("kullanici_adi", ""),), tek=True)
    if not k or not check_password_hash(k["sifre_hash"], veri.get("sifre", "")):
        return jsonify({"hata": "Kullanıcı adı veya şifre hatalı"}), 401

    session.clear()
    session["kullanici_id"] = k["id"]
    session["rol"] = k["rol"]
    session["ad_soyad"] = k["ad_soyad"]
    return jsonify({"mesaj": "Giriş başarılı",
                    "kullanici": {"id": k["id"], "ad_soyad": k["ad_soyad"], "rol": k["rol"]}})


@bp.post("/cikis")
def cikis():
    session.clear()
    return jsonify({"mesaj": "Çıkış yapıldı"})


@bp.get("/ben")
@giris_gerekli
def ben():
    """Frontend sayfa açılınca bunu çağırır: kim giriş yapmış, rolü ne?"""
    return jsonify({"id": session["kullanici_id"], "ad_soyad": session["ad_soyad"],
                    "rol": session["rol"]})


@bp.post("/sifre-degistir")
@giris_gerekli
def sifre_degistir():
    """Gövde: {"eski_sifre": "...", "yeni_sifre": "..."}"""
    veri = request.get_json(silent=True) or {}
    yeni = veri.get("yeni_sifre", "")
    if len(yeni) < 6:
        return jsonify({"hata": "Yeni şifre en az 6 karakter olmalı"}), 400
    k = sorgu("SELECT sifre_hash FROM kullanicilar WHERE id=%s", (session["kullanici_id"],), tek=True)
    if not check_password_hash(k["sifre_hash"], veri.get("eski_sifre", "")):
        return jsonify({"hata": "Eski şifre hatalı"}), 400
    calistir("UPDATE kullanicilar SET sifre_hash=%s WHERE id=%s",
             (generate_password_hash(yeni), session["kullanici_id"]))
    return jsonify({"mesaj": "Şifre değiştirildi"})

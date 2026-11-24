"""Kullanıcı yönetimi (sadece yönetici)."""
from flask import Blueprint, jsonify, request, session
from pymysql.err import IntegrityError
from werkzeug.security import generate_password_hash

from db import calistir, sorgu
from yetki import yonetici_gerekli

bp = Blueprint("kullanicilar", __name__)


@bp.get("")
@yonetici_gerekli
def listele():
    # sifre_hash asla dışarı gönderilmez
    return jsonify(sorgu("SELECT id, ad_soyad, kullanici_adi, rol, aktif, olusturma_tarihi "
                         "FROM kullanicilar ORDER BY rol, ad_soyad"))


@bp.post("")
@yonetici_gerekli
def ekle():
    """Gövde: {"ad_soyad", "kullanici_adi", "sifre", "rol": "calisan" | "yonetici"}"""
    veri = request.get_json(silent=True) or {}
    if not veri.get("ad_soyad") or not veri.get("kullanici_adi") or len(veri.get("sifre", "")) < 6:
        return jsonify({"hata": "ad_soyad, kullanici_adi ve en az 6 karakterli sifre gerekli"}), 400
    rol = veri.get("rol", "calisan")
    if rol not in ("calisan", "yonetici"):
        return jsonify({"hata": "rol 'calisan' veya 'yonetici' olmalı"}), 400
    try:
        _, yeni_id = calistir(
            "INSERT INTO kullanicilar (ad_soyad, kullanici_adi, sifre_hash, rol) VALUES (%s,%s,%s,%s)",
            (veri["ad_soyad"], veri["kullanici_adi"], generate_password_hash(veri["sifre"]), rol))
    except IntegrityError:
        return jsonify({"hata": "Bu kullanıcı adı alınmış"}), 409
    return jsonify({"mesaj": "Kullanıcı eklendi", "id": yeni_id}), 201


@bp.put("/<int:kid>/aktiflik")
@yonetici_gerekli
def aktiflik(kid):
    """Gövde: {"aktif": false}  -> kullanıcı giriş yapamaz ama geçmiş satışları korunur."""
    if kid == session["kullanici_id"]:
        return jsonify({"hata": "Kendinizi pasif yapamazsınız"}), 400
    aktif = 1 if (request.get_json(silent=True) or {}).get("aktif") else 0
    etkilenen, _ = calistir("UPDATE kullanicilar SET aktif=%s WHERE id=%s", (aktif, kid))
    if etkilenen == 0 and not sorgu("SELECT id FROM kullanicilar WHERE id=%s", (kid,), tek=True):
        return jsonify({"hata": "Kullanıcı bulunamadı"}), 404
    return jsonify({"mesaj": "Kullanıcı aktif" if aktif else "Kullanıcı pasif yapıldı"})


@bp.put("/<int:kid>/sifre")
@yonetici_gerekli
def sifre_sifirla(kid):
    """Çalışan şifresini unutursa yönetici sıfırlar. Gövde: {"yeni_sifre": "..."}"""
    yeni = (request.get_json(silent=True) or {}).get("yeni_sifre", "")
    if len(yeni) < 6:
        return jsonify({"hata": "Şifre en az 6 karakter olmalı"}), 400
    etkilenen, _ = calistir("UPDATE kullanicilar SET sifre_hash=%s WHERE id=%s",
                            (generate_password_hash(yeni), kid))
    if etkilenen == 0:
        return jsonify({"hata": "Kullanıcı bulunamadı"}), 404
    return jsonify({"mesaj": "Şifre sıfırlandı"})

"""Yetki kontrolleri. Bir endpoint'in üstüne @giris_gerekli veya @yonetici_gerekli yazınca
giriş yapmamış (401) ya da yetkisi olmayan (403) kişiler o endpoint'i kullanamaz."""
from functools import wraps

from flask import jsonify, session


def giris_gerekli(f):
    @wraps(f)
    def sarmal(*args, **kwargs):
        if "kullanici_id" not in session:
            return jsonify({"hata": "Önce giriş yapmalısınız"}), 401
        return f(*args, **kwargs)
    return sarmal


def yonetici_gerekli(f):
    @wraps(f)
    def sarmal(*args, **kwargs):
        if "kullanici_id" not in session:
            return jsonify({"hata": "Önce giriş yapmalısınız"}), 401
        if session.get("rol") != "yonetici":
            return jsonify({"hata": "Bu işlem için yönetici yetkisi gerekli"}), 403
        return f(*args, **kwargs)
    return sarmal


def aktif_kullanici_id():
    return session.get("kullanici_id")

"""Kategoriler ve markalar. İkisi de aynı yapıda (id + ad) olduğu için tek kalıptan üretiliyor."""
from flask import Blueprint, jsonify, request
from pymysql.err import IntegrityError

from db import calistir, sorgu
from yetki import giris_gerekli, yonetici_gerekli


def tanim_blueprint(ad, tablo, kolon, etiket):
    bp = Blueprint(ad, __name__)

    @bp.get("")
    @giris_gerekli
    def listele():
        return jsonify(sorgu(f"SELECT * FROM {tablo} ORDER BY {kolon}"))

    @bp.post("")
    @yonetici_gerekli
    def ekle():
        deger = ((request.get_json(silent=True) or {}).get(kolon) or "").strip()
        if not deger:
            return jsonify({"hata": f"{kolon} gerekli"}), 400
        try:
            _, yeni_id = calistir(f"INSERT INTO {tablo} ({kolon}) VALUES (%s)", (deger,))
        except IntegrityError:
            return jsonify({"hata": f"Bu {etiket} zaten var"}), 409
        return jsonify({"mesaj": f"{etiket.capitalize()} eklendi", "id": yeni_id}), 201

    @bp.put("/<int:tid>")
    @yonetici_gerekli
    def guncelle(tid):
        deger = ((request.get_json(silent=True) or {}).get(kolon) or "").strip()
        if not deger:
            return jsonify({"hata": f"{kolon} gerekli"}), 400
        try:
            calistir(f"UPDATE {tablo} SET {kolon}=%s WHERE id=%s", (deger, tid))
        except IntegrityError:
            return jsonify({"hata": f"Bu {etiket} zaten var"}), 409
        return jsonify({"mesaj": f"{etiket.capitalize()} güncellendi"})

    @bp.delete("/<int:tid>")
    @yonetici_gerekli
    def sil(tid):
        try:
            etkilenen, _ = calistir(f"DELETE FROM {tablo} WHERE id=%s", (tid,))
        except IntegrityError:
            return jsonify({"hata": f"Bu {etiket} ürünlerde kullanılıyor, silinemez"}), 409
        if etkilenen == 0:
            return jsonify({"hata": f"{etiket.capitalize()} bulunamadı"}), 404
        return jsonify({"mesaj": f"{etiket.capitalize()} silindi"})

    return bp


kategoriler_bp = tanim_blueprint("kategoriler", "kategoriler", "kategori_adi", "kategori")
markalar_bp = tanim_blueprint("markalar", "markalar", "marka_adi", "marka")

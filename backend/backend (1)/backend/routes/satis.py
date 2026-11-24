"""Satış ve iade. Satış kaydı + stok düşme TEK TRANSACTION içinde yapılır:
biri başarısız olursa hiçbiri kaydedilmez."""
from flask import Blueprint, jsonify, request, session

from db import get_conn, sorgu
from yetki import aktif_kullanici_id, giris_gerekli

bp = Blueprint("satis", __name__)


@bp.post("")
@giris_gerekli
def satis_yap():
    """Gövde: {"sepet": [{"barkod": "869...", "adet": 2}, ...], "odeme_tipi": "nakit" | "kart"}"""
    veri = request.get_json(silent=True) or {}
    sepet, odeme = veri.get("sepet"), veri.get("odeme_tipi", "nakit")
    if odeme not in ("nakit", "kart"):
        return jsonify({"hata": "odeme_tipi 'nakit' veya 'kart' olmalı"}), 400
    if not sepet or not all(isinstance(k.get("adet"), int) and k["adet"] > 0 and k.get("barkod")
                            for k in sepet):
        return jsonify({"hata": "Sepet boş veya hatalı"}), 400
    # Aynı barkod sepette birden fazla satırda varsa tek satırda birleştir
    birlesik = {}
    for k in sepet:
        birlesik[k["barkod"]] = birlesik.get(k["barkod"], 0) + k["adet"]
    sepet = [{"barkod": b, "adet": a} for b, a in birlesik.items()]

    conn = get_conn()
    try:
        conn.begin()
        with conn.cursor() as cur:
            kalemler, toplam = [], 0
            for kalem in sepet:
                # FOR UPDATE: aynı anda iki satış aynı stoğu düşmesin
                cur.execute("SELECT id, urun_adi, satis_fiyati, alis_fiyati, stok_adedi "
                            "FROM urunler WHERE barkod=%s FOR UPDATE", (kalem["barkod"],))
                urun = cur.fetchone()
                if not urun:
                    conn.rollback()
                    return jsonify({"hata": f"Barkod bulunamadı: {kalem['barkod']}"}), 404
                if urun["stok_adedi"] < kalem["adet"]:
                    conn.rollback()
                    return jsonify({"hata": f"Yetersiz stok: {urun['urun_adi']} "
                                            f"(mevcut {urun['stok_adedi']})"}), 409
                kalemler.append((urun, kalem["adet"]))
                toplam += urun["satis_fiyati"] * kalem["adet"]

            cur.execute("INSERT INTO satislar (kullanici_id, odeme_tipi, toplam_tutar) VALUES (%s,%s,%s)",
                        (aktif_kullanici_id(), odeme, toplam))
            satis_id = cur.lastrowid
            for urun, adet in kalemler:
                cur.execute("INSERT INTO satis_detay (satis_id, urun_id, adet, birim_fiyat, birim_maliyet) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (satis_id, urun["id"], adet, urun["satis_fiyati"], urun["alis_fiyati"]))
                cur.execute("UPDATE urunler SET stok_adedi = stok_adedi - %s WHERE id=%s",
                            (adet, urun["id"]))
                cur.execute("INSERT INTO stok_hareketleri (urun_id, kullanici_id, tip, adet, aciklama) "
                            "VALUES (%s, %s, 'satis', %s, %s)",
                            (urun["id"], aktif_kullanici_id(), -adet, f"Satış #{satis_id}"))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify({"mesaj": "Satış tamamlandı", "satis_id": satis_id, "toplam": toplam}), 201


@bp.post("/<int:satis_id>/iade")
@giris_gerekli
def iade(satis_id):
    """Fiş numarasıyla iade. Gövde: {"barkod": "869...", "adet": 1}
    Satış detayına negatif satır eklenir -> ciro/kâr raporları otomatik düzelir; ürün stoğa geri girer."""
    veri = request.get_json(silent=True) or {}
    adet = veri.get("adet")
    if not veri.get("barkod") or not isinstance(adet, int) or adet <= 0:
        return jsonify({"hata": "barkod ve pozitif tam sayı adet gerekli"}), 400

    conn = get_conn()
    try:
        conn.begin()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM satislar WHERE id=%s FOR UPDATE", (satis_id,))
            if not cur.fetchone():
                conn.rollback()
                return jsonify({"hata": "Satış bulunamadı"}), 404
            cur.execute("SELECT d.urun_id, SUM(d.adet) AS kalan, "
                        "MAX(CASE WHEN d.adet > 0 THEN d.birim_fiyat END) AS fiyat, "
                        "MAX(CASE WHEN d.adet > 0 THEN d.birim_maliyet END) AS maliyet "
                        "FROM satis_detay d JOIN urunler u ON u.id=d.urun_id "
                        "WHERE d.satis_id=%s AND u.barkod=%s GROUP BY d.urun_id",
                        (satis_id, veri["barkod"]))
            satir = cur.fetchone()
            if not satir:
                conn.rollback()
                return jsonify({"hata": "Bu ürün bu fişte yok"}), 404
            if satir["kalan"] < adet:
                conn.rollback()
                return jsonify({"hata": f"En fazla {satir['kalan']} adet iade edilebilir"}), 409

            cur.execute("INSERT INTO satis_detay (satis_id, urun_id, adet, birim_fiyat, birim_maliyet) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (satis_id, satir["urun_id"], -adet, satir["fiyat"], satir["maliyet"]))
            cur.execute("UPDATE satislar SET toplam_tutar = toplam_tutar - %s WHERE id=%s",
                        (satir["fiyat"] * adet, satis_id))
            cur.execute("UPDATE urunler SET stok_adedi = stok_adedi + %s WHERE id=%s",
                        (adet, satir["urun_id"]))
            cur.execute("INSERT INTO stok_hareketleri (urun_id, kullanici_id, tip, adet, aciklama) "
                        "VALUES (%s, %s, 'iade', %s, %s)",
                        (satir["urun_id"], aktif_kullanici_id(), adet, f"Satış #{satis_id} iadesi"))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify({"mesaj": "İade alındı", "iade_tutari": satir["fiyat"] * adet}), 201


@bp.get("")
@giris_gerekli
def satislari_listele():
    # /api/satis?baslangic=2026-11-01&bitis=2026-11-30
    # Çalışan sadece kendi satışlarını, yönetici hepsini görür.
    bas = request.args.get("baslangic", "1970-01-01")
    bit = request.args.get("bitis", "2999-12-31")
    sql = ("SELECT s.*, k.ad_soyad AS satan FROM satislar s "
           "JOIN kullanicilar k ON k.id = s.kullanici_id WHERE DATE(s.tarih) BETWEEN %s AND %s ")
    params = [bas, bit]
    if session.get("rol") != "yonetici":
        sql += "AND s.kullanici_id = %s "
        params.append(aktif_kullanici_id())
    return jsonify(sorgu(sql + "ORDER BY s.tarih DESC", params))


@bp.get("/<int:satis_id>")
@giris_gerekli
def satis_detay(satis_id):
    satis = sorgu("SELECT s.*, k.ad_soyad AS satan FROM satislar s "
                  "JOIN kullanicilar k ON k.id = s.kullanici_id WHERE s.id=%s", (satis_id,), tek=True)
    if not satis:
        return jsonify({"hata": "Satış bulunamadı"}), 404
    satis["kalemler"] = sorgu(
        "SELECT d.adet, d.birim_fiyat, m.marka_adi, u.urun_adi, u.varyant, u.barkod "
        "FROM satis_detay d JOIN urunler u ON u.id = d.urun_id JOIN markalar m ON m.id = u.marka_id "
        "WHERE d.satis_id=%s ORDER BY d.id", (satis_id,))
    return jsonify(satis)

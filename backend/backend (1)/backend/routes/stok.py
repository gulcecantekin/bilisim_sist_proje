"""Stok modülü: mal kabul, sayım düzeltmesi, kritik stok, hareket geçmişi."""
from flask import Blueprint, jsonify, request

from db import get_conn, sorgu
from yetki import aktif_kullanici_id, giris_gerekli, yonetici_gerekli

bp = Blueprint("stok", __name__)


def _stok_degistir(barkod, hesapla, tip, aciklama):
    """Ürünü kilitler, yeni stoğu hesaplar, günceller ve hareketi kaydeder (tek transaction).
    hesapla(mevcut) -> (degisim, hata_mesaji)"""
    conn = get_conn()
    try:
        conn.begin()
        with conn.cursor() as cur:
            cur.execute("SELECT id, stok_adedi FROM urunler WHERE barkod=%s FOR UPDATE", (barkod,))
            urun = cur.fetchone()
            if not urun:
                conn.rollback()
                return None, ("Bu barkoda ait ürün yok", 404)
            degisim, hata = hesapla(urun["stok_adedi"])
            if hata:
                conn.rollback()
                return None, (hata, 400)
            cur.execute("UPDATE urunler SET stok_adedi = stok_adedi + %s WHERE id=%s",
                        (degisim, urun["id"]))
            cur.execute("INSERT INTO stok_hareketleri (urun_id, kullanici_id, tip, adet, aciklama) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (urun["id"], aktif_kullanici_id(), tip, degisim, aciklama))
        conn.commit()
        return degisim, None
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@bp.post("/giris")
@giris_gerekli
def stok_giris():
    """Mal kabul. Gövde: {"barkod": "869...", "adet": 10, "aciklama": "..."}"""
    veri = request.get_json(silent=True) or {}
    adet = veri.get("adet")
    if not veri.get("barkod") or not isinstance(adet, int) or adet <= 0:
        return jsonify({"hata": "barkod ve pozitif tam sayı adet gerekli"}), 400
    _, hata = _stok_degistir(veri["barkod"], lambda mevcut: (adet, None), "giris",
                             veri.get("aciklama") or "Mal kabul")
    if hata:
        return jsonify({"hata": hata[0]}), hata[1]
    return jsonify({"mesaj": f"{adet} adet stok eklendi"}), 201


@bp.post("/duzeltme")
@yonetici_gerekli
def sayim_duzeltme():
    """Sayımda rafta farklı sayı çıkarsa (kırılan, kaybolan ürün).
    Gövde: {"barkod": "869...", "sayilan_adet": 7, "aciklama": "2 tanesi kırık"}"""
    veri = request.get_json(silent=True) or {}
    sayilan = veri.get("sayilan_adet")
    if not veri.get("barkod") or not isinstance(sayilan, int) or sayilan < 0:
        return jsonify({"hata": "barkod ve 0 veya pozitif sayilan_adet gerekli"}), 400
    degisim, hata = _stok_degistir(
        veri["barkod"],
        lambda mevcut: (sayilan - mevcut, None if sayilan != mevcut else "Stok zaten bu sayıda"),
        "duzeltme", veri.get("aciklama") or "Sayım düzeltmesi")
    if hata:
        return jsonify({"hata": hata[0]}), hata[1]
    return jsonify({"mesaj": "Stok düzeltildi", "fark": degisim})


@bp.get("/kritik")
@giris_gerekli
def kritik_stok():
    return jsonify(sorgu(
        "SELECT u.id, m.marka_adi, u.urun_adi, u.varyant, u.barkod, u.stok_adedi, u.kritik_stok "
        "FROM urunler u JOIN markalar m ON m.id=u.marka_id "
        "WHERE u.stok_adedi <= u.kritik_stok ORDER BY u.stok_adedi"))


@bp.get("/hareketler")
@yonetici_gerekli
def hareketler():
    # İsteğe bağlı: ?urun_id=3
    urun_id = request.args.get("urun_id", type=int)
    sql = ("SELECT h.*, u.urun_adi, m.marka_adi, k.ad_soyad AS yapan FROM stok_hareketleri h "
           "JOIN urunler u ON u.id = h.urun_id JOIN markalar m ON m.id = u.marka_id "
           "LEFT JOIN kullanicilar k ON k.id = h.kullanici_id ")
    if urun_id:
        return jsonify(sorgu(sql + "WHERE h.urun_id=%s ORDER BY h.tarih DESC", (urun_id,)))
    return jsonify(sorgu(sql + "ORDER BY h.tarih DESC LIMIT 200"))

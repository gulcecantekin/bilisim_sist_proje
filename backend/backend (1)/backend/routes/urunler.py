"""Ürün modülü: listeleme, barkodla arama, ekleme, güncelleme, silme."""
from flask import Blueprint, jsonify, request
from pymysql.err import IntegrityError

from db import calistir, get_conn, sorgu
from yetki import aktif_kullanici_id, giris_gerekli, yonetici_gerekli

bp = Blueprint("urunler", __name__)

ALANLAR = ["marka_id", "kategori_id", "urun_adi", "varyant", "barkod", "alis_fiyati",
           "satis_fiyati", "kritik_stok", "tedarik_suresi_gun"]
ZORUNLU = ["marka_id", "urun_adi", "barkod", "alis_fiyati", "satis_fiyati"]

# Ürünü marka ve kategori adlarıyla birlikte getiren ortak sorgu
URUN_SQL = ("SELECT u.*, m.marka_adi, k.kategori_adi FROM urunler u "
            "JOIN markalar m ON m.id = u.marka_id "
            "LEFT JOIN kategoriler k ON k.id = u.kategori_id ")


def butunluk_hatasi(e):
    """MySQL hata koduna göre anlaşılır mesaj üretir."""
    kod = e.args[0] if e.args else None
    if kod == 1062:
        return jsonify({"hata": "Bu barkod zaten kayıtlı"}), 409
    if kod == 1452:
        return jsonify({"hata": "Geçersiz marka_id veya kategori_id"}), 400
    if kod == 1451:
        return jsonify({"hata": "Bu ürünün satış/stok geçmişi var, silinemez"}), 409
    return jsonify({"hata": "Veri bütünlüğü hatası", "detay": str(e)}), 400


@bp.get("")
@giris_gerekli
def listele():
    # İsteğe bağlı filtreler: ?ara=tava  ?kategori_id=2  ?marka_id=1
    kosullar, params = [], []
    if request.args.get("ara"):
        like = f"%{request.args['ara']}%"
        kosullar.append("(u.urun_adi LIKE %s OR m.marka_adi LIKE %s OR u.barkod LIKE %s)")
        params += [like, like, like]
    for alan in ("kategori_id", "marka_id"):
        if request.args.get(alan, type=int):
            kosullar.append(f"u.{alan} = %s")
            params.append(request.args.get(alan, type=int))
    where = ("WHERE " + " AND ".join(kosullar)) if kosullar else ""
    return jsonify(sorgu(URUN_SQL + where + " ORDER BY m.marka_adi, u.urun_adi", params))


@bp.get("/<int:urun_id>")
@giris_gerekli
def getir(urun_id):
    urun = sorgu(URUN_SQL + "WHERE u.id = %s", (urun_id,), tek=True)
    if not urun:
        return jsonify({"hata": "Ürün bulunamadı"}), 404
    return jsonify(urun)


@bp.get("/barkod/<barkod>")
@giris_gerekli
def barkodla_getir(barkod):
    urun = sorgu(URUN_SQL + "WHERE u.barkod = %s", (barkod,), tek=True)
    if not urun:
        return jsonify({"hata": "Bu barkoda ait ürün yok"}), 404
    return jsonify(urun)


@bp.post("")
@yonetici_gerekli
def ekle():
    """Gövde örneği: {"marka_id":1, "kategori_id":2, "urun_adi":"Çelik Tencere", "varyant":"24 cm",
    "barkod":"8690000000001", "alis_fiyati":450, "satis_fiyati":650, "stok_adedi":10}"""
    veri = request.get_json(silent=True) or {}
    eksik = [a for a in ZORUNLU if veri.get(a) in (None, "")]
    if eksik:
        return jsonify({"hata": "Eksik alan", "alanlar": eksik}), 400
    acilis = veri.get("stok_adedi", 0)
    if not isinstance(acilis, int) or acilis < 0:
        return jsonify({"hata": "stok_adedi 0 veya pozitif tam sayı olmalı"}), 400

    alanlar = [a for a in ALANLAR if a in veri]
    conn = get_conn()
    try:
        conn.begin()
        with conn.cursor() as cur:
            cur.execute(f"INSERT INTO urunler ({', '.join(alanlar)}, stok_adedi) "
                        f"VALUES ({', '.join(['%s'] * len(alanlar))}, %s)",
                        [veri[a] for a in alanlar] + [acilis])
            yeni_id = cur.lastrowid
            if acilis > 0:  # açılış stoğu da hareket olarak kayda geçer
                cur.execute("INSERT INTO stok_hareketleri (urun_id, kullanici_id, tip, adet, aciklama) "
                            "VALUES (%s, %s, 'giris', %s, 'Açılış stoğu')",
                            (yeni_id, aktif_kullanici_id(), acilis))
        conn.commit()
    except IntegrityError as e:
        conn.rollback()
        return butunluk_hatasi(e)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify({"mesaj": "Ürün eklendi", "id": yeni_id}), 201


@bp.put("/<int:urun_id>")
@yonetici_gerekli
def guncelle(urun_id):
    veri = request.get_json(silent=True) or {}
    # stok_adedi buradan değişmez; stok sadece stok/satış hareketleriyle değişir
    alanlar = [a for a in ALANLAR if a in veri]
    if not alanlar:
        return jsonify({"hata": "Güncellenecek alan yok"}), 400
    if not sorgu("SELECT id FROM urunler WHERE id=%s", (urun_id,), tek=True):
        return jsonify({"hata": "Ürün bulunamadı"}), 404
    try:
        calistir(f"UPDATE urunler SET {', '.join(a + ' = %s' for a in alanlar)} WHERE id = %s",
                 [veri[a] for a in alanlar] + [urun_id])
    except IntegrityError as e:
        return butunluk_hatasi(e)
    return jsonify({"mesaj": "Ürün güncellendi"})


@bp.delete("/<int:urun_id>")
@yonetici_gerekli
def sil(urun_id):
    try:
        etkilenen, _ = calistir("DELETE FROM urunler WHERE id = %s", (urun_id,))
    except IntegrityError as e:
        return butunluk_hatasi(e)
    if etkilenen == 0:
        return jsonify({"hata": "Ürün bulunamadı"}), 404
    return jsonify({"mesaj": "Ürün silindi"})

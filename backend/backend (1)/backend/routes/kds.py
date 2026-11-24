"""Karar Destek Sistemi (KDS) — sadece yönetici görür. Her endpoint veri + somut ÖNERİ döndürür.
Not: iade satırları satis_detay'da negatif adetle tutulduğu için toplamlar iadeleri otomatik düşer."""
import math

from flask import Blueprint, jsonify, request

from db import sorgu
from yetki import yonetici_gerekli

bp = Blueprint("kds", __name__)

DETAY_JOIN = ("FROM satis_detay d JOIN satislar s ON s.id=d.satis_id "
              "JOIN urunler u ON u.id=d.urun_id JOIN markalar m ON m.id=u.marka_id ")


@bp.get("/ozet")
@yonetici_gerekli
def ozet():
    """Panelin üstündeki kartlar: bugünkü ciro, bu ayki ciro/kâr, kritik stok sayısı."""
    bugun = sorgu("SELECT COALESCE(SUM(d.adet*d.birim_fiyat),0) AS ciro, COUNT(DISTINCT s.id) AS fis "
                  "FROM satislar s JOIN satis_detay d ON d.satis_id=s.id WHERE DATE(s.tarih)=CURDATE()",
                  tek=True)
    ay = sorgu("SELECT COALESCE(SUM(d.adet*d.birim_fiyat),0) AS ciro, "
               "COALESCE(SUM(d.adet*(d.birim_fiyat-d.birim_maliyet)),0) AS kar "
               "FROM satislar s JOIN satis_detay d ON d.satis_id=s.id "
               "WHERE DATE_FORMAT(s.tarih,'%%Y-%%m') = DATE_FORMAT(CURDATE(),'%%Y-%%m')", tek=True)
    kritik = sorgu("SELECT COUNT(*) AS sayi FROM urunler WHERE stok_adedi <= kritik_stok", tek=True)
    return jsonify({"bugun_ciro": bugun["ciro"], "bugun_fis": bugun["fis"],
                    "bu_ay_ciro": ay["ciro"], "bu_ay_kar": ay["kar"], "kritik_stok_sayisi": kritik["sayi"]})


@bp.get("/cok-satanlar")
@yonetici_gerekli
def cok_satanlar():
    # ?gun=30&limit=10
    gun = request.args.get("gun", 30, type=int)
    limit = request.args.get("limit", 10, type=int)
    return jsonify(sorgu(
        "SELECT u.id, m.marka_adi, u.urun_adi, u.varyant, SUM(d.adet) AS satilan_adet, "
        "SUM(d.adet * d.birim_fiyat) AS ciro " + DETAY_JOIN +
        "WHERE s.tarih >= NOW() - INTERVAL %s DAY "
        "GROUP BY u.id HAVING satilan_adet > 0 ORDER BY satilan_adet DESC LIMIT %s", (gun, limit)))


@bp.get("/olu-stok")
@yonetici_gerekli
def olu_stok():
    """Belirli süredir hiç satılmamış ama rafta duran ürünler -> indirim önerisi."""
    gun = request.args.get("gun", 60, type=int)
    sonuc = sorgu(
        "SELECT u.id, m.marka_adi, u.urun_adi, u.varyant, u.stok_adedi, "
        "u.stok_adedi * u.alis_fiyati AS bagli_sermaye, MAX(s.tarih) AS son_satis "
        "FROM urunler u JOIN markalar m ON m.id=u.marka_id "
        "LEFT JOIN satis_detay d ON d.urun_id=u.id AND d.adet > 0 "
        "LEFT JOIN satislar s ON s.id=d.satis_id "
        "WHERE u.stok_adedi > 0 GROUP BY u.id "
        "HAVING son_satis IS NULL OR son_satis < NOW() - INTERVAL %s DAY "
        "ORDER BY bagli_sermaye DESC", (gun,))
    for r in sonuc:
        r["oneri"] = (f"{gun}+ gündür satılmıyor, {r['bagli_sermaye']} TL sermaye bağlı: "
                      "indirim/kampanya veya vitrine taşıma önerilir")
    return jsonify(sonuc)


@bp.get("/siparis-onerisi")
@yonetici_gerekli
def siparis_onerisi():
    """Kural: günlük ort. satış × (ürünün tedarik süresi + güvenlik günü) > stok ise sipariş ver."""
    guvenlik = request.args.get("guvenlik_gun", 3, type=int)
    analiz_gun = 30
    urunler = sorgu(
        "SELECT u.id, m.marka_adi, u.urun_adi, u.varyant, u.stok_adedi, u.tedarik_suresi_gun, "
        "COALESCE(SUM(CASE WHEN s.tarih >= NOW() - INTERVAL %s DAY THEN d.adet END), 0) AS son_satis "
        "FROM urunler u JOIN markalar m ON m.id=u.marka_id "
        "LEFT JOIN satis_detay d ON d.urun_id=u.id LEFT JOIN satislar s ON s.id=d.satis_id "
        "GROUP BY u.id", (analiz_gun,))
    oneriler = []
    for u in urunler:
        gunluk = float(u["son_satis"]) / analiz_gun
        ihtiyac = math.ceil(gunluk * (u["tedarik_suresi_gun"] + guvenlik))
        if gunluk > 0 and u["stok_adedi"] < ihtiyac:
            kac_gun = round(u["stok_adedi"] / gunluk, 1)
            oneriler.append({
                **u,
                "gunluk_ortalama": round(gunluk, 2),
                "kac_gun_yeter": kac_gun,
                "onerilen_siparis": ihtiyac - u["stok_adedi"],
                "aciliyet": "ACİL" if kac_gun <= u["tedarik_suresi_gun"] else "Yakında",
                "oneri": (f"Stok {kac_gun} günde biter, tedarik {u['tedarik_suresi_gun']} gün sürüyor: "
                          f"{ihtiyac - u['stok_adedi']} adet sipariş verin"),
            })
    oneriler.sort(key=lambda x: x["kac_gun_yeter"])  # en acil olan en üstte
    return jsonify(oneriler)


@bp.get("/kar-analizi")
@yonetici_gerekli
def kar_analizi():
    # ?grup=marka  veya  ?grup=kategori
    if request.args.get("grup") == "kategori":
        grup_sql, ek_join = "COALESCE(k.kategori_adi, 'Kategorisiz')", "LEFT JOIN kategoriler k ON k.id=u.kategori_id "
    else:
        grup_sql, ek_join = "m.marka_adi", ""
    gun = request.args.get("gun", 90, type=int)
    return jsonify(sorgu(
        f"SELECT {grup_sql} AS grup, SUM(d.adet) AS adet, SUM(d.adet*d.birim_fiyat) AS ciro, "
        "SUM(d.adet*(d.birim_fiyat-d.birim_maliyet)) AS kar, "
        "ROUND(100*SUM(d.adet*(d.birim_fiyat-d.birim_maliyet))/NULLIF(SUM(d.adet*d.birim_fiyat),0),1) "
        "AS kar_marji_yuzde " + DETAY_JOIN + ek_join +
        f"WHERE s.tarih >= NOW() - INTERVAL %s DAY GROUP BY grup ORDER BY kar DESC", (gun,)))


@bp.get("/abc-analizi")
@yonetici_gerekli
def abc_analizi():
    """Cironun ~%80'ini getirenler A, sonraki ~%15 B, kalanı C."""
    gun = request.args.get("gun", 90, type=int)
    satirlar = sorgu(
        "SELECT u.id, m.marka_adi, u.urun_adi, u.varyant, SUM(d.adet*d.birim_fiyat) AS ciro " + DETAY_JOIN +
        "WHERE s.tarih >= NOW() - INTERVAL %s DAY GROUP BY u.id HAVING ciro > 0 ORDER BY ciro DESC", (gun,))
    toplam = sum(float(r["ciro"]) for r in satirlar) or 1
    kumulatif = 0.0
    for r in satirlar:
        kumulatif += float(r["ciro"])
        oran = kumulatif / toplam
        r["sinif"] = "A" if oran <= 0.80 else "B" if oran <= 0.95 else "C"
        r["kumulatif_yuzde"] = round(oran * 100, 1)
    return jsonify(satirlar)


@bp.get("/aylik-ciro")
@yonetici_gerekli
def aylik_ciro():
    return jsonify(sorgu(
        "SELECT DATE_FORMAT(s.tarih, '%%Y-%%m') AS ay, COUNT(DISTINCT s.id) AS satis_sayisi, "
        "SUM(d.adet*d.birim_fiyat) AS ciro, SUM(d.adet*(d.birim_fiyat-d.birim_maliyet)) AS kar "
        "FROM satislar s JOIN satis_detay d ON d.satis_id=s.id "
        "GROUP BY ay ORDER BY ay"))


@bp.get("/odeme-dagilimi")
@yonetici_gerekli
def odeme_dagilimi():
    gun = request.args.get("gun", 30, type=int)
    return jsonify(sorgu(
        "SELECT odeme_tipi, COUNT(*) AS fis_sayisi, SUM(toplam_tutar) AS tutar "
        "FROM satislar WHERE tarih >= NOW() - INTERVAL %s DAY GROUP BY odeme_tipi", (gun,)))


@bp.get("/calisan-performansi")
@yonetici_gerekli
def calisan_performansi():
    gun = request.args.get("gun", 30, type=int)
    return jsonify(sorgu(
        "SELECT k.ad_soyad, COUNT(DISTINCT s.id) AS fis_sayisi, SUM(d.adet*d.birim_fiyat) AS ciro "
        "FROM satislar s JOIN satis_detay d ON d.satis_id=s.id JOIN kullanicilar k ON k.id=s.kullanici_id "
        "WHERE s.tarih >= NOW() - INTERVAL %s DAY GROUP BY k.id ORDER BY ciro DESC", (gun,)))

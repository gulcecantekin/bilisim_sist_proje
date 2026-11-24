# Züccaciye KDS – Backend (Flask)

## Kurulum
```bash
pip install -r requirements.txt
```
1. `.env.example` dosyasını kopyalayıp adını `.env` yapın; MySQL şifrenizi ve bir SECRET_KEY yazın.
2. MySQL Workbench'te `schema_onerisi.sql` dosyasını açıp çalıştırın (⚡).
   **Dikkat:** dosya `zuccaciye` veritabanını silip baştan kurar.
3. `python app.py` → http://localhost:5000/api/saglik adresinde `{"durum": "calisiyor"}` görmelisiniz.

## Başlangıç kullanıcıları
| Kullanıcı adı | Şifre | Rol |
|---|---|---|
| yonetici | yonetici123 | yonetici |
| calisan | calisan123 | calisan |

Canlıya almadan önce şifreleri değiştirin (`POST /api/auth/sifre-degistir`).

## Postman'de giriş
Önce `POST /api/auth/giris` isteğini `{"kullanici_adi":"yonetici","sifre":"yonetici123"}` gövdesiyle gönderin.
Postman oturum çerezini kendisi saklar; sonraki istekler giriş yapılmış sayılır.
Rol değiştirmek için `POST /api/auth/cikis` yapıp diğer kullanıcıyla girin.

## Yetkiler
| İşlem | Çalışan | Yönetici |
|---|---|---|
| Ürün/kategori/marka görüntüleme, barkodla arama | ✅ | ✅ |
| Satış yapma, iade alma, mal kabul (stok girişi), kritik stok | ✅ | ✅ |
| Satış listesi | Sadece kendi satışları | Hepsi |
| Ürün/kategori/marka ekleme-güncelleme-silme | ❌ | ✅ |
| Sayım düzeltmesi, stok hareket geçmişi | ❌ | ✅ |
| KDS paneli, kullanıcı yönetimi | ❌ | ✅ |

## Endpoint'ler
| Metot | Adres | Açıklama |
|---|---|---|
| POST | /api/auth/giris | `{"kullanici_adi","sifre"}` |
| POST | /api/auth/cikis | Çıkış |
| GET | /api/auth/ben | Giriş yapan kişi ve rolü |
| POST | /api/auth/sifre-degistir | `{"eski_sifre","yeni_sifre"}` |
| GET / POST | /api/kullanicilar | Kullanıcı listesi / ekle `{"ad_soyad","kullanici_adi","sifre","rol"}` |
| PUT | /api/kullanicilar/{id}/aktiflik | `{"aktif": false}` |
| PUT | /api/kullanicilar/{id}/sifre | `{"yeni_sifre"}` |
| GET / POST | /api/kategoriler | Liste / ekle `{"kategori_adi"}` |
| PUT / DELETE | /api/kategoriler/{id} | Güncelle / sil |
| GET / POST | /api/markalar | Liste / ekle `{"marka_adi"}` |
| PUT / DELETE | /api/markalar/{id} | Güncelle / sil |
| GET | /api/urunler?ara=&kategori_id=&marka_id= | Ürün listesi / arama |
| GET | /api/urunler/{id} | Tek ürün |
| GET | /api/urunler/barkod/{barkod} | Barkodla ürün (kasa ekranı) |
| POST | /api/urunler | Ürün ekle (marka_id, urun_adi, barkod, alis_fiyati, satis_fiyati zorunlu) |
| PUT | /api/urunler/{id} | Ürün güncelle (stok hariç) |
| DELETE | /api/urunler/{id} | Ürün sil |
| POST | /api/stok/giris | Mal kabul `{"barkod","adet","aciklama"}` |
| POST | /api/stok/duzeltme | Sayım `{"barkod","sayilan_adet","aciklama"}` |
| GET | /api/stok/kritik | Kritik seviyedeki ürünler |
| GET | /api/stok/hareketler?urun_id= | Stok hareket geçmişi |
| POST | /api/satis | Satış `{"sepet":[{"barkod","adet"}],"odeme_tipi":"nakit"}` |
| POST | /api/satis/{id}/iade | İade `{"barkod","adet"}` |
| GET | /api/satis?baslangic=&bitis= | Satış listesi |
| GET | /api/satis/{id} | Fiş detayı |
| GET | /api/kds/ozet | Bugünkü/aylık ciro, kâr, kritik stok sayısı |
| GET | /api/kds/cok-satanlar?gun=30 | En çok satanlar |
| GET | /api/kds/olu-stok?gun=60 | Satılmayan ürünler + indirim önerisi |
| GET | /api/kds/siparis-onerisi | Ürünün tedarik süresine göre sipariş önerisi |
| GET | /api/kds/kar-analizi?grup=marka | Marka/kategori kâr marjı |
| GET | /api/kds/abc-analizi | Ürünlerin A/B/C sınıfı |
| GET | /api/kds/aylik-ciro | Aylık ciro ve kâr |
| GET | /api/kds/odeme-dagilimi | Nakit/kart dağılımı |
| GET | /api/kds/calisan-performansi | Çalışan bazında satış |

## Frontend
Frontend dosyaları reponun `frontend/` klasörüne konur; Flask onları da sunar.
`frontend/index.html` varsa http://localhost:5000 adresinde açılır. JS'te istekler `/api/...` diye atılır
(başına adres yazmaya gerek yok).

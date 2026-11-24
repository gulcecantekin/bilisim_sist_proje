-- Züccaciye KDS veritabanı (7 tablo)
-- Adlandırma: küçük harf, Türkçe karakter yok, tablolar çoğul, yabancı anahtarlar tabloadi_id.

DROP DATABASE IF EXISTS zuccaciye;
CREATE DATABASE zuccaciye CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
USE zuccaciye;

-- Sisteme giriş yapan kişiler
CREATE TABLE kullanicilar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ad_soyad VARCHAR(100) NOT NULL,
    kullanici_adi VARCHAR(50) NOT NULL UNIQUE,
    sifre_hash VARCHAR(255) NOT NULL,          -- şifre asla düz metin tutulmaz
    rol ENUM('yonetici', 'calisan') NOT NULL DEFAULT 'calisan',
    aktif TINYINT(1) NOT NULL DEFAULT 1,       -- işten ayrılan silinmez, pasif yapılır
    olusturma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE kategoriler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kategori_adi VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE markalar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    marka_adi VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE urunler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    marka_id INT NOT NULL,
    kategori_id INT,
    urun_adi VARCHAR(200) NOT NULL,
    varyant VARCHAR(100),                      -- renk, ebat, adet vb.
    barkod VARCHAR(20) NOT NULL UNIQUE,
    alis_fiyati DECIMAL(10,2) NOT NULL,
    satis_fiyati DECIMAL(10,2) NOT NULL,
    stok_adedi INT NOT NULL DEFAULT 0,
    kritik_stok INT NOT NULL DEFAULT 5,
    tedarik_suresi_gun INT NOT NULL DEFAULT 7, -- sipariş verilince kaç günde geliyor
    olusturma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (marka_id) REFERENCES markalar(id),
    FOREIGN KEY (kategori_id) REFERENCES kategoriler(id),
    CHECK (alis_fiyati >= 0 AND satis_fiyati >= 0),
    CHECK (stok_adedi >= 0)
);

-- Her kasa işlemi (fiş)
CREATE TABLE satislar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
    kullanici_id INT NOT NULL,                 -- satışı yapan kişi
    odeme_tipi ENUM('nakit', 'kart') NOT NULL DEFAULT 'nakit',
    toplam_tutar DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id),
    INDEX (tarih)
);

-- ARA TABLO: satışlar <-> ürünler (çoka-çok ilişki)
CREATE TABLE satis_detay (
    id INT AUTO_INCREMENT PRIMARY KEY,
    satis_id INT NOT NULL,
    urun_id INT NOT NULL,
    adet INT NOT NULL,                         -- iade satırlarında negatif
    birim_fiyat DECIMAL(10,2) NOT NULL,        -- satış anındaki fiyat
    birim_maliyet DECIMAL(10,2) NOT NULL,      -- satış anındaki alış fiyatı (kâr hesabı için)
    FOREIGN KEY (satis_id) REFERENCES satislar(id),
    FOREIGN KEY (urun_id) REFERENCES urunler(id)
);

-- Stoğa her giriş/çıkışın kaydı
CREATE TABLE stok_hareketleri (
    id INT AUTO_INCREMENT PRIMARY KEY,
    urun_id INT NOT NULL,
    kullanici_id INT,
    tip ENUM('giris', 'satis', 'iade', 'duzeltme') NOT NULL,
    adet INT NOT NULL,                         -- stoğa giren pozitif, çıkan negatif
    tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
    aciklama VARCHAR(255),
    FOREIGN KEY (urun_id) REFERENCES urunler(id),
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id)
);

-- Başlangıç kullanıcıları. Şifreler: yonetici123 / calisan123
-- Sunumdan / canlıya almadan önce şifreleri değiştirin!
INSERT INTO kullanicilar (ad_soyad, kullanici_adi, sifre_hash, rol) VALUES
('Dükkan Sahibi', 'yonetici', 'pbkdf2:sha256:1000000$glm3CNLSq0ij8Z9i$28e5212ceb6b0cde6216e5e59707147a1af2caa539eceacb42ffb89c95884700', 'yonetici'),
('Kasa Çalışanı', 'calisan', 'pbkdf2:sha256:1000000$Tj39nsWqSoc3Uhvd$038fc3fda4fe559015cc1b463b478ceb016da6153d617628c17954fa169af7cb', 'calisan');

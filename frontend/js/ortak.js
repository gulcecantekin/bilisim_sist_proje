// Tüm sayfaların kullandığı ortak fonksiyonlar.
// Her HTML sayfasında Bootstrap'ten SONRA şu satırla eklenir:
//   <script src="/js/ortak.js"></script>

// ---- Backend'e istek atan yardımcı ----
// Örnek: const urunler = await api("/api/urunler");
//        await api("/api/urunler", "POST", { urun_adi: "Çay bardağı", ... });
async function api(adres, metot = "GET", govde = null) {
    const ayar = { method: metot, headers: {}, credentials: "same-origin" };
    if (govde !== null) {
        ayar.headers["Content-Type"] = "application/json";
        ayar.body = JSON.stringify(govde);
    }
    const cevap = await fetch(adres, ayar);
    const veri = await cevap.json().catch(() => ({}));

    if (cevap.status === 401 && !location.pathname.endsWith("index.html") && location.pathname !== "/") {
        location.href = "/index.html";          // oturum yoksa giriş sayfasına at
        throw new Error("Giriş gerekli");
    }
    if (!cevap.ok) throw new Error(veri.hata || "Bir hata oluştu");
    return veri;
}

// ---- Ekranın üstünde renkli mesaj göster ----
// tur: "success" | "danger" | "warning" | "info"
function mesajGoster(metin, tur = "info") {
    const kutu = document.getElementById("mesajlar");
    if (!kutu) return alert(metin);
    kutu.insertAdjacentHTML("beforeend",
        `<div class="alert alert-${tur} alert-dismissible fade show">${metin}
         <button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>`);
}

// ---- Para formatı: 1234.5 -> "1.234,50 ₺" ----
function tl(sayi) {
    return Number(sayi || 0).toLocaleString("tr-TR", { style: "currency", currency: "TRY" });
}

// ---- Giriş kontrolü + üst menü ----
// Giriş gerektiren her sayfanın başında çağrılır:  const ben = await sayfaHazirla();
// sadeceYonetici=true verilirse çalışan bu sayfayı açamaz.
async function sayfaHazirla(sadeceYonetici = false) {
    const ben = await api("/api/auth/ben");   // giriş yoksa api() zaten giriş sayfasına atar
    if (sadeceYonetici && ben.rol !== "yonetici") {
        location.href = "/panel.html";
        throw new Error("Yetki yok");
    }
    menuCiz(ben);
    return ben;
}

function menuCiz(ben) {
    const yonetici = ben.rol === "yonetici";
    const link = (adres, ikon, yazi) => {
        const aktif = location.pathname.endsWith(adres) ? "active" : "";
        return `<li class="nav-item"><a class="nav-link ${aktif}" href="${adres}"><i class="bi bi-${ikon}"></i> ${yazi}</a></li>`;
    };

    document.getElementById("menu").innerHTML = `
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container-fluid">
        <a class="navbar-brand" href="/panel.html"><i class="bi bi-shop"></i> Züccaciye</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#menuIcerik">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="menuIcerik">
          <ul class="navbar-nav me-auto">
            ${link("/satis.html", "upc-scan", "Satış")}
            ${link("/urunler.html", "box-seam", "Ürünler")}
            ${link("/stok.html", "boxes", "Stok")}
            ${yonetici ? link("/kds.html", "graph-up", "Raporlar (KDS)") : ""}
            ${yonetici ? link("/kullanicilar.html", "people", "Kullanıcılar") : ""}
          </ul>
          <span class="navbar-text me-3">
            <i class="bi bi-person-circle"></i> ${ben.ad_soyad}
            <span class="badge bg-secondary">${yonetici ? "Yönetici" : "Çalışan"}</span>
          </span>
          <button class="btn btn-outline-light btn-sm" onclick="cikisYap()">
            <i class="bi bi-box-arrow-right"></i> Çıkış
          </button>
        </div>
      </div>
    </nav>`;
}

async function cikisYap() {
    await api("/api/auth/cikis", "POST");
    location.href = "/index.html";
}

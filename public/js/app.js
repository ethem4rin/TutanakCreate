/* =========================================================================
   Müfettiş Programı — arayüz mantığı
   1. Tutanak yüklenir ve çözümlenir.
   2. Her noksanlık için dayanak (mevzuat maddesi) ve müfettiş önerisi seçilir.
   3. Yazı künyesi doldurulur ve Word belgesi üretilir.
   ========================================================================= */
"use strict";

const SAKLAMA_ANAHTARI = "mufettis-programi-durum-v2";
const EKSTRA_MADDELER_ANAHTARI = "mufettis-ekstra-maddeler-v1";
const EKSTRA_MEVZUATLAR_ANAHTARI = "mufettis-ekstra-mevzuatlar-v1";

/** Sunucusuz kurulumda (Vercel) kütüphane salt okunurdur. */
let yerelKurulum = true;

const durum = {
  kunye: null,
  dosyaAdi: "",
  paragraflar: [],
  secili: [],
  noksanliklar: [],
  belge: {
    sayi: "", tarih: "", eposta: "", bildirimTarihi: "", bildirimSaati: "",
    tebAd: "", tebBaba: "", tebDogum: "", tebTckn: "", tebGorev: "", tebTarih: "",
  },
  tumunuGoster: false,
};

/* ------------------------------------------------------------- yardımcılar */

const $ = (secici) => document.querySelector(secici);
const $$ = (secici) => Array.from(document.querySelectorAll(secici));

const kacis = (metin) =>
  String(metin ?? "").replace(/[&<>"']/g, (k) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[k]));

const kucult = (metin) => String(metin ?? "").toLocaleLowerCase("tr");

function bildir(mesaj, tur = "bilgi") {
  const yuva = $("#bildirim-yuvasi");
  const kutu = document.createElement("div");
  kutu.className = `bildirim ${tur}`;
  kutu.textContent = mesaj;
  yuva.appendChild(kutu);
  setTimeout(() => {
    kutu.style.opacity = "0";
    kutu.style.transition = "opacity .25s";
    setTimeout(() => kutu.remove(), 260);
  }, 4200);
}

async function istek(yol, secenekler = {}) {
  const yanit = await fetch(yol, secenekler);
  const tip = yanit.headers.get("content-type") || "";
  if (!yanit.ok) {
    let mesaj = `Sunucu hatası (${yanit.status})`;
    if (tip.includes("application/json")) {
      const govde = await yanit.json().catch(() => ({}));
      mesaj = govde.hata || mesaj;
    }
    throw new Error(mesaj);
  }
  return tip.includes("application/json") ? yanit.json() : yanit.blob();
}

/** İşaretli metni (``**kalın**`` / ``__altı çizili__``) HTML'e çevirir. */
function isaretliHtml(metin) {
  return kacis(metin)
    .replace(/\*\*(.+?)\*\*/gs, "<strong>$1</strong>")
    .replace(/__(.+?)__/gs, "<u><em><strong>$1</strong></em></u>")
    .replace(/\n/g, "<br>");
}

const yeniKimlik = () => "n" + Math.random().toString(36).slice(2, 9);

/** "4857 - İş Kanunu m.63 — Çalışma Süresi" */
const maddeAdi = (m) =>
  `${m.mevzuat_ad} m.${m.no}${m.baslik ? " — " + m.baslik : ""}`;

function kipKapat(secici) { $(secici).classList.remove("acik"); }
function kipAc(secici) { $(secici).classList.add("acik"); }

/* ------------------------------------------------------------- kalıcılık */

function durumuKaydet() {
  try {
    localStorage.setItem(SAKLAMA_ANAHTARI, JSON.stringify(durum));
  } catch (hata) {
    /* kota dolu olabilir; kritik değil */
  }
}

function durumuYukle() {
  try {
    const ham = localStorage.getItem(SAKLAMA_ANAHTARI);
    if (!ham) return false;
    Object.assign(durum, JSON.parse(ham));
    return Boolean(durum.kunye);
  } catch (hata) {
    return false;
  }
}

/* ---------------------------------------------------------------- sayfalar */

function sayfaAc(ad) {
  $$(".sayfa").forEach((s) => s.classList.toggle("etkin", s.id === `sayfa-${ad}`));
  $$(".menu-dugme[data-sayfa]").forEach((d) =>
    d.classList.toggle("etkin", d.dataset.sayfa === ad));
  $$(".adim[data-sayfa]").forEach((d) =>
    d.classList.toggle("etkin", d.dataset.sayfa === ad));
  if (ad === "kutuphane") kutuphaneAc();
  if (ad === "belge") belgeOzetiCiz();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ====================================================================== */
/* 1. AŞAMA — TUTANAK                                                      */
/* ====================================================================== */

function kunyeyiFormaYaz() {
  if (!durum.kunye) return;
  const k = durum.kunye;
  $("#k-unvan").value = k.unvan || "";
  $("#k-adres").value = k.adres || "";
  $("#k-sicil").value = k.sgk_sicil_no || k.sicil_no || "";
  $("#k-giris").value = k.giris_metni || "";
  $("#k-mufettis1").value = (k.mufettisler || [])[0] || "";
  $("#k-mufettis2").value = (k.mufettisler || [])[1] || "";
  $("#k-vekil").value = [k.vekil_adi, k.vekil_gorevi].filter(Boolean).join(" — ");
  $("#kaynak-dosya").textContent = durum.dosyaAdi || "";
  $("#ust-alt-yazi").textContent = k.unvan
    ? `${k.unvan} · ${k.teftis_tarihleri || ""}`.trim()
    : "Noksanlık / Aykırılık Bildirimi hazırlama";
}

function kunyeyiFormdanOku() {
  if (!durum.kunye) return;
  durum.kunye.unvan = $("#k-unvan").value.trim();
  durum.kunye.adres = $("#k-adres").value.trim();
  durum.kunye.sgk_sicil_no = $("#k-sicil").value.trim();
  durum.kunye.giris_metni = $("#k-giris").value.trim();
  durum.kunye.mufettisler = [$("#k-mufettis1").value.trim(), $("#k-mufettis2").value.trim()];
  durumuKaydet();
}

function paragraflariCiz() {
  const yuva = $("#paragraf-listesi");
  const gosterilecek = durum.tumunuGoster
    ? durum.paragraflar
    : durum.paragraflar.filter((p) => p.aday || durum.secili.includes(p.sira));

  if (!gosterilecek.length) {
    yuva.innerHTML = `<div class="bos-durum">
      <svg><use href="#s-liste"/></svg>
      <div>Tutanakta kalın yazılmış noksanlık bulunamadı.</div>
      <div style="font-size:12px;margin-top:6px">“Tüm paragrafları göster” ile elle seçebilirsiniz.</div>
    </div>`;
  } else {
    yuva.innerHTML = gosterilecek
      .map((p) => {
        const secili = durum.secili.includes(p.sira);
        const rozetler = [];
        if (p.aday) rozetler.push('<span class="etiket aday">kalın · aday</span>');
        if (p.baslik_mi) rozetler.push('<span class="etiket">bölüm başlığı</span>');
        return `<div class="paragraf-satiri ${secili ? "secili" : ""}" data-sira="${p.sira}">
            <div class="kutucuk"><svg><use href="#s-onay"/></svg></div>
            <div style="flex:1 1 auto;min-width:0">
              <div style="display:flex;gap:7px;margin-bottom:5px;flex-wrap:wrap">${rozetler.join("")}</div>
              <div class="govde-metin">${p.html}</div>
            </div>
          </div>`;
      })
      .join("");
  }

  $("#secim-sayisi").textContent = `${durum.secili.length} noksanlık seçili`;
  $("#tumunu-goster").textContent = durum.tumunuGoster
    ? "Yalnızca adayları göster"
    : "Tüm paragrafları göster";

  yuva.querySelectorAll(".paragraf-satiri").forEach((satir) => {
    satir.addEventListener("click", () => {
      const sira = Number(satir.dataset.sira);
      const yeri = durum.secili.indexOf(sira);
      if (yeri >= 0) durum.secili.splice(yeri, 1);
      else durum.secili.push(sira);
      durum.secili.sort((a, b) => a - b);
      durumuKaydet();
      paragraflariCiz();
    });
  });
}

async function tutanagiYukle(dosya) {
  if (!dosya) return;
  if (!dosya.name.toLowerCase().endsWith(".docx")) {
    bildir("Yalnızca .docx uzantılı Word dosyaları yüklenebilir.", "hata");
    return;
  }
  const alan = $("#birak-alani");
  const eskiHtml = alan.innerHTML;
  alan.innerHTML = `<div class="yukleniyor"></div>
    <div class="baslik" style="margin-top:12px">Tutanak çözümleniyor…</div>`;

  try {
    const govde = new FormData();
    govde.append("dosya", dosya);
    const veri = await istek("/api/tutanak", { method: "POST", body: govde });

    durum.kunye = veri.kunye;
    durum.paragraflar = veri.paragraflar;
    durum.dosyaAdi = veri.dosya_adi;
    durum.secili = veri.paragraflar.filter((p) => p.aday).map((p) => p.sira);
    durum.noksanliklar = [];
    durum.belge.tebAd = veri.kunye.vekil_adi || "";
    durum.belge.tebGorev = veri.kunye.vekil_gorevi || "";
    durum.belge.tarih = veri.kunye.tutanak_tarihi || "";
    durum.belge.tebTarih = veri.kunye.tutanak_tarihi || "";
    durumuKaydet();

    alan.innerHTML = eskiHtml;
    dosyaGirdisiniBagla();
    $("#tutanak-sonuc").classList.remove("gizli");
    kunyeyiFormaYaz();
    paragraflariCiz();
    belgeFormunuYaz();
    bildir(`Tutanak okundu · ${durum.secili.length} noksanlık adayı bulundu.`, "basarili");
  } catch (hata) {
    alan.innerHTML = eskiHtml;
    dosyaGirdisiniBagla();
    bildir(hata.message, "hata");
  }
}

function dosyaGirdisiniBagla() {
  const alan = $("#birak-alani");
  const girdi = $("#dosya-girdisi");
  if (!girdi) return;
  alan.onclick = () => girdi.click();
  girdi.onchange = () => tutanagiYukle(girdi.files[0]);
}

/* ====================================================================== */
/* MEVZUAT AĞACI — Mevzuat Türü → Mevzuat → Madde                          */
/* ====================================================================== */

/* --- localStorage'daki ekstra maddeler (Vercel salt-okunur ortam fallback) --- */

function ekstraMaddeleriYukle() {
  try { return JSON.parse(localStorage.getItem(EKSTRA_MADDELER_ANAHTARI) || "[]"); }
  catch { return []; }
}

function ekstraMaddeleriKaydet(liste) {
  try { localStorage.setItem(EKSTRA_MADDELER_ANAHTARI, JSON.stringify(liste)); } catch { /* kota dolu */ }
}

function ekstraMevzuatlariYukle() {
  try { return JSON.parse(localStorage.getItem(EKSTRA_MEVZUATLAR_ANAHTARI) || "[]"); }
  catch { return []; }
}

function ekstraMevzuatlariKaydet(liste) {
  try { localStorage.setItem(EKSTRA_MEVZUATLAR_ANAHTARI, JSON.stringify(liste)); } catch { /* kota dolu */ }
}

/**
 * Mevzuat ağacına localStorage'daki ekstra mevzuatları merge eder.
 */
function ekstraMevzuatlariMergeEt(agac) {
  const liste = ekstraMevzuatlariYukle();
  if (!liste.length) return;
  liste.forEach((em) => {
    const tur = agac.find((t) => t.id === em.tur_id);
    if (!tur) return;
    const mevcut = tur.mevzuat.find((m) => m.id === em.id);
    if (!mevcut) {
      tur.mevzuat.push({
        id: em.id,
        ad: em.ad,
        atif: em.atif,
        maddeler: []
      });
    }
  });
}

/**
 * Mevzuat ağacına localStorage'daki ekstra maddeleri merge eder.
 * Aynı no'ya sahip madde varsa üzerine yazar (düzenleme), yoksa ekler.
 */
function ekstraMaddeleriMergeEt(agac) {
  const liste = ekstraMaddeleriYukle();
  if (!liste.length) return;
  liste.forEach((em) => {
    const tur = agac.find((t) => t.id === em.tur_id);
    if (!tur) return;
    const mevzuat = tur.mevzuat.find((m) => m.id === em.mevzuat_id);
    if (!mevzuat) return;
    if (em._silindi) {
      mevzuat.maddeler = mevzuat.maddeler.filter((m) => m.no !== em.no);
      return;
    }
    const mevcutIdx = mevzuat.maddeler.findIndex((m) => m.no === em.no);
    const madde = {
      kimlik: `${em.mevzuat_id}-${em.no}`,
      no: em.no, baslik: em.baslik, ceza: em.ceza,
      anahtar: Array.isArray(em.anahtar) ? em.anahtar
        : String(em.anahtar || "").split(",").map((s) => s.trim()).filter(Boolean),
      paragraf: em.paragraf, html: em.html || em.paragraf,
      mevzuat_id: em.mevzuat_id, mevzuat_ad: mevzuat.ad,
      tur_id: em.tur_id,
    };
    if (mevcutIdx >= 0) mevzuat.maddeler[mevcutIdx] = madde;
    else mevzuat.maddeler.push(madde);
  });
}

let mevzuatAgaci = null;

async function mevzuatAgaciniYukle(zorla = false) {
  if (!mevzuatAgaci || zorla) {
    mevzuatAgaci = await istek("/api/mevzuat");
    ekstraMevzuatlariMergeEt(mevzuatAgaci);
    ekstraMaddeleriMergeEt(mevzuatAgaci);
  }
  return mevzuatAgaci;
}

function turBul(turId) {
  return (mevzuatAgaci || []).find((t) => t.id === turId) || null;
}

function mevzuatBul(turId, mevzuatId) {
  const tur = turBul(turId);
  return tur ? tur.mevzuat.find((m) => m.id === mevzuatId) || null : null;
}

/** Ağaçtaki tüm maddeleri, ait oldukları mevzuat bilgisiyle birlikte düzleştirir. */
function tumMaddeler() {
  const duz = [];
  (mevzuatAgaci || []).forEach((tur) =>
    tur.mevzuat.forEach((mevzuat) =>
      mevzuat.maddeler.forEach((madde) =>
        duz.push({
          ...madde,
          tur_id: tur.id, tur_ad: tur.ad,
          mevzuat_id: mevzuat.id, mevzuat_ad: mevzuat.ad, atif: mevzuat.atif,
        })
      )
    )
  );
  return duz;
}

function maddeBulKimlikle(kimlik) {
  return tumMaddeler().find((m) => m.kimlik === kimlik) || null;
}

/**
 * Kademeli seçiciyi çizer.
 *
 * gorunum: { turId, mevzuatId, maddeKimlik, arama, onerilenler, secilenler:Set }
 * ayar   : { yuva, onDegisim(gorunum), onMadde(madde), oneriSutunu }
 */
function sutunlariCiz(ayar, gorunum) {
  const yuva = $(ayar.yuva);
  const arama = kucult(gorunum.arama || "").trim();
  const onerilenler = gorunum.onerilenler || [];

  /* --- 1. sütun: mevzuat türü --- */
  const turSatirlari = [];
  if (ayar.oneriSutunu && onerilenler.length) {
    turSatirlari.push(
      `<button class="kademe ${gorunum.turId === "__oneri__" ? "etkin" : ""}" data-tur="__oneri__">
         <span class="ad">Önerilenler</span>
         <span class="sag">${onerilenler.length}</span>
       </button>`
    );
  }
  (mevzuatAgaci || []).forEach((tur) => {
    turSatirlari.push(
      `<button class="kademe ${gorunum.turId === tur.id ? "etkin" : ""}" data-tur="${tur.id}">
         <span class="ad">${kacis(tur.ad)}</span>
         <span class="sag">${tur.mevzuat_sayisi} ›</span>
       </button>`
    );
  });

  /* --- 2. sütun: mevzuat --- */
  let mevzuatSatirlari;
  if (arama) {
    mevzuatSatirlari = `<div class="sutun-bos">Arama sonuçları sağda listelendi.</div>`;
  } else if (gorunum.turId === "__oneri__") {
    mevzuatSatirlari =
      `<div class="sutun-bos">Noksanlık metnine göre önerilen maddeler sağda.</div>`;
  } else {
    const tur = turBul(gorunum.turId);
    if (!tur) {
      mevzuatSatirlari = `<div class="sutun-bos">Soldan bir mevzuat türü seçin.</div>`;
    } else if (!tur.mevzuat.length) {
      mevzuatSatirlari = `<div class="sutun-bos">Bu türde kayıtlı mevzuat yok.</div>`;
    } else {
      mevzuatSatirlari = tur.mevzuat
        .map(
          (m) => `<button class="kademe ${gorunum.mevzuatId === m.id ? "etkin" : ""}"
                          data-mevzuat="${m.id}">
              <span class="ad">${kacis(m.ad)}</span>
              <span class="sag">${m.dolu_sayisi}/${m.madde_sayisi} ›</span>
            </button>`
        )
        .join("");
    }
  }

  /* --- 3. sütun: madde --- */
  let maddeler = [];
  let maddeBasligi = "Madde";
  if (arama) {
    maddeBasligi = "Arama Sonucu";
    maddeler = tumMaddeler().filter((m) =>
      kucult(
        [m.mevzuat_ad, m.no, m.baslik, m.paragraf, (m.anahtar || []).join(" ")].join(" ")
      ).includes(arama)
    ).slice(0, 80);
  } else if (gorunum.turId === "__oneri__") {
    maddeBasligi = "Önerilen Madde";
    maddeler = onerilenler;
  } else if (gorunum.mevzuatId) {
    const mevzuat = mevzuatBul(gorunum.turId, gorunum.mevzuatId);
    maddeler = mevzuat ? mevzuat.maddeler.map((m) => ({
      ...m, tur_id: gorunum.turId, mevzuat_id: mevzuat.id,
      mevzuat_ad: mevzuat.ad, atif: mevzuat.atif,
    })) : [];
  }

  let maddeSatirlari;
  if (!maddeler.length) {
    maddeSatirlari = `<div class="sutun-bos">${
      arama ? "Eşleşen madde yok." : "Ortadan bir mevzuat seçin."
    }</div>`;
  } else {
    maddeSatirlari = maddeler
      .map((m) => {
        const secili = gorunum.secilenler && gorunum.secilenler.has(m.kimlik);
        const acik = gorunum.acikMadde === m.kimlik;
        const sagParcalar = [];
        if (m.puan) sagParcalar.push("ilgili");
        if (m.ceza) sagParcalar.push(`ceza ${kacis(m.ceza)}`);
        // Fıkra bazlı kayıtlarda fıkra sınırı PDF düzeninden çıkarılır;
        // müfettiş eklemeden önce metni görsün diye işaretlenir.
        if (m.dolu && !m.dogrulandi) sagParcalar.push("fıkra");
        if (!m.dolu) sagParcalar.push("metin yok");

        const govde = m.dolu
          ? (m.html || isaretliHtml(m.paragraf))
          : `<span class="bos-metin">Bu maddenin metni henüz girilmedi.</span>`;
        const eylemler = (ayar.eylemler ? ayar.eylemler(m) : [])
          .map((e, i) => `<button class="dugme kucuk ${e.ana ? "ana" : ""}"
                                  data-eylem="${m.kimlik}" data-eylem-no="${i}">
                            ${kacis(e.etiket)}
                          </button>`)
          .join("");

        return `<div class="madde-ogesi">
            <button class="kademe ${acik ? "etkin" : ""} ${secili ? "secili" : ""}
                            ${m.dolu ? "" : "bos"}" data-madde="${m.kimlik}">
              <span class="madde-no">${kacis(m.no)}</span>
              <span class="ad">${kacis(m.baslik || (arama || gorunum.turId === "__oneri__" ? m.mevzuat_ad : "—"))}
                ${(arama || gorunum.turId === "__oneri__") && m.baslik
                  ? `<br><span style="font-size:11px;color:var(--metin-sonuk)">${kacis(m.mevzuat_ad)}</span>`
                  : ""}
              </span>
              <span class="sag">${sagParcalar.join(" · ")}</span>
            </button>
            ${acik
              ? `<div class="madde-metni">${govde}
                   ${eylemler ? `<div class="eylemler">${eylemler}</div>` : ""}
                 </div>`
              : ""}
          </div>`;
      })
      .join("");
  }

  yuva.innerHTML = `<div class="sutunlar">
      <div class="sutun">
        <h5>Mevzuat Türü</h5>
        <div class="sutun-ic">${turSatirlari.join("")}</div>
      </div>
      <div class="sutun">
        <h5>Mevzuat</h5>
        <div class="sutun-ic">${mevzuatSatirlari}</div>
      </div>
      <div class="sutun">
        <h5>${maddeBasligi}</h5>
        <div class="sutun-ic">${maddeSatirlari}</div>
      </div>
    </div>`;

  yuva.querySelectorAll("[data-tur]").forEach((d) =>
    d.addEventListener("click", () => {
      gorunum.turId = d.dataset.tur;
      gorunum.mevzuatId = null;
      gorunum.maddeKimlik = null;
      ayar.onDegisim(gorunum);
    })
  );
  yuva.querySelectorAll("[data-mevzuat]").forEach((d) =>
    d.addEventListener("click", () => {
      gorunum.mevzuatId = d.dataset.mevzuat;
      gorunum.maddeKimlik = null;
      ayar.onDegisim(gorunum);
    })
  );
  // Madde satırına tıklamak metnini satırın altında açar/kapatır.
  yuva.querySelectorAll("[data-madde]").forEach((d) =>
    d.addEventListener("click", () => {
      const madde = maddeler.find((m) => m.kimlik === d.dataset.madde);
      gorunum.acikMadde = gorunum.acikMadde === madde.kimlik ? null : madde.kimlik;
      gorunum.maddeKimlik = madde.kimlik;
      if (ayar.onMadde) ayar.onMadde(madde, gorunum);
      ayar.onDegisim(gorunum);
    })
  );
  yuva.querySelectorAll("[data-eylem]").forEach((d) =>
    d.addEventListener("click", (olay) => {
      olay.stopPropagation();
      const madde = maddeler.find((m) => m.kimlik === d.dataset.eylem);
      const eylem = ayar.eylemler(madde)[Number(d.dataset.eylemNo)];
      if (eylem) eylem.calistir(madde);
    })
  );
}

/* ------------------------------------------- 2. aşama: dayanak seçim kipi */

const dayanak = {
  noksanlik: null,
  gorunum: { turId: null, mevzuatId: null, maddeKimlik: null, arama: "",
             onerilenler: [], secilenler: new Set() },
  secilenler: [],   // [{kimlik, baslik, metin}]
};

async function mevzuatKipiAc(noksanlik) {
  dayanak.noksanlik = noksanlik;
  dayanak.secilenler = noksanlik.mevzuat.map((m) => ({ ...m }));
  dayanak.gorunum = {
    turId: null, mevzuatId: null, maddeKimlik: null, arama: "",
    onerilenler: [], secilenler: new Set(dayanak.secilenler.map((m) => m.kimlik)),
  };
  $("#mevzuat-ara").value = "";
  $("#mevzuat-sutunlar").innerHTML = `<div class="bos-durum"><div class="yukleniyor"></div></div>`;
  kipAc("#mevzuat-kipi");

  try {
    await mevzuatAgaciniYukle();
    dayanak.gorunum.onerilenler = await istek("/api/mevzuat/oner", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metin: noksanlik.metin }),
    });
    dayanak.gorunum.turId = dayanak.gorunum.onerilenler.length ? "__oneri__" : "kanun";
    dayanakCiz();
  } catch (hata) {
    $("#mevzuat-sutunlar").innerHTML = `<div class="bos-durum">${kacis(hata.message)}</div>`;
  }
}

function dayanakCiz() {
  sutunlariCiz(
    {
      yuva: "#mevzuat-sutunlar",
      oneriSutunu: true,
      onDegisim: () => dayanakCiz(),
      eylemler: (madde) => {
        if (!madde.dolu) {
          return [{
            etiket: "Metni gir", ana: true,
            calistir: () => maddeKipiAc(madde, { sonra: () => dayanakCiz() }),
          }];
        }
        const secili = dayanak.secilenler.some((m) => m.kimlik === madde.kimlik);
        return [{
          etiket: secili ? "Dayanaktan çıkar" : "Dayanak olarak ekle",
          ana: !secili,
          calistir: () => {
            const yeri = dayanak.secilenler.findIndex((m) => m.kimlik === madde.kimlik);
            if (yeri >= 0) dayanak.secilenler.splice(yeri, 1);
            else dayanak.secilenler.push({
              kimlik: madde.kimlik, baslik: maddeAdi(madde), metin: madde.paragraf,
            });
            dayanak.gorunum.secilenler = new Set(dayanak.secilenler.map((m) => m.kimlik));
            dayanakCiz();
          },
        }];
      },
    },
    dayanak.gorunum
  );

  $("#mevzuat-madde-yeni").disabled = false;

  $("#mevzuat-tepsi").innerHTML = dayanak.secilenler.length
    ? `<span class="tepsi-etiket">Seçilen dayanaklar</span>` +
      dayanak.secilenler
        .map(
          (m, i) => `<span class="pul">${kacis(m.baslik)}
            <button data-pul="${i}" title="Çıkar"><svg><use href="#s-kapat"/></svg></button>
          </span>`
        )
        .join("")
    : `<span class="tepsi-etiket">Henüz dayanak seçilmedi</span>`;

  $("#mevzuat-tepsi").querySelectorAll("[data-pul]").forEach((d) =>
    d.addEventListener("click", () => {
      dayanak.secilenler.splice(Number(d.dataset.pul), 1);
      dayanak.gorunum.secilenler = new Set(dayanak.secilenler.map((m) => m.kimlik));
      dayanakCiz();
    })
  );
}

function dayanagiUygula() {
  if (!dayanak.noksanlik) return;
  if (!dayanak.secilenler.length) {
    bildir("Hiçbir dayanak seçilmedi.", "hata");
    return;
  }
  dayanak.noksanlik.mevzuat = dayanak.secilenler.map((m) => ({ ...m }));
  durumuKaydet();
  kipKapat("#mevzuat-kipi");
  noksanlikKartlariniCiz();
}

/* ------------------------------------------------------- madde düzenleme */

let maddeDuzenleme = { madde: null, yeni: false, sonra: null };

function maddeKipiAc(madde, secenekler = {}) {
  maddeDuzenleme = { madde, yeni: Boolean(secenekler.yeni), sonra: secenekler.sonra || null };
  $("#madde-kip-baslik").textContent = secenekler.yeni ? "Yeni Madde" : "Madde Düzenle";
  $("#madde-yol").innerHTML =
    `<strong>${kacis(madde.mevzuat_ad)}</strong><br>
     <span style="color:var(--metin-sonuk)">Atıf biçimi: ${kacis(madde.atif || "—")}</span>`;
  $("#madde-no").value = secenekler.yeni ? "" : madde.no || "";
  $("#madde-baslik").value = madde.baslik || "";
  $("#madde-ceza").value = madde.ceza || "";
  $("#madde-anahtar").value = (madde.anahtar || []).join(", ");
  $("#madde-paragraf").value = madde.paragraf || "";
  $("#madde-alinti").value = "";
  $("#madde-sil").classList.toggle("gizli", Boolean(secenekler.yeni) || !madde.no);
  maddeOnizlemeGuncelle();
  kipAc("#madde-kipi");
  setTimeout(() => $(secenekler.yeni ? "#madde-no" : "#madde-paragraf").focus(), 60);
}

function maddeOnizlemeGuncelle() {
  const metin = $("#madde-paragraf").value;
  $("#madde-onizleme").innerHTML = metin
    ? isaretliHtml(metin)
    : '<span style="color:var(--metin-sonuk)">Paragraf girildikçe burada görünür.</span>';
}

async function maddeKalipUret() {
  const m = maddeDuzenleme.madde;
  const alinti = $("#madde-alinti").value.trim();
  if (!alinti) {
    bildir("Önce maddenin tırnak içine alınacak metnini yazın.", "hata");
    return;
  }
  try {
    const sonuc = await istek("/api/mevzuat/kalip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        atif: m.atif, no: $("#madde-no").value.trim(),
        baslik: $("#madde-baslik").value.trim(), alinti,
        kapanis: $("#madde-kapanis").value,
      }),
    });
    $("#madde-paragraf").value = sonuc.paragraf;
    maddeOnizlemeGuncelle();
  } catch (hata) {
    bildir(hata.message, "hata");
  }
}

async function maddeyiKaydet() {
  const m = maddeDuzenleme.madde;
  const govde = {
    no: $("#madde-no").value.trim(),
    baslik: $("#madde-baslik").value.trim(),
    ceza: $("#madde-ceza").value.trim(),
    anahtar: $("#madde-anahtar").value,
    paragraf: $("#madde-paragraf").value.trim(),
    eski_no: maddeDuzenleme.yeni ? "" : m.no,
  };
  if (!govde.no) {
    bildir("Madde numarası zorunludur.", "hata");
    return;
  }
  // Önce sunucuya kaydetmeyi dene; salt-okunur ortamda (Vercel) başarısız olursa
  // tarayıcının localStorage'ına ekle — bir sonraki yüklemede merge edilir.
  let sunucuBasarili = false;
  try {
    await istek(`/api/mevzuat/${m.tur_id}/${m.mevzuat_id}/madde`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(govde),
    });
    sunucuBasarili = true;
  } catch { /* salt-okunur — localStorage fallback'e geç */ }

  if (!sunucuBasarili) {
    const liste = ekstraMaddeleriYukle();
    // Aynı mevzuat+no kombinasyonu varsa güncelle, yoksa ekle
    const eskiIdx = liste.findIndex(
      (e) => e.tur_id === m.tur_id && e.mevzuat_id === m.mevzuat_id && e.no === (govde.eski_no || govde.no)
    );
    const yeniKayit = { tur_id: m.tur_id, mevzuat_id: m.mevzuat_id, ...govde };
    if (eskiIdx >= 0) liste[eskiIdx] = yeniKayit;
    else liste.push(yeniKayit);
    ekstraMaddeleriKaydet(liste);
  }

  await mevzuatAgaciniYukle(true);
  kipKapat("#madde-kipi");
  bildir("Madde kaydedildi.", "basarili");
  if (maddeDuzenleme.sonra) maddeDuzenleme.sonra();
}

async function maddeyiSil() {
  const m = maddeDuzenleme.madde;
  if (!confirm(`${m.mevzuat_ad} m.${m.no} silinsin mi?`)) return;
  let sunucuBasarili = false;
  try {
    await istek(
      `/api/mevzuat/${m.tur_id}/${m.mevzuat_id}/madde/${encodeURIComponent(m.no)}`,
      { method: "DELETE" }
    );
    sunucuBasarili = true;
  } catch { /* salt-okunur — localStorage fallback */ }

  if (!sunucuBasarili) {
    const liste = ekstraMaddeleriYukle();
    // Daha önce localStorage'da eklendiyse oradan kaldır, yoksa silinmiş olarak işaretle
    const idx = liste.findIndex(
      (e) => e.tur_id === m.tur_id && e.mevzuat_id === m.mevzuat_id && e.no === m.no
    );
    if (idx >= 0) liste.splice(idx, 1);
    else liste.push({ tur_id: m.tur_id, mevzuat_id: m.mevzuat_id, no: m.no, _silindi: true });
    ekstraMaddeleriKaydet(liste);
  }

  await mevzuatAgaciniYukle(true);
  kipKapat("#madde-kipi");
  bildir("Madde silindi.", "basarili");
  if (maddeDuzenleme.sonra) maddeDuzenleme.sonra();
}

/* --------------------------------------------------------- yeni mevzuat */

function yeniMevzuatKipiAc() {
  $("#yeni-mevzuat-tur").innerHTML = (mevzuatAgaci || [])
    .map((t) => `<option value="${t.id}">${kacis(t.ad)}</option>`)
    .join("");
  $("#yeni-mevzuat-ad").value = "";
  $("#yeni-mevzuat-atif").value = "";
  kipAc("#mevzuat-ekle-kipi");
  setTimeout(() => $("#yeni-mevzuat-ad").focus(), 60);
}

async function yeniMevzuatKaydet() {
  const turId = $("#yeni-mevzuat-tur").value;
  const govde = {
    ad: $("#yeni-mevzuat-ad").value.trim(),
    atif: $("#yeni-mevzuat-atif").value.trim(),
  };
  
  let sunucuBasarili = false;
  try {
    await istek(`/api/mevzuat/${turId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(govde),
    });
    sunucuBasarili = true;
  } catch { /* salt-okunur — localStorage fallback */ }

  if (!sunucuBasarili) {
    const liste = ekstraMevzuatlariYukle();
    const id = "m" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    liste.push({ tur_id: turId, id, ad: govde.ad, atif: govde.atif });
    ekstraMevzuatlariKaydet(liste);
  }

  await mevzuatAgaciniYukle(true);
  kipKapat("#mevzuat-ekle-kipi");
  bildir("Mevzuat eklendi.", "basarili");
  if ($("#sayfa-kutuphane").classList.contains("etkin")) kutuphaneMevzuatCiz();
  if ($("#mevzuat-kipi").classList.contains("acik")) dayanakCiz();
}

/* ====================================================================== */
/* 2. AŞAMA — NOKSANLIKLAR                                                 */
/* ====================================================================== */

function noksanliklariHazirla() {
  kunyeyiFormdanOku();
  const onceki = new Map(durum.noksanliklar.map((n) => [n.sira, n]));
  durum.noksanliklar = durum.secili.map((sira) => {
    if (onceki.has(sira)) return onceki.get(sira);
    const paragraf = durum.paragraflar.find((p) => p.sira === sira);
    return {
      id: yeniKimlik(),
      sira,
      metin: paragraf ? paragraf.noksanlik_metni : "",
      mevzuat: [],
      oneri: null,
      acik: true,
    };
  });
  durumuKaydet();
}

function noksanlikKartlariniCiz() {
  const yuva = $("#noksanlik-kartlari");
  if (!durum.noksanliklar.length) {
    yuva.innerHTML = `<div class="bos-durum">
      <svg><use href="#s-liste"/></svg>
      <div>Henüz noksanlık seçilmedi.</div>
      <div style="font-size:12px;margin-top:6px">1. aşamada tutanaktan noksanlık seçin.</div>
    </div>`;
    $("#noksanlik-ozet").textContent = "0 madde";
    return;
  }

  yuva.innerHTML = durum.noksanliklar
    .map((n, sira) => {
      const mevzuatHtml = n.mevzuat.length
        ? n.mevzuat
            .map(
              (m, i) => `<div class="secim-parcasi">
                <div class="icerik">
                  <div class="baslik">${kacis(m.baslik)}</div>
                  <textarea data-alan="mevzuat" data-indeks="${i}"
                    style="min-height:110px;margin-top:4px">${kacis(m.metin)}</textarea>
                </div>
                <button class="dugme sade kucuk" data-mevzuat-cikar="${i}" title="Çıkar">
                  <svg><use href="#s-kapat"/></svg>
                </button>
              </div>`
            )
            .join("")
        : `<div class="bos-bilgi">Dayanak (mevzuat maddesi) seçilmedi.</div>`;

      const oneriHtml = n.oneri
        ? `<div class="secim-parcasi">
             <div class="icerik">
               <div class="baslik">${kacis(n.oneri.baslik)}</div>
               <textarea data-alan="oneri" style="min-height:120px;margin-top:4px">${kacis(n.oneri.metin)}</textarea>
             </div>
             <button class="dugme sade kucuk" data-oneri-cikar title="Çıkar">
               <svg><use href="#s-kapat"/></svg>
             </button>
           </div>`
        : `<div class="bos-bilgi">Müfettiş önerisi seçilmedi.</div>`;

      const tamamlanan = [true, n.mevzuat.length > 0, Boolean(n.oneri)].filter(Boolean).length;

      return `<div class="noksanlik-kart ${n.acik ? "acik" : ""}" data-id="${n.id}">
        <div class="noksanlik-ust" data-katla>
          <div class="rozet">${sira + 1}</div>
          <div class="ozet">${kacis(n.metin.slice(0, 150))}…</div>
          <span class="etiket ${tamamlanan === 3 ? "basarili" : "uyari"}">${tamamlanan}/3</span>
        </div>
        <div class="noksanlik-govde">

          <div class="asama tamam" data-no="1">
            <h4>Noksanlık Maddesi <span class="etiket bilgi">tutanaktan</span></h4>
            <textarea data-alan="metin" style="min-height:140px">${kacis(n.metin)}</textarea>
          </div>

          <div class="asama ${n.mevzuat.length ? "tamam" : ""}" data-no="2">
            <h4>İlgili Mevzuat Maddesi (Dayanak)</h4>
            <div class="secim-listesi">${mevzuatHtml}</div>
            <button class="dugme kucuk" data-sec="mevzuat">
              <svg><use href="#s-kitap"/></svg> Dayanak Seç
            </button>
          </div>

          <div class="asama ${n.oneri ? "tamam" : ""}" data-no="3">
            <h4>Müfettiş Önerisi</h4>
            <div class="secim-listesi">${oneriHtml}</div>
            <button class="dugme kucuk" data-sec="oneri">
              <svg><use href="#s-kalem"/></svg> Müfettiş Önerisi Seç
            </button>
          </div>

          <div class="ayirac"></div>
          <div class="dugme-sirasi">
            <button class="dugme tehlike kucuk" data-noksanlik-sil>
              <svg><use href="#s-cop"/></svg> Bu noksanlığı çıkar
            </button>
          </div>
        </div>
      </div>`;
    })
    .join("");

  const tamam = durum.noksanliklar.filter((n) => n.mevzuat.length && n.oneri).length;
  $("#noksanlik-ozet").textContent =
    `${durum.noksanliklar.length} madde · ${tamam} tamamlandı`;

  noksanlikOlaylariniBagla();
}

function noksanlikOlaylariniBagla() {
  $$("#noksanlik-kartlari .noksanlik-kart").forEach((kart) => {
    const noksanlik = durum.noksanliklar.find((n) => n.id === kart.dataset.id);
    if (!noksanlik) return;

    kart.querySelector("[data-katla]").addEventListener("click", () => {
      noksanlik.acik = !noksanlik.acik;
      kart.classList.toggle("acik", noksanlik.acik);
      durumuKaydet();
    });

    kart.querySelectorAll("textarea").forEach((alan) => {
      alan.addEventListener("input", () => {
        if (alan.dataset.alan === "metin") noksanlik.metin = alan.value;
        else if (alan.dataset.alan === "mevzuat")
          noksanlik.mevzuat[Number(alan.dataset.indeks)].metin = alan.value;
        else if (alan.dataset.alan === "oneri" && noksanlik.oneri)
          noksanlik.oneri.metin = alan.value;
        durumuKaydet();
      });
    });

    kart.querySelectorAll("[data-mevzuat-cikar]").forEach((dugme) => {
      dugme.addEventListener("click", () => {
        noksanlik.mevzuat.splice(Number(dugme.dataset.mevzuatCikar), 1);
        durumuKaydet();
        noksanlikKartlariniCiz();
      });
    });

    const oneriCikar = kart.querySelector("[data-oneri-cikar]");
    if (oneriCikar) {
      oneriCikar.addEventListener("click", () => {
        noksanlik.oneri = null;
        durumuKaydet();
        noksanlikKartlariniCiz();
      });
    }

    kart.querySelectorAll("[data-sec]").forEach((dugme) => {
      dugme.addEventListener("click", () =>
        dugme.dataset.sec === "mevzuat"
          ? mevzuatKipiAc(noksanlik)
          : oneriKipiAc(noksanlik)
      );
    });

    kart.querySelector("[data-noksanlik-sil]").addEventListener("click", () => {
      durum.noksanliklar = durum.noksanliklar.filter((n) => n.id !== noksanlik.id);
      durum.secili = durum.secili.filter((s) => s !== noksanlik.sira);
      durumuKaydet();
      noksanlikKartlariniCiz();
      paragraflariCiz();
    });
  });
}

/* ------------------------------------------------- müfettiş önerisi seçimi */

let oneriBaglami = { noksanlik: null, secili: new Set(), kayitlar: [] };

function oneriKipiAc(noksanlik) {
  oneriBaglami = { noksanlik, secili: new Set(), kayitlar: onerileriSirala(noksanlik.metin) };
  $("#secim-ara").value = "";
  kipAc("#secim-kipi");
  oneriListesiniCiz();
}

function oneriListesiniCiz() {
  const arama = kucult($("#secim-ara").value.trim());
  const kayitlar = oneriBaglami.kayitlar.filter(
    (k) =>
      !arama ||
      kucult(k.baslik + " " + k.metin + " " + (k.anahtar || []).join(" ")).includes(arama)
  );

  const yuva = $("#secim-listesi");
  if (!kayitlar.length) {
    yuva.innerHTML = `<div class="bos-durum">
      <svg><use href="#s-kalem"/></svg>
      <div>${onerileriOku().length ? "Eşleşen öneri yok." : "Henüz öneri eklemediniz."}</div>
      <div style="font-size:12px;margin-top:6px">
        Aşağıdaki “Kütüphaneye yeni kayıt” ile kendi kalıplarınızı oluşturun.
      </div></div>`;
    return;
  }

  yuva.innerHTML = kayitlar
    .map(
      (k) => `<div class="kayit-satiri ${oneriBaglami.secili.has(k.id) ? "secili" : ""}"
                   data-id="${k.id}">
        <div class="ust">
          <span class="ad">${kacis(k.baslik)}</span>
          ${k.puan > 0 ? `<span class="etiket aday">bu noksanlıkla ilgili</span>` : ""}
        </div>
        <div class="metin">${k.html || isaretliHtml(k.metin)}</div>
      </div>`
    )
    .join("");

  yuva.querySelectorAll(".kayit-satiri").forEach((satir) => {
    satir.addEventListener("click", () => {
      oneriBaglami.secili.clear();
      oneriBaglami.secili.add(satir.dataset.id);
      oneriListesiniCiz();
    });
  });
}

function oneriyiUygula() {
  const { noksanlik, secili, kayitlar } = oneriBaglami;
  if (!noksanlik) return;
  const kayit = kayitlar.find((k) => secili.has(k.id));
  if (!kayit) {
    bildir("Hiçbir öneri seçilmedi.", "hata");
    return;
  }
  noksanlik.oneri = { kaynakId: kayit.id, baslik: kayit.baslik, metin: kayit.metin };
  durumuKaydet();
  kipKapat("#secim-kipi");
  noksanlikKartlariniCiz();
}

/* ====================================================================== */
/* MÜFETTİŞ ÖNERİLERİ — tarayıcıda saklanır                                */
/*                                                                         */
/* Öneriler müfettişin kendi kalıplarıdır ve kişiye özeldir; bu yüzden     */
/* sunucuda değil tarayıcıda tutulur. Böylece sunucusuz kurulumda da       */
/* (Vercel'de dosya sistemi salt okunurdur) eklenip düzenlenebilirler.     */
/* Tarayıcı verisi silinebileceği için dışa/içe aktarma da sunulur.        */
/* ====================================================================== */

const ONERI_ANAHTARI = "mufettis-programi-oneriler-v1";

const yeniOneriKimligi = () =>
  "o" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

function onerileriOku() {
  try {
    const ham = localStorage.getItem(ONERI_ANAHTARI);
    const liste = ham ? JSON.parse(ham) : [];
    return Array.isArray(liste) ? liste : [];
  } catch (hata) {
    return [];
  }
}

function onerileriYaz(liste) {
  try {
    localStorage.setItem(ONERI_ANAHTARI, JSON.stringify(liste));
    return true;
  } catch (hata) {
    bildir("Öneriler kaydedilemedi: tarayıcı deposu dolu ya da kapalı.", "hata");
    return false;
  }
}

function oneriKaydet(kayit, kimlik) {
  const liste = onerileriOku();
  const temiz = {
    id: kimlik || yeniOneriKimligi(),
    baslik: (kayit.baslik || "").trim(),
    anahtar: String(kayit.anahtar || "").split(",").map((a) => a.trim()).filter(Boolean),
    metin: (kayit.metin || "").trim(),
  };
  const yeri = liste.findIndex((k) => k.id === temiz.id);
  if (yeri >= 0) liste[yeri] = temiz;
  else liste.push(temiz);
  return onerileriYaz(liste) ? temiz : null;
}

function oneriSil(kimlik) {
  return onerileriYaz(onerileriOku().filter((k) => k.id !== kimlik));
}

/** Türkçe duyarlı sadeleştirme — anahtar kelime eşleştirmesi için. */
function sadelestir(metin) {
  const harfler = { "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u" };
  return String(metin == null ? "" : metin)
    .replace(/I/g, "ı")
    .replace(/İ/g, "i")
    .toLowerCase()
    .replace(/[çğıöşü]/g, (h) => harfler[h])
    .replace(/\s+/g, " ");
}

/** Önerileri, noksanlık metniyle ilgisine göre sıralar. */
function onerileriSirala(noksanlikMetni) {
  const hedef = sadelestir(noksanlikMetni);
  return onerileriOku()
    .map((k) => ({
      ...k,
      puan: (k.anahtar || []).filter((a) => hedef.includes(sadelestir(a))).length,
    }))
    .sort((a, b) => b.puan - a.puan || a.baslik.localeCompare(b.baslik, "tr"));
}

function onerileriDisaAktar() {
  const liste = onerileriOku();
  if (!liste.length) {
    bildir("Dışa aktarılacak öneri yok.", "hata");
    return;
  }
  const blob = new Blob([JSON.stringify(liste, null, 2)], { type: "application/json" });
  const adres = URL.createObjectURL(blob);
  const bag = document.createElement("a");
  bag.href = adres;
  bag.download = "mufettis-onerileri.json";
  document.body.appendChild(bag);
  bag.click();
  bag.remove();
  URL.revokeObjectURL(adres);
  bildir(liste.length + " öneri dosyaya aktarıldı.", "basarili");
}

async function onerileriIceAktar(dosya) {
  if (!dosya) return;
  try {
    const gelen = JSON.parse(await dosya.text());
    if (!Array.isArray(gelen)) throw new Error("Dosya bir öneri listesi değil.");
    const mevcut = onerileriOku();
    const kimlikler = new Set(mevcut.map((k) => k.id));
    let eklenen = 0;
    gelen.forEach((k) => {
      if (!k || !k.baslik || !k.metin) return;
      if (k.id && kimlikler.has(k.id)) return;   // aynısı zaten var
      mevcut.push({
        id: k.id || yeniOneriKimligi(),
        baslik: String(k.baslik).trim(),
        anahtar: Array.isArray(k.anahtar) ? k.anahtar : [],
        metin: String(k.metin).trim(),
      });
      eklenen += 1;
    });
    if (onerileriYaz(mevcut)) {
      bildir(eklenen + " öneri içe aktarıldı.", "basarili");
      oneriKutuphanesiniCiz();
    }
  } catch (hata) {
    bildir("Dosya okunamadı: " + hata.message, "hata");
  }
}

/* ====================================================================== */
/* 3. AŞAMA — BELGE                                                        */
/* ====================================================================== */

function belgeFormunuYaz() {
  const b = durum.belge;
  $("#b-sayi").value = b.sayi || "";
  $("#b-tarih").value = b.tarih || "";
  $("#b-eposta").value = b.eposta || "";
  $("#b-bildirim-tarihi").value = b.bildirimTarihi || "";
  $("#b-bildirim-saati").value = b.bildirimSaati || "";
  $("#t-ad").value = b.tebAd || "";
  $("#t-baba").value = b.tebBaba || "";
  $("#t-dogum").value = b.tebDogum || "";
  $("#t-tckn").value = b.tebTckn || "";
  $("#t-gorev").value = b.tebGorev || "";
  $("#t-tarih").value = b.tebTarih || "";
}

function belgeFormunuOku() {
  Object.assign(durum.belge, {
    sayi: $("#b-sayi").value.trim(),
    tarih: $("#b-tarih").value.trim(),
    eposta: $("#b-eposta").value.trim(),
    bildirimTarihi: $("#b-bildirim-tarihi").value.trim(),
    bildirimSaati: $("#b-bildirim-saati").value.trim(),
    tebAd: $("#t-ad").value.trim(),
    tebBaba: $("#t-baba").value.trim(),
    tebDogum: $("#t-dogum").value.trim(),
    tebTckn: $("#t-tckn").value.trim(),
    tebGorev: $("#t-gorev").value.trim(),
    tebTarih: $("#t-tarih").value.trim(),
  });
  durumuKaydet();
}

function belgeOzetiCiz() {
  const eksikMevzuat = durum.noksanliklar.filter((n) => !n.mevzuat.length).length;
  const eksikOneri = durum.noksanliklar.filter((n) => !n.oneri).length;
  const kutular = [
    ["Noksanlık maddesi", durum.noksanliklar.length, false],
    ["Dayanağı eksik", eksikMevzuat, true],
    ["Önerisi eksik", eksikOneri, true],
  ];
  $("#belge-ozet").innerHTML = kutular
    .map(
      ([ad, sayi, uyar]) => `<div class="ozet-kutu">
        <div class="sayi" ${uyar && sayi > 0 ? 'style="color:var(--sari)"' : ""}>${sayi}</div>
        <div class="ad">${ad}</div>
      </div>`
    )
    .join("");
}

function belgeVerisi() {
  kunyeyiFormdanOku();
  belgeFormunuOku();
  const k = durum.kunye || {};
  const b = durum.belge;
  return {
    sayi: b.sayi,
    tarih: b.tarih,
    unvan: k.unvan || "",
    adres: k.adres || "",
    giris: k.giris_metni || "",
    bildirim_tarihi: b.bildirimTarihi,
    bildirim_saati: b.bildirimSaati,
    sgk_sicil_no: k.sgk_sicil_no || "",
    eposta: b.eposta,
    mufettis_1: (k.mufettisler || [])[0] || "",
    mufettis_2: (k.mufettisler || [])[1] || "",
    teb_ad_soyad: b.tebAd,
    teb_baba_ana: b.tebBaba,
    teb_dogum: b.tebDogum,
    teb_tckn: b.tebTckn,
    teb_gorev: b.tebGorev,
    teb_tarih: b.tebTarih,
    noksanliklar: durum.noksanliklar.map((n) => ({
      metin: n.metin,
      mevzuat: n.mevzuat.map((m) => m.metin),
      oneri: n.oneri ? n.oneri.metin : "",
    })),
  };
}

async function onizlemeAc() {
  const veri = belgeVerisi();
  if (!veri.noksanliklar.length) {
    bildir("En az bir noksanlık maddesi gerekli.", "hata");
    return;
  }
  try {
    const sonuc = await istek("/api/onizleme", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(veri),
    });
    const y = sonuc.yer_tutucular;
    const bloklar = sonuc.bloklar
      .map(
        (blok) => `
        <p class="madde">${blok.numara} ${kacis(blok.metin)}</p>
        ${blok.mevzuat.map((m) => `<p>${m}</p>`).join("")}
        ${blok.oneri ? `<p>${blok.oneri}</p>` : ""}`
      )
      .join("");
    $("#onizleme-govde").innerHTML = `
      <p class="ust-satir"><strong>Sayı : ${kacis(y["{{SAYI}}"])}</strong>
        <span>${kacis(y["{{TARIH}}"])}</span></p>
      <p style="text-indent:0"><strong>Konu:</strong> Noksanlıklar/Aykırılıklar</p>
      <br>
      <p class="orta" style="text-indent:0">${kacis(y["{{UNVAN}}"])}</p>
      <p class="orta" style="text-indent:0">${kacis(y["{{ADRES}}"])}</p>
      <br>
      <p>${kacis(y["{{GIRIS}}"])}</p>
      ${bloklar}
      <br>
      <p>Tarafınıza tebliğ edilen iş bu bildirim … belirtilen süre sonunda teftiş
         tamamlanacağından <strong>${kacis(y["{{BILDIRIM_TARIHI}}"])} tarihinde saat
         ${kacis(y["{{BILDIRIM_SAATI}}"])}’da</strong> işyerinde noksanlık ve aykırılıkların
         giderildiğine ilişkin defter, kayıt ve belgelerin hazır bulundurulması … rica ederiz.</p>
      <br>
      <p style="text-indent:0;text-align:center">
        ${kacis(y["{{MUFETTIS_1}}"])} &nbsp;&nbsp;&nbsp;&nbsp; ${kacis(y["{{MUFETTIS_2}}"])}<br>
        Bakan a.<br>İş Müfettişi
      </p>`;
    kipAc("#onizleme-kipi");
  } catch (hata) {
    bildir(hata.message, "hata");
  }
}

async function belgeyiOlustur(dugme) {
  const veri = belgeVerisi();
  if (!veri.noksanliklar.length) {
    bildir("En az bir noksanlık maddesi gerekli.", "hata");
    return;
  }
  const eksik = durum.noksanliklar.findIndex((n) => !n.mevzuat.length || !n.oneri);
  if (eksik >= 0 &&
      !confirm(`${eksik + 1}. noksanlığın dayanağı veya önerisi eksik. Yine de oluşturulsun mu?`)) {
    return;
  }

  const eskiHtml = dugme ? dugme.innerHTML : "";
  if (dugme) {
    dugme.disabled = true;
    dugme.innerHTML = `<span class="yukleniyor"></span> Oluşturuluyor…`;
  }
  try {
    const blob = await istek("/api/bildirim", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(veri),
    });
    const adres = URL.createObjectURL(blob);
    const bag = document.createElement("a");
    bag.href = adres;
    bag.download = `${veri.unvan || "Noksanlik"} - Noksanlık Bildirimi.docx`;
    document.body.appendChild(bag);
    bag.click();
    bag.remove();
    URL.revokeObjectURL(adres);
    bildir("Noksanlık bildirimi oluşturuldu ve indirildi.", "basarili");
  } catch (hata) {
    bildir(hata.message, "hata");
  } finally {
    if (dugme) {
      dugme.disabled = false;
      dugme.innerHTML = eskiHtml;
    }
  }
}

/* ====================================================================== */
/* KÜTÜPHANE                                                               */
/* ====================================================================== */

let kutuphaneSekmesi = "mevzuat";
let duzenlenenKayit = null;

const kutGorunum = { turId: "kanun", mevzuatId: null, maddeKimlik: null, arama: "" };

function kutuphaneAc() {
  if (kutuphaneSekmesi === "mevzuat") kutuphaneMevzuatCiz();
  else oneriKutuphanesiniCiz();
}

async function kutuphaneMevzuatCiz() {
  const yuva = $("#kut-sutunlar");
  if (!mevzuatAgaci) {
    yuva.innerHTML = `<div class="bos-durum"><div class="yukleniyor"></div></div>`;
    try {
      await mevzuatAgaciniYukle();
    } catch (hata) {
      yuva.innerHTML = `<div class="bos-durum">${kacis(hata.message)}</div>`;
      return;
    }
  }

  kutGorunum.arama = $("#kut-mevzuat-ara").value;
  sutunlariCiz(
    {
      yuva: "#kut-sutunlar",
      oneriSutunu: false,
      onDegisim: () => kutuphaneMevzuatCiz(),
      eylemler: (madde) => [{
        etiket: madde.dolu ? "Metni düzenle" : "Metni gir",
        ana: !madde.dolu,
        calistir: () => maddeKipiAc(madde, { sonra: () => kutuphaneMevzuatCiz() }),
      }],
    },
    kutGorunum
  );

  $("#kut-madde-yeni").disabled = !kutGorunum.mevzuatId;
}

function oneriKutuphanesiniCiz() {
  const yuva = $("#kutuphane-listesi");
  const kayitlar = onerileriOku();
  const arama = kucult($("#kutuphane-ara").value.trim());
  const suzulmus = kayitlar.filter(
    (k) =>
      !arama ||
      kucult(k.baslik + " " + k.metin + " " + (k.anahtar || []).join(" ")).includes(arama)
  );

  $("#oneri-sayaci").textContent = `${kayitlar.length} öneri`;

  if (!suzulmus.length) {
    yuva.innerHTML = `<div class="bos-durum">
      <svg><use href="#s-kalem"/></svg>
      <div>${kayitlar.length ? "Eşleşen öneri yok." : "Henüz öneri eklemediniz."}</div>
      <div style="font-size:12px;margin-top:6px">
        ${kayitlar.length ? "Aramayı değiştirin." : "“Yeni öneri” ile ilk kalıbınızı oluşturun."}
      </div></div>`;
    return;
  }

  yuva.innerHTML = suzulmus
    .map(
      (k) => `<div class="kayit-satiri" data-id="${k.id}">
        <div class="ust">
          <span class="ad">${kacis(k.baslik)}</span>
          <span class="etiket">${(k.anahtar || []).length} anahtar</span>
        </div>
        <div class="metin">${isaretliHtml(k.metin)}</div>
      </div>`
    )
    .join("");
  yuva.querySelectorAll(".kayit-satiri").forEach((satir) => {
    satir.addEventListener("click", () =>
      kayitKipiAc(kayitlar.find((k) => k.id === satir.dataset.id))
    );
  });
}

function kayitKipiAc(kayit) {
  duzenlenenKayit = kayit || null;
  $("#kayit-kip-baslik").textContent = kayit ? "Öneriyi Düzenle" : "Yeni Müfettiş Önerisi";
  $("#kayit-baslik").value = kayit ? kayit.baslik : "";
  $("#kayit-anahtar").value = kayit ? (kayit.anahtar || []).join(", ") : "";
  $("#kayit-metin").value = kayit ? kayit.metin : "__Buna göre;__ ";
  $("#kayit-sil").classList.toggle("gizli", !kayit);
  kayitOnizlemeGuncelle();
  kipAc("#kayit-kipi");
  setTimeout(() => $("#kayit-baslik").focus(), 60);
}

function kayitOnizlemeGuncelle() {
  $("#kayit-onizleme").innerHTML = isaretliHtml($("#kayit-metin").value) ||
    '<span style="color:var(--metin-sonuk)">Metin girildikçe burada görünür.</span>';
}

function kaydiKaydet() {
  const govde = {
    baslik: $("#kayit-baslik").value.trim(),
    anahtar: $("#kayit-anahtar").value,
    metin: $("#kayit-metin").value.trim(),
  };
  if (!govde.baslik || !govde.metin) {
    bildir("Başlık ve metin zorunludur.", "hata");
    return;
  }
  const kayit = oneriKaydet(govde, duzenlenenKayit ? duzenlenenKayit.id : null);
  if (!kayit) return;
  bildir(duzenlenenKayit ? "Öneri güncellendi." : "Öneri eklendi.", "basarili");
  kipKapat("#kayit-kipi");
  oneriListesiniTazele(kayit.id);
}

/**
 * Öneri listelerini günceller. Kayıt kipi hem Kütüphane sekmesinden hem de
 * seçim penceresinin içinden açılabildiği için ikisi de tazelenir; seçim
 * penceresi açıksa yeni eklenen öneri doğrudan seçili gelir.
 */
function oneriListesiniTazele(secilecekKimlik) {
  if ($("#sayfa-kutuphane").classList.contains("etkin")) oneriKutuphanesiniCiz();
  if (!$("#secim-kipi").classList.contains("acik")) return;
  oneriBaglami.kayitlar = onerileriSirala(oneriBaglami.noksanlik.metin);
  if (secilecekKimlik) {
    oneriBaglami.secili.clear();
    oneriBaglami.secili.add(secilecekKimlik);
  }
  oneriListesiniCiz();
}

function kaydiSil() {
  if (!duzenlenenKayit) return;
  if (!confirm(`“${duzenlenenKayit.baslik}” önerisi silinsin mi?`)) return;
  if (!oneriSil(duzenlenenKayit.id)) return;
  bildir("Öneri silindi.", "basarili");
  kipKapat("#kayit-kipi");
  oneriListesiniTazele();
}

/* ====================================================================== */
/* OLAY BAĞLAMALARI                                                        */
/* ====================================================================== */

function olaylariBagla() {
  // Yan menü ve adım şeridi
  $$("[data-sayfa]").forEach((dugme) =>
    dugme.addEventListener("click", () => {
      if (dugme.dataset.sayfa === "noksanliklar") {
        noksanliklariHazirla();
        noksanlikKartlariniCiz();
      }
      sayfaAc(dugme.dataset.sayfa);
    })
  );

  // Dosya yükleme
  dosyaGirdisiniBagla();
  const alan = $("#birak-alani");
  ["dragenter", "dragover"].forEach((olay) =>
    alan.addEventListener(olay, (e) => {
      e.preventDefault();
      alan.classList.add("uzerinde");
    })
  );
  ["dragleave", "drop"].forEach((olay) =>
    alan.addEventListener(olay, (e) => {
      e.preventDefault();
      alan.classList.remove("uzerinde");
    })
  );
  alan.addEventListener("drop", (e) => tutanagiYukle(e.dataTransfer.files[0]));

  // 1. aşama
  $("#tumunu-goster").addEventListener("click", () => {
    durum.tumunuGoster = !durum.tumunuGoster;
    paragraflariCiz();
  });
  ["#k-unvan", "#k-adres", "#k-sicil", "#k-giris", "#k-mufettis1", "#k-mufettis2"].forEach(
    (secici) => $(secici).addEventListener("input", kunyeyiFormdanOku)
  );
  $("#noksanliga-gec").addEventListener("click", () => {
    if (!durum.secili.length) {
      bildir("En az bir noksanlık seçin.", "hata");
      return;
    }
    noksanliklariHazirla();
    noksanlikKartlariniCiz();
    sayfaAc("noksanliklar");
  });

  // 2. aşama
  $("#belgeye-gec").addEventListener("click", () => sayfaAc("belge"));

  // Dayanak (mevzuat) kipi
  $("#mevzuat-ara").addEventListener("input", () => {
    dayanak.gorunum.arama = $("#mevzuat-ara").value;
    dayanakCiz();
  });
  $("#mevzuat-uygula").addEventListener("click", dayanagiUygula);
  $("#mevzuat-madde-yeni").addEventListener("click", () => {
    const mevzuat = mevzuatBul(dayanak.gorunum.turId, dayanak.gorunum.mevzuatId);
    if (!mevzuat) {
      bildir("Önce sol sütundan bir kanun / yönetmelik seçin.", "uyari");
      return;
    }
    maddeKipiAc(
      { tur_id: dayanak.gorunum.turId, mevzuat_id: mevzuat.id,
        mevzuat_ad: mevzuat.ad, atif: mevzuat.atif, no: "", baslik: "", ceza: "",
        anahtar: [], paragraf: "" },
      { yeni: true, sonra: () => dayanakCiz() }
    );
  });

  // Müfettiş önerisi kipi
  $("#secim-ara").addEventListener("input", oneriListesiniCiz);
  $("#secimi-uygula").addEventListener("click", oneriyiUygula);
  $("#secimden-yeni").addEventListener("click", () => kayitKipiAc(null));

  // Madde düzenleme kipi
  $("#madde-paragraf").addEventListener("input", maddeOnizlemeGuncelle);
  $("#madde-kalip-uret").addEventListener("click", maddeKalipUret);
  $("#madde-kaydet").addEventListener("click", maddeyiKaydet);
  $("#madde-sil").addEventListener("click", maddeyiSil);

  // Yeni mevzuat kipi
  $("#yeni-mevzuat-kaydet").addEventListener("click", yeniMevzuatKaydet);

  // 3. aşama
  $$("#sayfa-belge input").forEach((alanGirdisi) =>
    alanGirdisi.addEventListener("input", () => {
      belgeFormunuOku();
      belgeOzetiCiz();
    })
  );
  $("#vekilden-doldur").addEventListener("click", () => {
    const k = durum.kunye || {};
    $("#t-ad").value = k.vekil_adi || "";
    $("#t-gorev").value = k.vekil_gorevi || "";
    $("#t-tarih").value = k.tutanak_tarihi || "";
    belgeFormunuOku();
    bildir("İşveren vekili bilgileri dolduruldu.", "basarili");
  });
  $("#onizle-dugme").addEventListener("click", onizlemeAc);
  $("#olustur-dugme").addEventListener("click", (e) => belgeyiOlustur(e.currentTarget));
  $("#onizlemeden-olustur").addEventListener("click", (e) => {
    kipKapat("#onizleme-kipi");
    belgeyiOlustur(e.currentTarget);
  });

  // Kütüphane
  $$(".kut-sekme").forEach((dugme) =>
    dugme.addEventListener("click", () => {
      kutuphaneSekmesi = dugme.dataset.sekme;
      $$(".kut-sekme").forEach((d) => d.classList.toggle("ana", d === dugme));
      $("#kut-mevzuat").classList.toggle("gizli", kutuphaneSekmesi !== "mevzuat");
      $("#kut-oneri").classList.toggle("gizli", kutuphaneSekmesi !== "oneri");
      kutuphaneAc();
    })
  );
  $("#kut-mevzuat-ara").addEventListener("input", kutuphaneMevzuatCiz);
  $("#kut-madde-yeni").addEventListener("click", () => {
    const mevzuat = mevzuatBul(kutGorunum.turId, kutGorunum.mevzuatId);
    if (!mevzuat) return;
    maddeKipiAc(
      { tur_id: kutGorunum.turId, mevzuat_id: mevzuat.id, mevzuat_ad: mevzuat.ad,
        atif: mevzuat.atif, no: "", baslik: "", ceza: "", anahtar: [], paragraf: "" },
      { yeni: true, sonra: () => kutuphaneMevzuatCiz() }
    );
  });
  $("#kut-mevzuat-yeni").addEventListener("click", yeniMevzuatKipiAc);
  $("#kutuphane-ara").addEventListener("input", oneriKutuphanesiniCiz);
  $("#yeni-kayit").addEventListener("click", () => kayitKipiAc(null));
  $("#oneri-disa").addEventListener("click", onerileriDisaAktar);
  $("#oneri-ice").addEventListener("click", () => $("#oneri-dosya").click());
  $("#oneri-dosya").addEventListener("change", (e) => {
    onerileriIceAktar(e.target.files[0]);
    e.target.value = "";
  });
  $("#kayit-metin").addEventListener("input", kayitOnizlemeGuncelle);
  $("#kayit-kaydet").addEventListener("click", kaydiKaydet);
  $("#kayit-sil").addEventListener("click", kaydiSil);

  // Kip kapatma
  $$("[data-kapat]").forEach((dugme) =>
    dugme.addEventListener("click", () => dugme.closest(".kip-perde").classList.remove("acik"))
  );
  $$(".kip-perde").forEach((perde) =>
    perde.addEventListener("click", (e) => {
      if (e.target === perde) perde.classList.remove("acik");
    })
  );
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    // En üstteki kipi kapat (madde kipi dayanak kipinin üstünde açılabilir).
    const acikKipler = $$(".kip-perde.acik");
    if (acikKipler.length) acikKipler[acikKipler.length - 1].classList.remove("acik");
  });

  // Sıfırla
  $("#sifirla-dugme").addEventListener("click", () => {
    if (!confirm("Yüklenen tutanak ve tüm seçimler silinsin mi?")) return;
    localStorage.removeItem(SAKLAMA_ANAHTARI);
    location.reload();
  });
}

/* ------------------------------------------------------------- başlangıç */

async function ortamiOgren() {
  try {
    const o = await istek("/api/ortam");
    yerelKurulum = Boolean(o.yerel);
  } catch (hata) {
    yerelKurulum = true;
  }
  if (yerelKurulum) return;
  $("#salt-okunur-not").classList.remove("gizli");
}

document.addEventListener("DOMContentLoaded", () => {
  olaylariBagla();
  ortamiOgren();
  if (durumuYukle()) {
    $("#tutanak-sonuc").classList.remove("gizli");
    kunyeyiFormaYaz();
    paragraflariCiz();
    belgeFormunuYaz();
    noksanlikKartlariniCiz();
    bildir("Önceki çalışma geri yüklendi.", "basarili");
  }
});

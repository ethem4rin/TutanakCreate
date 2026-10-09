# -*- coding: utf-8 -*-
"""
Müfettiş Programı — Noksanlık/Aykırılık Bildirimi üreteci.

Çalıştırma:
    python app.py
Ardından tarayıcıdan http://127.0.0.1:5000 adresini açın.
"""
from __future__ import annotations

import io
import re
import traceback
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from core import belge as belge_modulu
from core import kutuphane
from core import mevzuat as mevzuat_modulu
from core import tutanak as tutanak_modulu
from core.kutuphane import KutuphaneHatasi
from core.metin import html_onizleme
from core.mevzuat import MevzuatHatasi

KOK = Path(__file__).resolve().parent
CIKTI_DIZINI = KOK / "calisma" / "cikti"


def _yazilabilir_mi(dizin: Path) -> bool:
    """Dizin oluşturulabiliyor ve yazılabiliyor mu? (Vercel'de dosya sistemi salt okunur.)"""
    try:
        dizin.mkdir(parents=True, exist_ok=True)
        deneme = dizin / ".yazma-denemesi"
        deneme.write_text("", encoding="utf-8")
        deneme.unlink()
        return True
    except OSError:
        return False


# Sunucusuz ortamda (Vercel) disk salt okunurdur: tutanak bellekte çözümlenir,
# bildirim bellekte üretilir ve kütüphane düzenlemesi kapatılır.
YEREL = _yazilabilir_mi(CIKTI_DIZINI)

# Statik dosyalar `public/` altındadır: Vercel bu klasörü CDN'den sunar, Flask
# da yerelde aynı adreslerden (/css/app.css) verir. Böylece şablondaki
# bağlantılar iki ortamda da aynı çalışır.
app = Flask(__name__, static_folder="public", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB
app.config["JSON_AS_ASCII"] = False


def _dosya_adi_temizle(ad: str) -> str:
    ad = re.sub(r"[^\w\s.\-()İıĞğÜüŞşÖöÇç]", "", ad, flags=re.UNICODE).strip()
    return re.sub(r"\s+", " ", ad) or "Noksanlik Bildirimi"


@app.errorhandler(RequestEntityTooLarge)
def _buyuk_dosya(_hata):
    return jsonify({"hata": "Dosya çok büyük (en fazla 25 MB)."}), 413


@app.errorhandler(Exception)
def _beklenmeyen_hata(hata):
    if isinstance(hata, (KutuphaneHatasi, MevzuatHatasi)):
        return jsonify({"hata": str(hata)}), 400
    if isinstance(hata, HTTPException):  # 404, 405 … olduğu gibi geçsin
        return hata
    app.logger.error("Beklenmeyen hata:\n%s", traceback.format_exc())
    return jsonify({"hata": f"Beklenmeyen hata: {hata}"}), 500


# --------------------------------------------------------------------------- #
# Sayfalar
# --------------------------------------------------------------------------- #

@app.get("/")
def anasayfa():
    return render_template("index.html", yerel=YEREL)


@app.get("/api/ortam")
def ortam():
    """Arayüz, kütüphane düzenlemesinin açık olup olmadığını buradan öğrenir."""
    return jsonify({"yerel": YEREL})


def _yazma_izni():
    """Salt okunur ortamda kütüphaneyi değiştiren uçları kapatır."""
    if not YEREL:
        raise KutuphaneHatasi(
            "Bu kurulumda kütüphane salt okunurdur. Mevzuat ve öneri "
            "düzenlemelerini kendi bilgisayarınızda yapıp depoya gönderin."
        )


# --------------------------------------------------------------------------- #
# 1. Aşama — Tutanağı yükle ve çözümle
# --------------------------------------------------------------------------- #

@app.post("/api/tutanak")
def tutanak_yukle():
    dosya = request.files.get("dosya")
    if dosya is None or not dosya.filename:
        return jsonify({"hata": "Tutanak dosyası seçilmedi."}), 400
    if not dosya.filename.lower().endswith(".docx"):
        return jsonify({"hata": "Yalnızca .docx uzantılı Word dosyaları yüklenebilir."}), 400

    # Tutanak diske yazılmadan bellekte çözümlenir: hem sunucusuz ortamda
    # çalışır hem de kişisel veri taşıyan belge sunucuda kalmaz.
    try:
        sonuc = tutanak_modulu.coz(io.BytesIO(dosya.read()))
    except Exception as hata:  # bozuk/uyumsuz belge
        return jsonify({"hata": f"Tutanak okunamadı: {hata}"}), 400

    veri = sonuc.sozluk()
    veri["dosya_adi"] = dosya.filename
    # Noksanlık metinleri madde numarası olmadan hazırlanır.
    for paragraf in veri["paragraflar"]:
        paragraf["noksanlik_metni"] = tutanak_modulu.madde_numarasini_ayikla(paragraf["metin"])
    return jsonify(veri)


# --------------------------------------------------------------------------- #
# 2. Aşama — Mevzuat (Mevzuat Türü → Mevzuat → Madde)
# --------------------------------------------------------------------------- #

def _madde_sus(madde: dict) -> dict:
    """Madde kaydına arayüz için HTML önizlemesi ekler."""
    return {**madde, "html": html_onizleme(madde.get("paragraf", ""))}


@app.get("/api/mevzuat")
def mevzuat_agaci():
    """Kademeli seçici için tür → mevzuat → madde ağacı."""
    agac = mevzuat_modulu.agaci_listele()
    for tur in agac:
        for mevzuat in tur["mevzuat"]:
            mevzuat["maddeler"] = [_madde_sus(m) for m in mevzuat["maddeler"]]
    return jsonify(agac)


@app.post("/api/mevzuat/oner")
def mevzuat_oner():
    """Noksanlık metnine göre en ilgili maddeleri sıralar."""
    govde = request.get_json(silent=True) or {}
    maddeler = mevzuat_modulu.oner(govde.get("metin", ""))
    return jsonify([_madde_sus(m) for m in maddeler])


@app.post("/api/mevzuat/<tur_id>/<mevzuat_id>/madde")
def mevzuat_madde_kaydet(tur_id: str, mevzuat_id: str):
    _yazma_izni()
    govde = request.get_json(silent=True) or {}
    madde = mevzuat_modulu.madde_kaydet(
        tur_id, mevzuat_id, govde, eski_no=govde.get("eski_no", "")
    )
    return jsonify(_madde_sus(madde))


@app.delete("/api/mevzuat/<tur_id>/<mevzuat_id>/madde/<path:no>")
def mevzuat_madde_sil(tur_id: str, mevzuat_id: str, no: str):
    _yazma_izni()
    mevzuat_modulu.madde_sil(tur_id, mevzuat_id, no)
    return jsonify({"durum": "silindi"})


@app.post("/api/mevzuat/<tur_id>")
def mevzuat_ekle(tur_id: str):
    _yazma_izni()
    govde = request.get_json(silent=True) or {}
    yeni = mevzuat_modulu.mevzuat_kaydet(tur_id, govde, eski_id=govde.get("eski_id", ""))
    return jsonify(yeni), 201


@app.post("/api/mevzuat/kalip")
def mevzuat_kalip():
    """Yeni madde eklerken hazır paragraf kalıbı üretir."""
    g = request.get_json(silent=True) or {}
    return jsonify(
        {
            "paragraf": mevzuat_modulu.varsayilan_paragraf(
                g.get("atif", ""), g.get("no", ""), g.get("baslik", ""),
                g.get("alinti", ""), g.get("kapanis", "Hükmü amirdir."),
            )
        }
    )


# --------------------------------------------------------------------------- #
# 3. Aşama — Müfettiş önerisi kütüphanesi
# --------------------------------------------------------------------------- #

@app.get("/api/kutuphane/<tur>")
def kutuphane_listele(tur: str):
    kayitlar = kutuphane.yukle(tur)
    for kayit in kayitlar:
        kayit["html"] = html_onizleme(kayit["metin"])
    return jsonify(kayitlar)


@app.post("/api/kutuphane/<tur>/oner")
def kutuphane_oner(tur: str):
    govde = request.get_json(silent=True) or {}
    kayitlar = kutuphane.puanla(tur, govde.get("metin", ""))
    for kayit in kayitlar:
        kayit["html"] = html_onizleme(kayit["metin"])
    return jsonify(kayitlar)


@app.post("/api/kutuphane/<tur>")
def kutuphane_ekle(tur: str):
    _yazma_izni()
    kayit = kutuphane.ekle(tur, request.get_json(silent=True) or {})
    kayit["html"] = html_onizleme(kayit["metin"])
    return jsonify(kayit), 201


@app.put("/api/kutuphane/<tur>/<kayit_id>")
def kutuphane_guncelle(tur: str, kayit_id: str):
    _yazma_izni()
    kayit = kutuphane.guncelle(tur, kayit_id, request.get_json(silent=True) or {})
    kayit["html"] = html_onizleme(kayit["metin"])
    return jsonify(kayit)


@app.delete("/api/kutuphane/<tur>/<kayit_id>")
def kutuphane_sil(tur: str, kayit_id: str):
    _yazma_izni()
    kutuphane.sil(tur, kayit_id)
    return jsonify({"durum": "silindi"})


# --------------------------------------------------------------------------- #
# Belge üretimi
# --------------------------------------------------------------------------- #

def _veriyi_al() -> belge_modulu.BildirimVerisi:
    govde = request.get_json(silent=True) or {}
    veri = belge_modulu.BildirimVerisi.sozlukten(govde)
    if not veri.noksanliklar:
        raise KutuphaneHatasi("En az bir noksanlık maddesi seçilmelidir.")
    return veri


@app.post("/api/onizleme")
def bildirim_onizleme():
    """Belgeyi indirmeden önce tarayıcıda göstermek için HTML döndürür."""
    veri = _veriyi_al()
    bloklar = []
    for sira, noksanlik in enumerate(veri.noksanliklar, start=1):
        bloklar.append(
            {
                "numara": f"{sira}-",
                "metin": noksanlik.metin,
                "mevzuat": [html_onizleme(m) for m in noksanlik.mevzuat],
                "oneri": html_onizleme(noksanlik.oneri) if noksanlik.oneri else "",
            }
        )
    return jsonify({"bloklar": bloklar, "yer_tutucular": veri.yer_tutucular()})


@app.post("/api/bildirim")
def bildirim_olustur():
    veri = _veriyi_al()
    ad = _dosya_adi_temizle(veri.unvan or "Noksanlik Bildirimi")
    dosya_adi = f"{ad} - Noksanlık Bildirimi.docx"

    akis = belge_modulu.bellege_uret(veri)

    # Yerel kurulumda çıktının bir kopyası arşiv olarak saklanır.
    if YEREL:
        damga = datetime.now().strftime("%Y%m%d-%H%M%S")
        kopya = CIKTI_DIZINI / f"{ad} - Noksanlık Bildirimi {damga}.docx"
        kopya.write_bytes(akis.getvalue())

    return send_file(
        akis,
        as_attachment=True,
        download_name=dosya_adi,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

# -*- coding: utf-8 -*-
"""
mevzuat.gov.tr PDF'inden madde metinlerini `data/mevzuat.json` içine aktarır.

Kullanım
--------
    # Kütüphanede kayıtlı maddelerin metnini resmî PDF'ten doldur
    python tools/mevzuat_ice_aktar.py 4857.pdf kanun 4857

    # PDF'teki belirli maddeleri (kütüphanede yoksa ekleyerek) aktar
    python tools/mevzuat_ice_aktar.py 4857.pdf kanun 4857 --maddeler 63,68,41

    # Ne yapılacağını göster, dosyaya yazma
    python tools/mevzuat_ice_aktar.py 4857.pdf kanun 4857 --deneme

PDF'i mevzuat.gov.tr üzerinden indirin:
    Mevzuat Bilgi Sistemi → ilgili mevzuat → sayfanın üstündeki PDF simgesi

Madde numarasında eğik çizgi varsa (``92/2``, ``96/1``) o maddenin ilgili
fıkrası alınır; fıkra sınırı PDF'teki paragraf düzeninden çıkarıldığı için
bu kayıtlar ``dogrulandi = false`` bırakılır ve ekranda ayrıca listelenir.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from core import mevzuat  # noqa: E402
from core.mevzuat_pdf import maddeleri_ayikla  # noqa: E402

# Bakanlık sistemindeki fıkra yazımları: 92/2 · 3/(2) · 6(8) · 13(1)
# Ayraç (eğik çizgi ya da parantez) zorunludur; yoksa "14" gibi iki basamaklı
# madde numaraları yanlışlıkla "1. maddenin 4. fıkrası" diye okunurdu.
FIKRALI = re.compile(r"^(\d+)\s*(?:/\s*\(?(\d+)\)?|\(\s*(\d+)\s*\))$")


def paragraf_kur(atif: str, no: str, baslik: str, metin: str, kapanis: str,
                 fikra: tuple | None = None) -> str:
    """
    Bildirime yazılacak paragrafı kurar.

    ``fikra`` verilirse atıf "63. maddesinin 2. fıkrasında" biçiminde yazılır;
    "63/2. maddesinde" demek Türkçe açısından yanlış olurdu.
    """
    baslik_parcasi = f" **{baslik}** başlıklı" if baslik else ""
    if fikra:
        ana_no, fikra_no = fikra
        yer = f"{ana_no}. maddesinin {fikra_no}. fıkrasında"
    else:
        yer = f"{no}. maddesinde"
    return f'{atif}{baslik_parcasi} {yer}; “{metin}” {kapanis}'


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__,
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
    ayristirici.add_argument("pdf", help="mevzuat.gov.tr'den indirilen PDF")
    ayristirici.add_argument("tur_id", help="kanun | yonetmelik | cbk")
    ayristirici.add_argument("mevzuat_id", help="data/mevzuat.json içindeki mevzuat kimliği")
    ayristirici.add_argument("--maddeler", default="",
                             help="Virgülle ayrılmış madde numaraları; kütüphanede yoksa eklenir")
    ayristirici.add_argument("--kapanis", default="Hükmü amirdir.",
                             help="Paragrafın kapanış kalıbı")
    ayristirici.add_argument("--deneme", action="store_true",
                             help="Değişiklikleri yazmadan göster")
    secenekler = ayristirici.parse_args()

    pdf = Path(secenekler.pdf)
    if not pdf.exists():
        print(f"HATA: PDF bulunamadı: {pdf}", file=sys.stderr)
        return 1

    pdf_maddeleri = maddeleri_ayikla(pdf)
    print(f"PDF'te {len(pdf_maddeleri)} madde bulundu: {pdf.name}")

    veri = mevzuat.agac()
    hedef = mevzuat._mevzuat_bul(veri, secenekler.tur_id, secenekler.mevzuat_id)
    atif = hedef.get("atif", "")
    print(f"Hedef mevzuat  : {hedef['ad']}")
    print(f"Atıf biçimi    : {atif}\n")

    istenen = [m.strip() for m in secenekler.maddeler.split(",") if m.strip()]
    mevcut = {m["no"] for m in hedef["maddeler"]}
    for no in istenen:
        if no not in mevcut:
            hedef["maddeler"].append(
                {"no": no, "baslik": "", "ceza": "", "anahtar": [],
                 "paragraf": "", "dogrulandi": False}
            )

    dolan, atlanan, fikrali = [], [], []
    for kayit in hedef["maddeler"]:
        no = kayit["no"]
        if istenen and no not in istenen:
            continue

        fikra_eslesmesi = FIKRALI.match(no)
        if fikra_eslesmesi:
            ana_no = fikra_eslesmesi.group(1)
            fikra_no = int(fikra_eslesmesi.group(2) or fikra_eslesmesi.group(3))
            kaynak = pdf_maddeleri.get(ana_no)
            if kaynak is None or fikra_no > len(kaynak.fikralar):
                atlanan.append((no, "PDF'te bulunamadı"))
                continue
            metin = kaynak.fikralar[fikra_no - 1]
            baslik = kayit["baslik"] or kaynak.baslik
            dogrulandi = False
            fikra_bilgisi = (ana_no, fikra_no)
            fikrali.append((no, metin))
        else:
            kaynak = pdf_maddeleri.get(no)
            if kaynak is None:
                atlanan.append((no, "PDF'te bulunamadı"))
                continue
            metin = kaynak.metin
            baslik = kayit["baslik"] or kaynak.baslik
            dogrulandi = True
            fikra_bilgisi = None

        kayit["baslik"] = baslik
        kayit["paragraf"] = paragraf_kur(
            atif, no, baslik, metin, secenekler.kapanis, fikra_bilgisi
        )
        kayit["dogrulandi"] = dogrulandi
        dolan.append((no, baslik, len(metin)))

    print(f"Metni dolduruldu: {len(dolan)} madde")
    for no, baslik, uzunluk in dolan:
        isaret = "~" if any(no == f[0] for f in fikrali) else " "
        print(f"  {isaret} m.{no:<8} {baslik[:48]:<48} {uzunluk:>6} karakter")
    if atlanan:
        print(f"\nAtlanan: {len(atlanan)} madde")
        for no, sebep in atlanan:
            print(f"    m.{no:<8} {sebep}")
    if fikrali:
        print("\n~ işaretli kayıtlar fıkra bazlıdır; metni gözden geçirin:")
        for no, metin in fikrali:
            print(f"    m.{no}: {metin[:150]}…")

    if secenekler.deneme:
        print("\n(--deneme) Dosyaya yazılmadı.")
        return 0

    mevzuat.kaydet(veri)
    print(f"\nYazıldı: {mevzuat.DOSYA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

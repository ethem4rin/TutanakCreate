# -*- coding: utf-8 -*-
"""
İşveren Metni (.docx) üreteci — ikinci belge.

Noksanlık bildiriminden ayrı olarak, teftiş tutanağından otomatik çekilen
**işveren vekili beyanını** ("IX-) İşveren vekili … şeklinde ifade etmiştir.")
kapanış cümlesi ve imza bloğu ile birlikte tek sayfalık bir Word belgesine yazar.

Kullanıcının isteği doğrultusunda içerik sadedir: işveren beyanı + imza.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any, Dict, List

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Cm, Pt

PUNTO = 11


@dataclass
class IsverenVerisi:
    beyan: str = ""
    kapanis: str = ""
    mufettis_1: str = ""
    mufettis_2: str = ""
    vekil_adi: str = ""
    vekil_gorevi: str = "İşveren Vekili"

    @classmethod
    def sozlukten(cls, veri: Dict[str, Any]) -> "IsverenVerisi":
        alanlar = {k: (veri.get(k) or "") for k in cls.__dataclass_fields__}
        if not alanlar.get("vekil_gorevi"):
            alanlar["vekil_gorevi"] = "İşveren Vekili"
        return cls(**alanlar)


def _govde_paragrafi(belge, metin: str):
    p = belge.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    pf.line_spacing = 1.5
    pf.first_line_indent = Cm(1.0)
    run = p.add_run(metin)
    run.font.size = Pt(PUNTO)
    return p


def _imza_tablosu(belge, veri: IsverenVerisi) -> None:
    # Sol: müfettiş(ler), Sağ: işveren vekili
    sol_ad = veri.mufettis_1 or veri.mufettis_2 or ""
    sag_ad = veri.vekil_adi or ""

    belge.add_paragraph()  # boşluk
    tablo = belge.add_table(rows=2, cols=2)
    tablo.alignment = WD_TABLE_ALIGNMENT.CENTER
    tablo.autofit = True

    adlar = (sol_ad, sag_ad)
    unvanlar = ("İş Müfettişi", veri.vekil_gorevi or "İşveren Vekili")
    for sutun in range(2):
        hucre_ad = tablo.rows[0].cells[sutun]
        hucre_un = tablo.rows[1].cells[sutun]
        for hucre, deger, kalin in (
            (hucre_ad, adlar[sutun], True),
            (hucre_un, unvanlar[sutun], False),
        ):
            p = hucre.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(deger)
            r.font.size = Pt(PUNTO)
            r.font.bold = kalin


def kur(veri: IsverenVerisi):
    belge = docx.Document()
    # Sayfa düzeni: A4, makul kenar boşlukları
    for bolum in belge.sections:
        bolum.page_height = Cm(29.7)
        bolum.page_width = Cm(21.0)
        bolum.top_margin = Cm(2.5)
        bolum.bottom_margin = Cm(2.5)
        bolum.left_margin = Cm(2.5)
        bolum.right_margin = Cm(2.5)

    # Varsayılan yazı tipi
    stil = belge.styles["Normal"]
    stil.font.size = Pt(PUNTO)

    beyan = (veri.beyan or "").strip()
    if beyan:
        _govde_paragrafi(belge, beyan)
    kapanis = (veri.kapanis or "").strip()
    if kapanis:
        _govde_paragrafi(belge, kapanis)

    _imza_tablosu(belge, veri)
    return belge


def bellege_uret(veri: IsverenVerisi) -> io.BytesIO:
    akis = io.BytesIO()
    kur(veri).save(akis)
    akis.seek(0)
    return akis


# --------------------------------------------------------------------------- #
# Tutanağın sonuna işveren metnini yazan üretim (asıl kullanılan)
# --------------------------------------------------------------------------- #

def _tr_kucuk(metin: str) -> str:
    return (metin or "").replace("I", "ı").replace("İ", "i").lower()


def _paragraf_metnini_degistir(p, yeni: str) -> None:
    """Paragrafın metnini, ilk run'ın biçimini koruyarak değiştirir."""
    yeni = yeni or ""
    if not p.runs:
        p.add_run(yeni)
        return
    p.runs[0].text = yeni
    for r in p.runs[1:]:
        r.text = ""


def tutanaktan_uret(tutanak_kaynak, veri: IsverenVerisi):
    """
    Yüklenen tutanağın KENDİSİNİ açar, içindeki işveren vekili beyanı ve kapanış
    paragraflarını (müfettişin düzenlediği) güncel metinle değiştirir; bulunamazsa
    sona ekler. Böylece çıktı, tüm tutanağı ve sonunda işveren metnini içerir —
    yeni boş bir belge değil.
    """
    belge = docx.Document(tutanak_kaynak)

    beyan = (veri.beyan or "").strip()
    kapanis = (veri.kapanis or "").strip()

    beyan_yazildi = False
    kapanis_yazildi = False
    for p in belge.paragraphs:
        kucuk = _tr_kucuk(p.text)
        if not beyan_yazildi and beyan and "işveren vekili" in kucuk and (
            "ifade etmiştir" in kucuk or "beyan etmiştir" in kucuk or "şeklinde ifade" in kucuk
        ):
            _paragraf_metnini_degistir(p, beyan)
            beyan_yazildi = True
        elif not kapanis_yazildi and kapanis and "iş bu tutanak" in kucuk:
            _paragraf_metnini_degistir(p, kapanis)
            kapanis_yazildi = True

    # Tutanakta işveren beyanı yoksa en sona ekle (+ gerekiyorsa kapanış ve imza).
    if beyan and not beyan_yazildi:
        _govde_paragrafi(belge, beyan)
        if kapanis and not kapanis_yazildi:
            _govde_paragrafi(belge, kapanis)
            kapanis_yazildi = True
        # Tutanakta imza tablosu yoksa ekleyelim.
        if not belge.tables:
            _imza_tablosu(belge, veri)

    return belge


def tutanaktan_bellege(tutanak_kaynak, veri: IsverenVerisi) -> io.BytesIO:
    akis = io.BytesIO()
    tutanaktan_uret(tutanak_kaynak, veri).save(akis)
    akis.seek(0)
    return akis

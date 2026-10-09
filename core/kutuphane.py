# -*- coding: utf-8 -*-
"""
Müfettiş önerisi kütüphanesi.

Kayıtlar ``data/oneri.json`` dosyasında tutulur.
Her kayıt: ``{"id", "baslik", "anahtar": [...], "metin"}``.

Mevzuat maddeleri kademeli bir yapıda tutulduğu için ayrı modüldedir:
bkz. ``core.mevzuat``.

``metin`` alanında hafif biçimlendirme işaretleri kullanılabilir:
``**kalın**`` ve ``__kalın+italik+altı çizili__`` (bkz. ``core.metin``).
"""
from __future__ import annotations

import json
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Dict, List

KOK = Path(__file__).resolve().parent.parent
VERI_DIZINI = KOK / "data"

DOSYALAR = {
    "oneri": VERI_DIZINI / "oneri.json",
}


class KutuphaneHatasi(Exception):
    pass


def _dosya(tur: str) -> Path:
    if tur not in DOSYALAR:
        raise KutuphaneHatasi(f"Bilinmeyen kütüphane türü: {tur}")
    return DOSYALAR[tur]


def yukle(tur: str) -> List[Dict[str, Any]]:
    yol = _dosya(tur)
    if not yol.exists():
        return []
    with yol.open(encoding="utf-8") as kaynak:
        return json.load(kaynak)


def kaydet(tur: str, kayitlar: List[Dict[str, Any]]) -> None:
    yol = _dosya(tur)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with yol.open("w", encoding="utf-8") as hedef:
        json.dump(kayitlar, hedef, ensure_ascii=False, indent=2)
        hedef.write("\n")


def _dogrula(kayit: Dict[str, Any]) -> Dict[str, Any]:
    baslik = (kayit.get("baslik") or "").strip()
    metin = (kayit.get("metin") or "").strip()
    if not baslik:
        raise KutuphaneHatasi("Başlık boş olamaz.")
    if not metin:
        raise KutuphaneHatasi("Metin boş olamaz.")
    anahtar = kayit.get("anahtar") or []
    if isinstance(anahtar, str):
        anahtar = [p.strip() for p in anahtar.split(",")]
    return {
        "id": (kayit.get("id") or "").strip() or uuid.uuid4().hex[:10],
        "baslik": baslik,
        "anahtar": [a.strip() for a in anahtar if (a or "").strip()],
        "metin": metin,
    }


def ekle(tur: str, kayit: Dict[str, Any]) -> Dict[str, Any]:
    kayitlar = yukle(tur)
    yeni = _dogrula(kayit)
    if any(k["id"] == yeni["id"] for k in kayitlar):
        yeni["id"] = uuid.uuid4().hex[:10]
    kayitlar.append(yeni)
    kaydet(tur, kayitlar)
    return yeni


def guncelle(tur: str, kayit_id: str, kayit: Dict[str, Any]) -> Dict[str, Any]:
    kayitlar = yukle(tur)
    for sira, mevcut in enumerate(kayitlar):
        if mevcut["id"] == kayit_id:
            yeni = _dogrula({**kayit, "id": kayit_id})
            kayitlar[sira] = yeni
            kaydet(tur, kayitlar)
            return yeni
    raise KutuphaneHatasi(f"Kayıt bulunamadı: {kayit_id}")


def sil(tur: str, kayit_id: str) -> None:
    kayitlar = yukle(tur)
    kalanlar = [k for k in kayitlar if k["id"] != kayit_id]
    if len(kalanlar) == len(kayitlar):
        raise KutuphaneHatasi(f"Kayıt bulunamadı: {kayit_id}")
    kaydet(tur, kalanlar)


# --------------------------------------------------------------------------- #
# Noksanlık metnine göre öneri sıralaması
# --------------------------------------------------------------------------- #

def _normalize(metin: str) -> str:
    metin = metin.replace("I", "ı").replace("İ", "i").lower()
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(k for k in metin if not unicodedata.combining(k))
    cevrim = str.maketrans("çğıöşü", "cgiosu")
    return re.sub(r"\s+", " ", metin.translate(cevrim))


def puanla(tur: str, noksanlik_metni: str) -> List[Dict[str, Any]]:
    """
    Noksanlık metnine göre kütüphane kayıtlarını ilgi puanına göre sıralar.

    Puan, kaydın anahtar kelimelerinden kaçının noksanlık metninde geçtiğiyle
    belirlenir. Puanı 0 olan kayıtlar da listede kalır (müfettiş yine de
    seçebilsin diye), yalnızca sona alınır.
    """
    hedef = _normalize(noksanlik_metni or "")
    sonuc = []
    for kayit in yukle(tur):
        puan = 0
        for anahtar in kayit.get("anahtar", []):
            if _normalize(anahtar) in hedef:
                puan += 1
        sonuc.append({**kayit, "puan": puan})
    sonuc.sort(key=lambda k: (-k["puan"], k["baslik"]))
    return sonuc

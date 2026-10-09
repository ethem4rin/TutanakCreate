# -*- coding: utf-8 -*-
"""
Mevzuat kütüphanesi — kademeli yapı.

Bakanlığın "Dayanak Seç" ekranındaki düzeni izler::

    Mevzuat Türü  ->  Mevzuat  ->  Madde  (+ Ceza Maddesi)

``data/mevzuat.json`` yapısı::

    {
      "surum": 2,
      "turler": [
        {"id": "kanun", "ad": "Kanun", "mevzuat": [
            {"id": "4857", "ad": "4857 - İş Kanunu",
             "atif": "4857 sayılı İş Kanunu'nun",
             "maddeler": [
               {"no": "63", "baslik": "Çalışma Süresi", "ceza": "104",
                "anahtar": ["çalışma süresi", …],
                "paragraf": "…bildirime yazılacak tam metin…",
                "dogrulandi": true}
             ]}
        ]}
      ]
    }

``paragraf`` boşsa madde henüz doldurulmamıştır; arayüzde seçilemez, yalnızca
düzenlenebilir. ``dogrulandi`` yalnızca örnek bildirimden birebir alınan
maddelerde ``True``'dur.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

KOK = Path(__file__).resolve().parent.parent
DOSYA = KOK / "data" / "mevzuat.json"

AYRAC = "|"


class MevzuatHatasi(Exception):
    pass


# --------------------------------------------------------------------------- #
# Okuma / yazma
# --------------------------------------------------------------------------- #

def agac() -> Dict[str, Any]:
    if not DOSYA.exists():
        return {"surum": 2, "turler": []}
    with DOSYA.open(encoding="utf-8") as kaynak:
        return json.load(kaynak)


def kaydet(veri: Dict[str, Any]) -> None:
    DOSYA.parent.mkdir(parents=True, exist_ok=True)
    with DOSYA.open("w", encoding="utf-8") as hedef:
        json.dump(veri, hedef, ensure_ascii=False, indent=2)
        hedef.write("\n")


def _tur_bul(veri: Dict[str, Any], tur_id: str) -> Dict[str, Any]:
    for tur in veri["turler"]:
        if tur["id"] == tur_id:
            return tur
    raise MevzuatHatasi(f"Mevzuat türü bulunamadı: {tur_id}")


def _mevzuat_bul(veri: Dict[str, Any], tur_id: str, mevzuat_id: str) -> Dict[str, Any]:
    for mevzuat in _tur_bul(veri, tur_id)["mevzuat"]:
        if mevzuat["id"] == mevzuat_id:
            return mevzuat
    raise MevzuatHatasi(f"Mevzuat bulunamadı: {mevzuat_id}")


# --------------------------------------------------------------------------- #
# Listeleme
# --------------------------------------------------------------------------- #

def madde_kimligi(tur_id: str, mevzuat_id: str, no: str) -> str:
    return AYRAC.join((tur_id, mevzuat_id, no))


def kimligi_coz(kimlik: str) -> Tuple[str, str, str]:
    parcalar = kimlik.split(AYRAC)
    if len(parcalar) != 3:
        raise MevzuatHatasi(f"Geçersiz madde kimliği: {kimlik}")
    return parcalar[0], parcalar[1], parcalar[2]


def agaci_listele() -> List[Dict[str, Any]]:
    """Arayüzün kademeli seçicisi için tür/mevzuat/madde ağacını döndürür."""
    veri = agac()
    cikti = []
    for tur in veri["turler"]:
        mevzuatlar = []
        for mevzuat in tur["mevzuat"]:
            maddeler = [
                {
                    "kimlik": madde_kimligi(tur["id"], mevzuat["id"], m["no"]),
                    "no": m["no"],
                    "baslik": m.get("baslik", ""),
                    "ceza": m.get("ceza", ""),
                    "anahtar": m.get("anahtar", []),
                    "paragraf": m.get("paragraf", ""),
                    "dolu": bool(m.get("paragraf")),
                    "dogrulandi": bool(m.get("dogrulandi")),
                }
                for m in mevzuat["maddeler"]
            ]
            mevzuatlar.append(
                {
                    "id": mevzuat["id"],
                    "ad": mevzuat["ad"],
                    "atif": mevzuat.get("atif", ""),
                    "madde_sayisi": len(maddeler),
                    "dolu_sayisi": sum(1 for m in maddeler if m["dolu"]),
                    "maddeler": maddeler,
                }
            )
        cikti.append(
            {
                "id": tur["id"],
                "ad": tur["ad"],
                "mevzuat_sayisi": len(mevzuatlar),
                "mevzuat": mevzuatlar,
            }
        )
    return cikti


def duzlestir() -> List[Dict[str, Any]]:
    """Tüm maddeleri tek düzeyli listeye indirger."""
    duz = []
    for tur in agaci_listele():
        for mevzuat in tur["mevzuat"]:
            for m in mevzuat["maddeler"]:
                duz.append(
                    {
                        **m,
                        "tur_id": tur["id"],
                        "tur_ad": tur["ad"],
                        "mevzuat_id": mevzuat["id"],
                        "mevzuat_ad": mevzuat["ad"],
                    }
                )
    return duz


def madde_getir(kimlik: str) -> Optional[Dict[str, Any]]:
    for m in duzlestir():
        if m["kimlik"] == kimlik:
            return m
    return None


# --------------------------------------------------------------------------- #
# Noksanlık metnine göre ilgi sıralaması
# --------------------------------------------------------------------------- #

def _normalize(metin: str) -> str:
    metin = metin.replace("I", "ı").replace("İ", "i").lower()
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(k for k in metin if not unicodedata.combining(k))
    return re.sub(r"\s+", " ", metin.translate(str.maketrans("çğıöşü", "cgiosu")))


def oner(noksanlik_metni: str, limit: int = 12) -> List[Dict[str, Any]]:
    """
    Noksanlık metnindeki anahtar kelimelere göre en ilgili maddeleri döndürür.

    Yalnızca metni doldurulmuş maddeler önerilir; puanı sıfır olanlar listeye
    girmez (kademeli seçiciden zaten ulaşılabiliyorlar).
    """
    hedef = _normalize(noksanlik_metni or "")
    if not hedef:
        return []
    puanlilar = []
    for m in duzlestir():
        if not m["dolu"]:
            continue
        puan = sum(1 for a in m["anahtar"] if _normalize(a) in hedef)
        if puan:
            puanlilar.append({**m, "puan": puan})
    puanlilar.sort(key=lambda m: (-m["puan"], m["mevzuat_ad"], m["no"]))
    return puanlilar[:limit]


# --------------------------------------------------------------------------- #
# Düzenleme
# --------------------------------------------------------------------------- #

def varsayilan_paragraf(atif: str, no: str, baslik: str, alinti: str,
                        kapanis: str = "Hükmü amirdir.") -> str:
    """Yeni madde eklenirken kullanılacak hazır paragraf kalıbı."""
    baslik_parcasi = f" **{baslik}** başlıklı" if baslik.strip() else ""
    return f'{atif}{baslik_parcasi} {no}. maddesinde; “{alinti.strip()}” {kapanis}'


def _madde_dogrula(govde: Dict[str, Any]) -> Dict[str, Any]:
    no = str(govde.get("no") or "").strip()
    if not no:
        raise MevzuatHatasi("Madde numarası boş olamaz.")
    anahtar = govde.get("anahtar") or []
    if isinstance(anahtar, str):
        anahtar = [p.strip() for p in anahtar.split(",")]
    return {
        "no": no,
        "baslik": (govde.get("baslik") or "").strip(),
        "ceza": (govde.get("ceza") or "").strip(),
        "anahtar": [a.strip() for a in anahtar if (a or "").strip()],
        "paragraf": (govde.get("paragraf") or "").strip(),
        "dogrulandi": bool(govde.get("dogrulandi")),
    }


def madde_kaydet(tur_id: str, mevzuat_id: str, govde: Dict[str, Any],
                 eski_no: str = "") -> Dict[str, Any]:
    """Maddeyi ekler ya da (``eski_no`` verilmişse) günceller."""
    veri = agac()
    mevzuat = _mevzuat_bul(veri, tur_id, mevzuat_id)
    yeni = _madde_dogrula(govde)

    hedef_no = eski_no or yeni["no"]
    for sira, mevcut in enumerate(mevzuat["maddeler"]):
        if mevcut["no"] == hedef_no:
            mevzuat["maddeler"][sira] = yeni
            kaydet(veri)
            return {**yeni, "kimlik": madde_kimligi(tur_id, mevzuat_id, yeni["no"])}

    if any(m["no"] == yeni["no"] for m in mevzuat["maddeler"]):
        raise MevzuatHatasi(f"Bu mevzuatta {yeni['no']} numaralı madde zaten var.")
    mevzuat["maddeler"].append(yeni)
    kaydet(veri)
    return {**yeni, "kimlik": madde_kimligi(tur_id, mevzuat_id, yeni["no"])}


def madde_sil(tur_id: str, mevzuat_id: str, no: str) -> None:
    veri = agac()
    mevzuat = _mevzuat_bul(veri, tur_id, mevzuat_id)
    kalanlar = [m for m in mevzuat["maddeler"] if m["no"] != no]
    if len(kalanlar) == len(mevzuat["maddeler"]):
        raise MevzuatHatasi(f"Madde bulunamadı: {no}")
    mevzuat["maddeler"] = kalanlar
    kaydet(veri)


def mevzuat_kaydet(tur_id: str, govde: Dict[str, Any], eski_id: str = "") -> Dict[str, Any]:
    """Yeni kanun/yönetmelik ekler ya da mevcudunu günceller."""
    veri = agac()
    tur = _tur_bul(veri, tur_id)
    ad = (govde.get("ad") or "").strip()
    atif = (govde.get("atif") or "").strip()
    if not ad:
        raise MevzuatHatasi("Mevzuat adı boş olamaz.")
    if not atif:
        raise MevzuatHatasi("Atıf biçimi boş olamaz (örn. “4857 sayılı İş Kanunu'nun”).")

    if eski_id:
        for mevzuat in tur["mevzuat"]:
            if mevzuat["id"] == eski_id:
                mevzuat["ad"] = ad
                mevzuat["atif"] = atif
                kaydet(veri)
                return mevzuat
        raise MevzuatHatasi(f"Mevzuat bulunamadı: {eski_id}")

    kimlik = re.sub(r"[^a-z0-9]+", "-", _normalize(ad)).strip("-")[:40] or "mevzuat"
    mevcut = {m["id"] for m in tur["mevzuat"]}
    sayac = 2
    temel = kimlik
    while kimlik in mevcut:
        kimlik = f"{temel}-{sayac}"
        sayac += 1

    yeni = {"id": kimlik, "ad": ad, "atif": atif, "maddeler": []}
    tur["mevzuat"].append(yeni)
    kaydet(veri)
    return yeni

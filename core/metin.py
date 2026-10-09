# -*- coding: utf-8 -*-
"""
Kütüphane metinlerinde kullanılan hafif biçimlendirme işaretlerini çözümler.

İşaretler
---------
``**metin**``  -> kalın
``__metin__``  -> kalın + italik + altı çizili  (örn. "Buna göre;")

Çözümleme sonucu ``Parca`` listesidir; Word üreteci bu listeyi doğrudan
run'lara dönüştürür.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

ISARET = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.DOTALL)


@dataclass
class Parca:
    metin: str
    kalin: bool = False
    italik: bool = False
    alti_cizili: bool = False


def cozumle(metin: str) -> List[Parca]:
    """Biçimlendirme işaretli metni ``Parca`` listesine çevirir."""
    parcalar: List[Parca] = []
    son = 0
    for eslesme in ISARET.finditer(metin):
        if eslesme.start() > son:
            parcalar.append(Parca(metin[son:eslesme.start()]))
        if eslesme.group(1) is not None:
            parcalar.append(Parca(eslesme.group(1), kalin=True))
        else:
            parcalar.append(
                Parca(eslesme.group(2), kalin=True, italik=True, alti_cizili=True)
            )
        son = eslesme.end()
    if son < len(metin):
        parcalar.append(Parca(metin[son:]))
    return [p for p in parcalar if p.metin] or [Parca("")]


def duz_metin(metin: str) -> str:
    """İşaretleri kaldırıp yalnızca okunabilir metni döndürür."""
    return ISARET.sub(lambda m: m.group(1) or m.group(2) or "", metin)


def html_onizleme(metin: str) -> str:
    """Arayüzde göstermek için güvenli HTML üretir."""
    from html import escape

    cikti = []
    for parca in cozumle(metin):
        govde = escape(parca.metin).replace("\n", "<br>")
        if parca.alti_cizili:
            cikti.append(f"<u><em><strong>{govde}</strong></em></u>")
        elif parca.kalin:
            cikti.append(f"<strong>{govde}</strong>")
        else:
            cikti.append(govde)
    return "".join(cikti)

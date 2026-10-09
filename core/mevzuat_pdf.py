# -*- coding: utf-8 -*-
"""
mevzuat.gov.tr PDF'lerinden madde metinlerini ayıklar.

mevzuat.gov.tr iki ayrı PDF biçimi sunar; ayıklayıcı ikisini de tanır ve
hangisinin daha çok madde çıkardığına bakarak kendisi seçer:

* **Girintili** (kanun metinleri) — fıkranın ilk satırı içeriden (x ≈ 106 pt),
  devam satırları dışarıdan (x ≈ 71 pt) başlar. Fıkra sınırı girintiden belli
  olur.
* **Akış** (HTML'den üretilen yönetmelik metinleri) — girinti yoktur; fıkra
  sınırı, satırın sağ kenara ulaşmadan bitmesinden (tırtıklı satır) anlaşılır.

Her iki biçimde de madde başlığı, "Madde N -" satırının hemen üstündeki kısa
paragraftır.

Metinden temizlenenler:
  * dipnotlar (gövdeden küçük puntoyla dizilir) ve dipnot numaraları
  * ortalanmış bölüm/kısım başlıkları
  * sayfa numaraları
  * "(Ek cümle: 10/9/2014-6552/7 md.)" gibi değişiklik şerhleri
  * tamamı mülga olan fıkralar
"""
from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import fitz

# Girinti eşiği: bunun üstünde başlayan satır yeni fıkra/başlık demektir.
GIRINTI_ESIGI = 90.0
# Ortalanmış (bölüm başlığı) kabul edilen sol kenar.
ORTA_ESIGI = 150.0
# Gövde puntosu belgeden belgeye değişir (kanunlarda 12, yönetmeliklerde 10,2);
# eşik, belgenin baskın puntosundan bu kadar düşük olanları dipnot sayar.
PUNTO_PAYI = 0.6

MADDE_BASI = re.compile(
    r"^(?:(Ek|Geçici|EK|GEÇİCİ)\s+)?(?:Madde|MADDE)\s+"
    r"(\d+(?:/[A-Za-zÇĞİÖŞÜçğıöşü]+)?)\s*[-–—]\s*(.*)$"
)
# Akış biçiminde fıkra sonu: satır, sağ kenarın bu kadar gerisinde bitiyorsa.
TIRTIK_ESIGI = 18.0
# "(Ek cümle: 10/9/2014-6552/7 md.)", "(Değişik: 4/4/2015-6645/36 md.)" …
SERH = re.compile(
    r"\(\s*(?:Ek|Değişik|Mülga|İptal|Yeniden düzenleme)[^()]*?\d{1,2}/\d{1,2}/\d{4}[^()]*?\)\s*"
)
# Cümle sonuna yapışmış dipnot numarası: "sayılmaz.19"
DIPNOT_NO = re.compile(r"(?<=[.\)\]”\"])\d{1,2}(?=\s|$)")
SAYFA_NO = re.compile(r"^\s*\d{1,4}\s*$")
# Punto süzgecinden kaçan dipnotlara karşı ikinci savunma hattı:
# "15 4/4/2015 tarihli ve 6645 sayılı Kanunun 34 üncü maddesiyle…"
# Baştaki dipnot numarası zorunludur; yoksa gövde metnindeki "… 17/7/1964
# tarihli ve 506 sayılı Kanun …" gibi göndermeler yanlışlıkla silinirdi.
DIPNOT_SATIRI = re.compile(
    r"^\d{1,2}\s+\d{1,2}/\d{1,2}/\d{4}\s+tarihli\s+ve\s+\d+\s+sayılı\s+"
)
# Madde başlığına yapışan dipnot numaraları: "Yetkili makam ve memurlar28"
BASLIK_DIPNOTU = re.compile(r"\d+$")
# "İKİNCİ BÖLÜM", "ÜÇÜNCÜ KISIM" gibi yapı başlıkları
BOLUM_BASLIGI = re.compile(
    r"^(?:BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|ALTINCI|YEDİNCİ|SEKİZİNCİ|"
    r"DOKUZUNCU|ONUNCU|ON\s*\w+)\s+(?:BÖLÜM|KISIM|AYIRIM)\s*$",
    re.IGNORECASE,
)


@dataclass
class Madde:
    no: str
    baslik: str
    fikralar: List[str] = field(default_factory=list)

    @property
    def metin(self) -> str:
        return " ".join(self.fikralar)


def _satirlari_topla(pdf_yolu: str | Path) -> List[tuple]:
    """PDF'ten (x0, punto, metin) üçlüleri döndürür."""
    satirlar = []
    with fitz.open(str(pdf_yolu)) as belge:
        for sayfa in belge:
            for blok in sayfa.get_text("dict")["blocks"]:
                for satir in blok.get("lines", []):
                    parcalar = satir.get("spans", [])
                    if not parcalar:
                        continue
                    metin = "".join(p["text"] for p in parcalar).strip()
                    if not metin:
                        continue
                    # Satırın puntosu, en çok karakteri taşıyan parçanınkidir;
                    # böylece dipnot numarasının üst simge puntosu yanıltmaz.
                    baskin = max(parcalar, key=lambda p: len(p["text"]))
                    satirlar.append(
                        (satir["bbox"][0], satir["bbox"][2], baskin["size"], metin)
                    )
    return satirlar


def _govde_puntosu(satirlar: List[tuple]) -> float:
    """Belgenin baskın (en çok karakter taşıyan) yazı puntosu."""
    sayac: collections.Counter = collections.Counter()
    for _x0, _x1, punto, metin in satirlar:
        sayac[round(punto, 1)] += len(metin)
    return sayac.most_common(1)[0][0] if sayac else 0.0


def _ayikla_gurultu(satirlar: List[tuple], orta_ele: bool) -> List[tuple]:
    """Dipnotları, sayfa numaralarını ve ortalanmış başlıkları atar."""
    esik = _govde_puntosu(satirlar) - PUNTO_PAYI
    temiz = []
    for x0, x1, punto, metin in satirlar:
        if punto < esik:                  # dipnot
            continue
        if SAYFA_NO.match(metin):         # sayfa numarası
            continue
        if DIPNOT_SATIRI.match(metin):    # puntodan kaçan dipnot
            continue
        if orta_ele and x0 > ORTA_ESIGI:  # ortalanmış bölüm başlığı
            continue
        if BOLUM_BASLIGI.match(metin):    # "İKİNCİ BÖLÜM" vb.
            continue
        temiz.append((x0, x1, punto, metin))
    return temiz


def _paragraflar_girintili(satirlar: List[tuple]) -> List[str]:
    """Kanun PDF'leri: fıkra sınırını ilk satırın girintisi belirler."""
    paragraflar: List[str] = []
    for x0, _x1, _punto, metin in _ayikla_gurultu(satirlar, orta_ele=True):
        if x0 >= GIRINTI_ESIGI or not paragraflar:
            paragraflar.append(metin)
        else:
            paragraflar[-1] += " " + metin
    return paragraflar


def _paragraflar_akis(satirlar: List[tuple]) -> List[str]:
    """Yönetmelik PDF'leri: fıkra sınırını satırın erken bitmesi belirler."""
    temiz = _ayikla_gurultu(satirlar, orta_ele=False)
    if not temiz:
        return []
    sag_kenar = max(x1 for _x0, x1, _p, _m in temiz)

    paragraflar: List[str] = []
    yeni_paragraf = True
    for _x0, x1, _punto, metin in temiz:
        if yeni_paragraf or not paragraflar:
            paragraflar.append(metin)
        else:
            paragraflar[-1] += " " + metin
        yeni_paragraf = x1 < sag_kenar - TIRTIK_ESIGI
    return paragraflar


def _temizle(metin: str) -> str:
    metin = SERH.sub("", metin)
    metin = DIPNOT_NO.sub("", metin)
    metin = metin.replace("­", "")               # yumuşak tire
    metin = re.sub(r"\s+", " ", metin)
    return metin.strip()


def _serh_mi(metin: str) -> bool:
    """Tamamı değişiklik şerhinden ibaret fıkra mı?"""
    return not SERH.sub("", metin).strip(" ().")


def _maddeleri_kur(paragraflar: List[str]) -> Dict[str, Madde]:

    # Madde başlangıçlarının paragraf indeksleri
    bas_indeksleri = [
        (sira, MADDE_BASI.match(p))
        for sira, p in enumerate(paragraflar)
        if MADDE_BASI.match(p)
    ]

    maddeler: Dict[str, Madde] = {}
    for yer, (indeks, eslesme) in enumerate(bas_indeksleri):
        onek, no, ilk_fikra = eslesme.group(1), eslesme.group(2), eslesme.group(3)
        anahtar = f"{onek} {no}".strip() if onek else no

        # Madde başlığı, "Madde N -" satırının hemen üstündeki kısa paragraftır.
        baslik = ""
        if indeks > 0:
            aday = paragraflar[indeks - 1]
            if len(aday) < 120 and not MADDE_BASI.match(aday) and not aday.endswith("."):
                baslik = BASLIK_DIPNOTU.sub("", _temizle(aday)).strip()

        # Sonraki maddenin başlığına kadar olan fıkralar bu maddeye aittir.
        son = len(paragraflar)
        if yer + 1 < len(bas_indeksleri):
            sonraki = bas_indeksleri[yer + 1][0]
            son = sonraki - 1 if sonraki - 1 > indeks else sonraki

        fikralar = []
        for ham in [ilk_fikra] + paragraflar[indeks + 1:son]:
            if not ham.strip() or _serh_mi(ham):
                continue
            temiz = _temizle(ham)
            if temiz:
                fikralar.append(temiz)

        # Maddenin sonunda kalan kısa, noktayla bitmeyen paragraflar bir
        # sonraki bölümün başlığıdır ("Genel Hükümler" gibi) — metne girmesin.
        while fikralar and len(fikralar[-1]) < 60 and not fikralar[-1].endswith((".", ";", ":")):
            fikralar.pop()

        if fikralar:
            maddeler[anahtar] = Madde(no=anahtar, baslik=baslik, fikralar=fikralar)

    return maddeler


def maddeleri_ayikla(pdf_yolu: str | Path, kip: str = "oto") -> Dict[str, Madde]:
    """
    PDF'teki maddeleri ``{madde_no: Madde}`` olarak döndürür.

    ``kip`` değerleri: ``"girintili"`` (kanun metinleri), ``"akis"``
    (HTML'den üretilen yönetmelik metinleri) ya da ``"oto"`` — ikisini de
    dener, daha çok madde çıkaranı seçer.
    """
    satirlar = _satirlari_topla(pdf_yolu)

    if kip == "girintili":
        return _maddeleri_kur(_paragraflar_girintili(satirlar))
    if kip == "akis":
        return _maddeleri_kur(_paragraflar_akis(satirlar))

    girintili = _maddeleri_kur(_paragraflar_girintili(satirlar))
    akis = _maddeleri_kur(_paragraflar_akis(satirlar))
    # Eşitlikte girintili kip yeğlenir: kanun PDF'lerinde fıkra sınırlarını
    # girinti, tırtıklı satır kuralından daha güvenilir belirler.
    return girintili if len(girintili) >= len(akis) else akis

# -*- coding: utf-8 -*-
"""
`data/mevzuat.json` ağacının **iskeletini** kurar.

Yapı, Bakanlığın "Dayanak Seç" ekranındaki kademeli düzeni izler:

    Mevzuat Türü  ->  Mevzuat  ->  Madde  (+ Ceza Maddesi)

Bu betik yalnızca mevzuat listesini, madde numaralarını, ceza maddelerini ve
arama anahtar kelimelerini yazar. **Madde metinleri buraya yazılmaz**; onlar
mevzuat.gov.tr PDF'lerinden `tools/mevzuat_ice_aktar.py` ile alınır:

    python tools/mevzuat_kur.py                                   # iskelet
    python tools/mevzuat_ice_aktar.py 4857.pdf kanun 4857         # metinler

Böylece kütüphanedeki her metnin kaynağı resmî yayın olur.

DİKKAT: Bu betik `data/mevzuat.json` dosyasını sıfırdan yazar; elle yapılmış
düzenlemeler ve içe aktarılmış metinler silinir.
"""
from __future__ import annotations

import json
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
HEDEF = KOK / "data" / "mevzuat.json"


def madde(no: str, anahtar=(), ceza: str = "") -> dict:
    return {"no": no, "baslik": "", "ceza": ceza, "anahtar": list(anahtar),
            "paragraf": "", "dogrulandi": False}


# --------------------------------------------------------------------------- #
# 4857 sayılı İş Kanunu — Bakanlık "Dayanak Seç" listesindeki maddeler
# Anahtar kelimeler, noksanlık metnine göre otomatik öneri sıralaması içindir.
# --------------------------------------------------------------------------- #

IS_KANUNU = [
    madde("3", ["işyeri bildirimi", "işyeri bildirme", "bölge müdürlüğü"]),
    madde("5", ["eşit davranma", "ayrımcılık", "cinsiyet", "gebelik"]),
    madde("7", ["geçici iş ilişkisi", "özel istihdam bürosu"]),
    madde("8", ["iş sözleşmesi", "yazılı sözleşme", "sözleşme sureti", "imza", "kaşe"]),
    madde("14", ["çağrı üzerine çalışma", "uzaktan çalışma", "kısmi süreli"]),
    madde("28", ["çalışma belgesi"]),
    madde("29", ["toplu işçi çıkarma", "toplu çıkarma"]),
    madde("30", ["engelli", "eski hükümlü", "kontenjan"]),
    madde("32", ["ücret", "ücret ödemesi", "ayda bir", "banka", "ödenmemiş ücret"]),
    madde("37", ["ücret hesap pusulası", "bordro", "kesinti", "tahakkuk"]),
    madde("38", ["ücret kesme cezası"]),
    madde("39", ["asgari ücret"]),
    madde("41", ["fazla çalışma ücreti", "yüzde elli", "%50", "270 saat", "zamlı ücret"]),
    madde("46", ["hafta tatili", "yirmidört saat", "kesintisiz dinlenme", "yedi günlük"]),
    madde("46/2", ["çalışılmayan hafta tatili", "bir iş karşılığı olmaksızın"]),
    madde("47", ["ulusal bayram", "genel tatil", "yevmiye"]),
    madde("52", ["yüzde bordrosu", "yüzde usulü"]),
    madde("53", ["yıllık izin", "yıllık ücretli izin", "14 gün", "20 gün", "26 gün", "50 yaş"]),
    madde("54", ["izne hak kazanma", "hizmet süresi birleştirme", "mevsimlik"]),
    madde("56", ["izin bölünmesi", "on günden aşağı", "yıllık izin kullandırma"]),
    madde("57", ["izin ücreti", "peşin ödeme", "avans"]),
    madde("60", ["izin yönetmeliği", "izin kaydı"]),
    madde("63", ["çalışma süresi", "haftalık 45 saat", "kırkbeş", "fazla çalışma",
                 "vardiya", "haftada 50 saat"]),
    madde("63/2", ["denkleştirme", "günlük 11 saat", "onbir saat", "haftalık ortalama"]),
    madde("64", ["telafi çalışması", "telafi"]),
    madde("68", ["ara dinlenme", "ara dinlenmesi", "mola", "yedibuçuk saat"]),
    madde("69", ["gece çalışması", "gece süresi", "20.00", "06.00", "gece postası"]),
    madde("72", ["yer altı", "su altı", "maden"]),
    madde("73", ["çocuk işçi", "genç işçi", "gece çalıştırma yasağı"]),
    madde("74", ["analık izni", "doğum", "süt izni", "gebelik", "kadın çalışan", "emzirme"]),
    madde("75", ["özlük dosyası", "özlük", "belge saklama"]),
    madde("92/2", ["teftiş", "bilgi verme", "müfettiş"]),
    madde("96/1", ["ifade", "telkin", "gerçeği saklama"]),
    madde("96/2", ["gerçeğe uygun olmayan haber", "şikayet"]),
]

KANUNLAR = [
    ("4857", "4857 - İş Kanunu", "4857 sayılı İş Kanunu'nun", IS_KANUNU),
    ("6331", "6331 - İş Sağlığı ve Güvenliği Kanunu",
     "6331 sayılı İş Sağlığı ve Güvenliği Kanunu'nun", []),
    ("6735", "6735 - Uluslararası İşgücü Kanunu",
     "6735 sayılı Uluslararası İşgücü Kanunu'nun", []),
    ("6356", "6356 - Sendikalar ve Toplu İş Sözleşmesi Kanunu",
     "6356 sayılı Sendikalar ve Toplu İş Sözleşmesi Kanunu'nun", []),
    ("5544", "5544 - Mesleki Yeterlilik Kurumu Kanunu",
     "5544 sayılı Mesleki Yeterlilik Kurumu Kanunu'nun", []),
    ("4447", "4447 - İşsizlik Sigortası Kanunu",
     "4447 sayılı İşsizlik Sigortası Kanunu'nun", []),
    ("4632", "4632 - Bireysel Emeklilik Tasarruf ve Yatırım Sistemi Kanunu",
     "4632 sayılı Bireysel Emeklilik Tasarruf ve Yatırım Sistemi Kanunu'nun", []),
    ("4904", "4904 - Türkiye İş Kurumu Kanunu",
     "4904 sayılı Türkiye İş Kurumu Kanunu'nun", []),
    ("854", "854 - Deniz İş Kanunu", "854 sayılı Deniz İş Kanunu'nun", []),
]

# Yönetmeliklerde ceza maddesi 4857/104'tür. Madde girdisi ya düz numaradır
# ya da (numara, anahtar kelimeler) ikilisidir.
YONETMELIKLER = [
    ("uzaktan-calisma", "Uzaktan Çalışma Yönetmeliği",
     "Uzaktan Çalışma Yönetmeliği'nin",
     ["5", "7", "11", "12", "13"]),
    ("yillik-izin", "Yıllık Ücretli İzin Yönetmeliği",
     "Yıllık Ücretli İzin Yönetmeliği'nin",
     [("6/(2)", ["izin kullandırma", "sürekli izin", "bölünemez"]),
      ("6/(4)", ["mahsup", "diğer izinler", "hastalık izni"]),
      ("6/(5)", ["ulusal bayram", "hafta tatili", "izin süresine rastlayan"]),
      ("6/(6)", ["yol izni", "başka yerde geçirme"]),
      ("6/(7)", ["bildirim süresi", "fesih", "izin süresi"]),
      ("6(8)", ["izin kayıt belgesi", "yıllık izin kaydı", "izin defteri"]),
      ("6/(9)", ["alt işveren", "aynı işyeri", "izin süresi"]),
      ("13(1)", ["kısmi süreli", "çağrı üzerine", "yıllık izin"]),
      ("13(2)", ["kısmi süreli", "çağrı üzerine", "izin kullandırma"]),
      ("15", ["izin kurulu", "yüzden fazla işçi"]),
      ("21(2)", ["izin ücreti", "peşin ödeme", "izin dönemi ücreti"])]),
    ("calisma-sureleri", "İş Kanununa İlişkin Çalışma Süreleri Yönetmeliği",
     "İş Kanununa İlişkin Çalışma Süreleri Yönetmeliği'nin",
     [("3/(2)", ["ara dinlenme", "kesintisiz oniki saat", "yirmidört saat", "dinlenme süresi"]),
      ("7/(3)", ["telafi çalışması", "zorunlu neden"]),
      ("9", ["çalışma süresinin belgelenmesi", "puantaj", "çalışma süresi kaydı"])]),
    ("cocuk-genc-isci",
     "Çocuk ve Genç İşçilerin Çalıştırılma Usul ve Esasları Hakkında Yönetmelik",
     "Çocuk ve Genç İşçilerin Çalıştırılma Usul ve Esasları Hakkında Yönetmeliğin",
     ["5", "6", "8", "9", "10", "11"]),
    ("kadin-gece-postasi",
     "Kadın Çalışanların Gece Postalarında Çalıştırılma Koşulları Hakkında Yönetmelik",
     "Kadın Çalışanların Gece Postalarında Çalıştırılma Koşulları Hakkında Yönetmeliğin",
     ["5", "6", "9"]),
    ("postalar-halinde",
     "Postalar Halinde İşçi Çalıştırılarak Yürütülen İşlerde Çalışmalara İlişkin "
     "Özel Usul ve Esaslar Hakkında Yönetmelik",
     "Postalar Halinde İşçi Çalıştırılarak Yürütülen İşlerde Çalışmalara İlişkin "
     "Özel Usul ve Esaslar Hakkında Yönetmeliğin",
     ["3", "4", "5", "6", "7", "8", "9", "10", "11"]),
    ("haftalik-bolunemeyen", "Haftalık İş Günlerine Bölünemeyen Çalışma Süreleri Yönetmeliği",
     "Haftalık İş Günlerine Bölünemeyen Çalışma Süreleri Yönetmeliği'nin",
     ["4", "5", "6", "7", "8", "9", "15", "16"]),
    ("fazla-calisma",
     "İş Kanununa İlişkin Fazla Çalışma ve Fazla Sürelerle Çalışma Yönetmeliği",
     "İş Kanunu'na İlişkin Fazla Çalışma ve Fazla Sürelerle Çalışma Yönetmeliği'nin",
     [("5", ["yarım saat", "fazla çalışma hesabı", "yuvarlama", "270 saat",
             "ikiyüzyetmiş"]),
      ("9", ["fazla çalışma onayı", "yazılı onay", "muvafakat"])]),
    ("gemi-adamlari", "Gemi Adamlarının İkamet Yerleri, Sağlık ve İaşelerine Dair Yönetmelik",
     "Gemi Adamlarının İkamet Yerleri, Sağlık ve İaşelerine Dair Yönetmeliğin", []),
    ("bes", "Bireysel Emeklilik Sistemi Hakkında Yönetmelik",
     "Bireysel Emeklilik Sistemi Hakkında Yönetmeliğin", []),
    ("otomatik-bes",
     "Çalışanların İşverenleri Aracılığıyla Otomatik Olarak Emeklilik Planına "
     "Dahil Edilmesine İlişkin Yönetmelik",
     "Çalışanların İşverenleri Aracılığıyla Otomatik Olarak Emeklilik Planına "
     "Dahil Edilmesine İlişkin Yönetmeliğin", []),
    ("tarimda-is-araciligi", "Tarımda İş Aracılığı Yönetmeliği",
     "Tarımda İş Aracılığı Yönetmeliği'nin", []),
]


def main() -> int:
    agac = {
        "surum": 2,
        "turler": [
            {
                "id": "kanun",
                "ad": "Kanun",
                "mevzuat": [
                    {"id": kimlik, "ad": ad, "atif": atif, "maddeler": maddeler}
                    for kimlik, ad, atif, maddeler in KANUNLAR
                ],
            },
            {
                "id": "yonetmelik",
                "ad": "Yönetmelik",
                "mevzuat": [
                    {"id": kimlik, "ad": ad, "atif": atif,
                     "maddeler": [
                         madde(*( (girdi, ()) if isinstance(girdi, str) else girdi ),
                               ceza="104")
                         for girdi in nolar
                     ]}
                    for kimlik, ad, atif, nolar in YONETMELIKLER
                ],
            },
            {"id": "cbk", "ad": "CBK", "mevzuat": []},
        ],
    }

    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    with HEDEF.open("w", encoding="utf-8") as hedef:
        json.dump(agac, hedef, ensure_ascii=False, indent=2)
        hedef.write("\n")

    toplam = sum(len(m["maddeler"]) for t in agac["turler"] for m in t["mevzuat"])
    mevzuat_sayisi = sum(len(t["mevzuat"]) for t in agac["turler"])
    print(f"İskelet yazıldı: {HEDEF}")
    print(f"  Mevzuat : {mevzuat_sayisi}")
    print(f"  Madde   : {toplam} (metinleri boş)")
    print("\nMetinleri doldurmak için:")
    print("  python tools/mevzuat_ice_aktar.py <pdf> <tur_id> <mevzuat_id>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

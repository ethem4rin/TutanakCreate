# -*- coding: utf-8 -*-
"""
Basit kullanıcı kimlik doğrulaması (kayıt / giriş).

Kullanıcılar Supabase'deki ``depo`` tablosunda ``kullanici:<kullanici_adi>`` kimliğiyle
saklanır. Şifreler werkzeug ile hash'lenir (düz metin tutulmaz). Oturum, Flask'ın
imzalı çerez tabanlı session'ı ile taşınır — sunucusuz (Vercel) ortamda da çalışır.

Kişiye özel veriler (öneriler, çalışmalar) ``<tur>:<kullanici_id>`` kimliğiyle
aynı ``depo`` tablosunda tutulur. Mevzuat ise ortak (``mevzuat``) kalır.
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Any, Dict, Optional

import requests
from werkzeug.security import check_password_hash, generate_password_hash

from core.mevzuat import SUPABASE_URL, SUPABASE_KEY, get_supabase_headers


class AuthHatasi(Exception):
    """İstemciye gösterilebilir kimlik doğrulama hatası."""


KULLANICI_ADI_DESENI = re.compile(r"^[a-z0-9ğüşıöç._-]{3,32}$")


def _kadi_normalize(kullanici_adi: str) -> str:
    # Türkçe duyarlı küçük harf + İ/I düzeltmesi
    k = (kullanici_adi or "").strip().replace("I", "ı").replace("İ", "i").lower()
    return re.sub(r"\s+", "", k)


def supabase_var() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


# --------------------------------------------------------------------------- #
# depo tablosu — genel KV erişimi
# --------------------------------------------------------------------------- #

def depo_oku(kimlik: str) -> Optional[Any]:
    if not supabase_var():
        return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/depo?id=eq.{kimlik}&select=veri"
        resp = requests.get(url, headers=get_supabase_headers(), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]["veri"]
    except Exception:
        pass
    return None


def depo_yaz(kimlik: str, veri: Any) -> bool:
    if not supabase_var():
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/depo"
        headers = get_supabase_headers()
        headers["Prefer"] = "resolution=merge-duplicates, return=minimal"
        resp = requests.post(url, headers=headers, json={"id": kimlik, "veri": veri}, timeout=10)
        return resp.status_code in (200, 201, 204)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Kullanıcılar
# --------------------------------------------------------------------------- #

def _kullanici_kimligi(kullanici_adi: str) -> str:
    return "kullanici:" + _kadi_normalize(kullanici_adi)


def kullanici_getir(kullanici_adi: str) -> Optional[Dict[str, Any]]:
    return depo_oku(_kullanici_kimligi(kullanici_adi))


def kayit(kullanici_adi: str, sifre: str) -> Dict[str, Any]:
    if not supabase_var():
        raise AuthHatasi("Sunucu veritabanı (Supabase) yapılandırılmamış; kayıt yapılamıyor.")
    kadi = _kadi_normalize(kullanici_adi)
    if not KULLANICI_ADI_DESENI.match(kadi):
        raise AuthHatasi("Kullanıcı adı 3-32 karakter olmalı; harf, rakam ve . _ - içerebilir.")
    if len(sifre or "") < 6:
        raise AuthHatasi("Şifre en az 6 karakter olmalıdır.")
    if kullanici_getir(kadi):
        raise AuthHatasi("Bu kullanıcı adı zaten alınmış. Başka bir ad deneyin ya da giriş yapın.")

    kayit_verisi = {
        "id": uuid.uuid4().hex,
        "kullanici_adi": kadi,
        "sifre_hash": generate_password_hash(sifre),
        "olusturma": int(time.time()),
    }
    if not depo_yaz(_kullanici_kimligi(kadi), kayit_verisi):
        raise AuthHatasi("Kayıt kaydedilemedi. Lütfen tekrar deneyin.")
    return {"id": kayit_verisi["id"], "kullanici_adi": kadi}


def giris(kullanici_adi: str, sifre: str) -> Dict[str, Any]:
    kadi = _kadi_normalize(kullanici_adi)
    kullanici = kullanici_getir(kadi)
    if not kullanici or not check_password_hash(kullanici.get("sifre_hash", ""), sifre or ""):
        raise AuthHatasi("Kullanıcı adı veya şifre hatalı.")
    return {"id": kullanici["id"], "kullanici_adi": kullanici.get("kullanici_adi", kadi)}


# --------------------------------------------------------------------------- #
# Kişiye özel veri (öneriler / çalışmalar)
# --------------------------------------------------------------------------- #

def kisisel_oku(tur: str, kullanici_id: str) -> Any:
    veri = depo_oku(f"{tur}:{kullanici_id}")
    return veri if veri is not None else []


def kisisel_yaz(tur: str, kullanici_id: str, veri: Any) -> bool:
    return depo_yaz(f"{tur}:{kullanici_id}", veri)

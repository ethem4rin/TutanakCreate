# -*- coding: utf-8 -*-
"""
Basit kullanıcı kimlik doğrulaması (kayıt / giriş).

Kullanıcılar Supabase'deki ``depo`` tablosunda ``kullanici:<eposta>`` kimliğiyle
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


EPOSTA_DESENI = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _eposta_normalize(eposta: str) -> str:
    return (eposta or "").strip().lower()


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

def _kullanici_kimligi(eposta: str) -> str:
    return "kullanici:" + _eposta_normalize(eposta)


def kullanici_getir(eposta: str) -> Optional[Dict[str, Any]]:
    return depo_oku(_kullanici_kimligi(eposta))


def kayit(ad: str, eposta: str, sifre: str) -> Dict[str, Any]:
    if not supabase_var():
        raise AuthHatasi("Sunucu veritabanı (Supabase) yapılandırılmamış; kayıt yapılamıyor.")
    ad = (ad or "").strip()
    eposta = _eposta_normalize(eposta)
    if not ad:
        raise AuthHatasi("Ad Soyad boş olamaz.")
    if not EPOSTA_DESENI.match(eposta):
        raise AuthHatasi("Geçerli bir e-posta adresi girin.")
    if len(sifre or "") < 6:
        raise AuthHatasi("Şifre en az 6 karakter olmalıdır.")
    if kullanici_getir(eposta):
        raise AuthHatasi("Bu e-posta ile zaten bir hesap var. Giriş yapın.")

    kayit_verisi = {
        "id": uuid.uuid4().hex,
        "ad": ad,
        "eposta": eposta,
        "sifre_hash": generate_password_hash(sifre),
        "olusturma": int(time.time()),
    }
    if not depo_yaz(_kullanici_kimligi(eposta), kayit_verisi):
        raise AuthHatasi("Kayıt kaydedilemedi. Lütfen tekrar deneyin.")
    return {"id": kayit_verisi["id"], "ad": ad, "eposta": eposta}


def giris(eposta: str, sifre: str) -> Dict[str, Any]:
    eposta = _eposta_normalize(eposta)
    kullanici = kullanici_getir(eposta)
    if not kullanici or not check_password_hash(kullanici.get("sifre_hash", ""), sifre or ""):
        raise AuthHatasi("E-posta veya şifre hatalı.")
    return {"id": kullanici["id"], "ad": kullanici.get("ad", ""), "eposta": eposta}


# --------------------------------------------------------------------------- #
# Kişiye özel veri (öneriler / çalışmalar)
# --------------------------------------------------------------------------- #

def kisisel_oku(tur: str, kullanici_id: str) -> Any:
    veri = depo_oku(f"{tur}:{kullanici_id}")
    return veri if veri is not None else []


def kisisel_yaz(tur: str, kullanici_id: str, veri: Any) -> bool:
    return depo_yaz(f"{tur}:{kullanici_id}", veri)

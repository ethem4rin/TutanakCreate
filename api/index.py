# -*- coding: utf-8 -*-
"""
Vercel sunucusuz giriş noktası.

Vercel, `api/` altındaki Python dosyalarını birer sunucusuz işlev olarak
çalıştırır ve WSGI uyumlu bir `app` nesnesi arar. Uygulamanın kendisi kök
dizindeki `app.py` içindedir; burada yalnızca içe aktarılır.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402,F401

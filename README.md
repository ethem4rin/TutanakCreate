# Müfettiş Programı — Noksanlık/Aykırılık Bildirimi

Teftiş tutanağını (.docx) yükleyip, tutanakta **kalın** yazılmış noksanlıkları
seçerek, her noksanlık için **ilgili mevzuat maddesi** ve **müfettiş önerisi**
belirleyip, örnek bildirimin biçimini birebir taşıyan Word belgesini üretir.

---

## Kurulum

```bash
pip install -r requirements.txt
```

Komut satırı araçlarını (mevzuat içe aktarma, şablon üretme) da kullanacaksanız:

```bash
pip install -r requirements-arac.txt
```

## Çalıştırma

```bash
python app.py
```

Tarayıcıdan **http://127.0.0.1:5000** adresini açın.
(Windows'ta `calistir.bat` dosyasına çift tıklamak da yeterlidir.)

VS Code kullanıyorsanız: klasörü açıp `app.py` üzerinde **F5** / *Run Python File*
demeniz yeterli.

---

## Akış

### 1. Aşama — Tutanak
Tutanak sürüklenip bırakılır. Program tutanaktan şunları otomatik okur:

| Alan | Kaynak |
|---|---|
| İşyeri unvanı | Künye tablosu → *İşveren/İşveren Vekili* (eğik çizgiden önceki kısım) |
| İşyeri adresi | Künye tablosu → *İşyerinin Adresi* |
| SGK / işyeri sicil no | Künye tablosu → *SGK Sicil No* (üst bilgiye yazılır) |
| Görev yazısı tarih/sayısı, program adı, teftiş tarihleri | Tutanağın giriş paragrafı |
| İş müfettişlerinin adları | Tutanağın imza tablosu |
| İşveren vekilinin adı ve görevi | Künye tablosu |
| Noksanlıklar | **Kalın (bold)** yazılmış, 80 karakterden uzun paragraflar |

Kalın yazılmış paragraflar noksanlık adayı olarak işaretli gelir.
Kalın yazılmamış bir tespiti de eklemek için **“Tüm paragrafları göster”**
düğmesiyle listeyi açıp ilgili paragrafa tıklayın.

### 2. Aşama — Noksanlıklar
Seçilen her noksanlık için üç adımlı bir kart açılır:

1. **Noksanlık maddesi** — tutanaktan gelir, metin düzenlenebilir.
   Baştaki `5.1-)` gibi madde numarası otomatik temizlenir.
2. **İlgili mevzuat maddesi (dayanak)** — “Dayanak Seç” penceresi açılır.
   Bakanlığın kendi ekranındaki gibi **Mevzuat Türü → Mevzuat → Madde**
   şeklinde ilerlenir. Pencere, noksanlık metnindeki anahtar kelimelere göre
   eşleşen maddeleri gösteren **Önerilenler** sekmesiyle açılır.
   Bir noksanlığa birden çok dayanak bağlanabilir (kanun + yönetmelik birlikte).
3. **Müfettiş önerisi** — kütüphaneden seçilir, metni düzenlenebilir.

### 3. Aşama — Belge
Yazı sayısı/tarihi, teftişe ara verme tarih-saati ve *Tebellüğ Eden* bilgileri
girilir. **Önizle** ile kontrol edilip **Word Belgesini Oluştur** ile indirilir.

Çalışma tarayıcıda saklanır; sayfayı kapatıp açsanız da kaldığınız yerden
devam edersiniz. Sol alttaki yenileme düğmesi her şeyi sıfırlar.

---

## Mevzuat kütüphanesi

`data/mevzuat.json` dosyasında, Bakanlığın **“Dayanak Seç”** ekranındaki
kademeli düzende tutulur:

```
Mevzuat Türü  →  Mevzuat                          →  Madde      (+ Ceza Maddesi)
Kanun            4857 - İş Kanunu                    63            104
Yönetmelik       Yıllık Ücretli İzin Yönetmeliği     6(8)          104
CBK              …                                   …
```

Bir noksanlığa **birden çok dayanak** bağlanabilir; kanun ve yönetmelik maddesi
yan yana yazılır. Örnek bildirimdeki 1. noksanlıkta olduğu gibi:

```
1-  İşyerinde çalışan işçilerin günlük, haftalık ve aylık çalışma sürelerinin …
    4857 sayılı İş Kanunu'nun Çalışma süresi başlıklı 63. maddesinde; “…” Hükmü amirdir.
    İş Kanunu'na İlişkin Fazla Çalışma … Yönetmeliği'nin Fazla Çalışmada Sınır
    başlıklı 5. maddesinde; “…” Hükmü amirdir.
    Buna göre; a) tutanak tarihi itibariyle …
```

### Madde metinleri nereden geliyor

Hepsi **mevzuat.gov.tr'nin resmî PDF'lerinden** otomatik aktarılır; elle
yazılmaz. Kaynak dosyalar `mevzuat_pdf/` klasöründedir.

| | |
|---|---|
| Kanun | 9 (4857, 6331, 6735, 6356, 5544, 4447, 4632, 4904, 854) |
| Yönetmelik | 12 |
| Toplam madde | 81 |
| Metni dolu | 50 — 4857'nin 34 maddesi, Yıllık Ücretli İzin Yön. 11, Çalışma Süreleri Yön. 3, Fazla Çalışma Yön. 2 |
| Metni boş | 31 — madde numarası ve ceza maddesi girili, metin bekliyor |

Kütüphaneyi kurmak iki adımdır:

```bash
python tools/mevzuat_kur.py                                      # iskelet (mevzuat + madde no + anahtar kelimeler)
python tools/mevzuat_ice_aktar.py "mevzuat_pdf/4857 - İş Kanunu.pdf" kanun 4857
```

> `mevzuat_kur.py` dosyayı **sıfırdan yazar** — aktarılmış metinler ve elle
> yapılan düzenlemeler silinir. Normalde çalıştırmanız gerekmez.

### Yeni mevzuat eklemek

1. mevzuat.gov.tr'de mevzuatı açın, sayfanın üstündeki **PDF** simgesinden
   indirip `mevzuat_pdf/` klasörüne koyun.
2. Mevzuat kütüphanede yoksa arayüzden **Kütüphane → Yeni kanun / yönetmelik**
   ile ekleyin (atıf biçimini ek çekimiyle yazın: “…Kanunu**'nun**”,
   “…Yönetmeliği**'nin**”).
3. Metinleri aktarın:

```bash
python tools/mevzuat_ice_aktar.py "mevzuat_pdf/<dosya>.pdf" yonetmelik <mevzuat_id> --maddeler 5,9
```

`--maddeler` verilmezse kütüphanede kayıtlı maddelerin metni doldurulur;
verilirse o maddeler (kayıtlı değilse eklenerek) aktarılır. `--deneme` ile
dosyaya yazmadan önizleyebilirsiniz.

Ayıklayıcı iki PDF biçimini de tanır: kanunların girintili dizgisini ve
yönetmeliklerin HTML'den üretilmiş akış dizgisini. Dipnotları, değişiklik
şerhlerini (“(Ek cümle: 10/9/2014-6552/7 md.)”), bölüm başlıklarını ve sayfa
numaralarını temizler.

### Fıkra bazlı maddeler

Bakanlık sistemindeki gibi fıkraya atıf yapılabilir: `92/2`, `3/(2)`, `6(8)`,
`13(1)`. Aktarıcı o fıkranın metnini alır ve atfı doğru Türkçeyle kurar —
*“6. maddesinin 8. fıkrasında”*, “6(8). maddesinde” değil.

Fıkra sınırı PDF'in paragraf düzeninden çıkarıldığı için bu kayıtlar arayüzde
`fıkra` rozetiyle işaretlenir; eklemeden önce önizlemeden metni görün.

### Elle düzenleme

Arayüzde bir maddeye tıklayıp metnini değiştirebilirsiniz. Metni boş olan
maddeler `metin yok` rozetiyle görünür ve seçilemez; tıklayınca düzenleme
penceresi açılır. Metni yapıştırıp **“Paragrafı kalıptan yaz”** düğmesine
basmak yeterli:

```
İş Kanununa İlişkin Çalışma Süreleri Yönetmeliği'nin **Çalışma Süresi**
başlıklı 3. maddesinde; “…yapıştırdığınız metin…” Hükmü amirdir.
```

Kapanış kalıbı: *Hükmü amirdir.* · *Hükmü,* · *hükmüne yer verilmiştir.*

> Ceza maddesi alanı yapıda vardır ama noksanlık bildiriminde kullanılmaz —
> yalnızca Bakanlık sistemindeki karşılığıyla eşleşsin diye tutulur.

## Müfettiş önerileri kütüphanesi

Öneriler **kendi tarayıcınızda** saklanır (`localStorage`), sunucuda değil.
Her müfettiş kendi kalıplarını oluşturur; kurulu gelen hazır öneri yoktur.
Böylece Vercel'de de (dosya sistemi salt okunurken) ekleme ve düzenleme
çalışır.

**Kütüphane → Müfettiş Önerileri** sekmesinden eklenir, düzenlenir, silinir.
Noksanlık metnindeki anahtar kelimelere göre en ilgili öneriler seçim
penceresinde en üste gelir.

> **Yedek alın.** Tarayıcı verisi silinirse öneriler de gider.
> **Yedekle** düğmesi tüm önerileri `mufettis-onerileri.json` olarak indirir,
> **Yedekten yükle** geri alır. Aynı dosyayı başka bir bilgisayarda yükleyerek
> kalıplarınızı taşıyabilirsiniz.

Metinlerde hafif biçimlendirme işaretleri kullanılır:

| İşaret | Sonuç | Kullanım |
|---|---|---|
| `**metin**` | **kalın** | Vurgu |
| `__metin__` | **_kalın + italik + altı çizili_** | “Buna göre;” kalıbı |

Örnek öneri kaydı:

```
__Buna göre;__ a) tutanak tarihi itibariyle işyerinde çalışma düzeninin
haftalık 45 saati aşmayacak şekilde uygulanması … sağlanmalıdır.
```

## Üretilen belgenin biçimi

Belge, örnek bildirimden türetilen `sablon/noksanlik_bildirimi_sablon.docx`
üzerinden kurulur. Şablon; **stilleri, yazı tipini (Times New Roman 11 pt),
numaralandırma tanımlarını, satır aralıklarını (1,15), girintileri (0,99 cm),
paragraf aralıklarını (6 nk), iki yana yaslamayı, sayfa kenar boşluklarını,
üst bilgiyi (T.C. Çalışma ve Sosyal Güvenlik Bakanlığı tablosu + işyeri sicil
no) ve alt bilgiyi** olduğu gibi taşır.

Her noksanlık bloğu şu paragraflardan oluşur:

```
1-  <noksanlık metni>                 → Liste Paragraf, kalın, otomatik "1-, 2-, 3-"
    <mevzuat maddesi>                 → sekme + metin, madde başlığı kalın
    Buna göre; <müfettiş önerisi>     → sekme + metin, "Buna göre;" kalın/italik/altı çizili
```

Doğrulama için:

```bash
python tools/dogrula.py
```

Örnek tutanaktan üretilen belgeyi örnek bildirimle paragraf paragraf
karşılaştırır (stil, hizalama, girinti, aralık, kalın/italik/altı çizili,
punto) ve raporu `calisma/cikti/_dogrulama_raporu.txt` dosyasına yazar.

Şablonu örnek bildirimden yeniden üretmek için:

```bash
python tools/sablon_olustur.py
```

---

## Vercel'de yayınlama

Depo, Vercel'in **Flask** ön ayarıyla sıfır yapılandırma çalışacak şekilde
düzenlenmiştir. Vercel kökteki `app.py` dosyasında `app` adlı Flask örneğini
bulur ve uygulamayı tek bir Vercel Function'a dönüştürür.

| Dosya / klasör | İşlevi |
|---|---|
| `app.py` | Flask giriş noktası — Vercel'in aradığı yer |
| `public/` | CSS ve JS; Vercel bunları CDN'den sunar, işleve hiç uğramaz |
| `vercel.json` | Şablon, veri ve çekirdek modülleri işlev paketine ekler |
| `.vercelignore` | Örnek belgeler, mevzuat PDF'leri ve araçlar pakete girmez |
| `requirements.txt` | Yalnızca Flask ve python-docx (PyMuPDF sadece araçlar için) |

Yayınlamak için Vercel'de **Add New → Project** deyip bu depoyu seçin.
Application Preset **Flask** olarak gelir, Root Directory `./` kalır;
build komutu ve ortam değişkeni gerekmez. **Deploy**'a basmanız yeterli.

> Statik dosyalar Flask'ın `static/` klasöründe değil `public/` altındadır:
> Vercel, Flask uygulamalarında `app.static_folder` yerine `public/**`
> kullanılmasını önerir. Flask yerelde de aynı adreslerden (`/css/app.css`)
> sunacak şekilde yapılandırılmıştır, bu yüzden iki ortam da aynı çalışır.

### Sunucusuz ortamda neler değişir

Vercel'de dosya sistemi salt okunurdur. Uygulama bunu açılışta algılar
(`/api/ortam`) ve davranışını buna göre ayarlar:

| | Yerel | Vercel |
|---|---|---|
| Tutanak yükleme ve çözümleme | ✔ | ✔ (bellekte, diske yazılmaz) |
| Dayanak ve öneri seçimi | ✔ | ✔ |
| Word bildirimi üretme ve indirme | ✔ | ✔ (bellekte üretilir) |
| Üretilen bildirimin arşiv kopyası | ✔ `calisma/cikti/` | — |
| Müfettiş önerisi ekleme, düzenleme | ✔ | ✔ (tarayıcıda saklanır) |
| Mevzuat maddesi metni düzenleme | ✔ | ✘ salt okunur |

Kütüphane düzenlemesi Vercel'de kapalıdır; arayüz bunu sarı bir not ve pasif
düğmelerle belirtir. Mevzuat veya öneri eklemek için değişikliği kendi
bilgisayarınızda yapıp `data/*.json` dosyalarını depoya gönderin — yeni
dağıtım otomatik alınır.

Yüklenen tutanak sunucuda hiçbir zaman saklanmaz; bellekte çözümlenip atılır.

> Vercel'in ücretsiz planında istek gövdesi sınırı yaklaşık 4,5 MB'tır.
> Normal bir tutanak bunun çok altındadır.

## Klasör düzeni

```
app.py                     Flask uygulaması ve API uçları (Vercel giriş noktası)
core/
  tutanak.py               Tutanak çözümleyici (künye + noksanlık adayları)
  belge.py                 Word bildirimi üreteci
  mevzuat.py               Kademeli mevzuat ağacı (gezinme, arama, öneri, CRUD)
  mevzuat_pdf.py           mevzuat.gov.tr PDF'lerinden madde metni ayıklayıcı
  metin.py                 **kalın** / __altı çizili__ işaret çözümleyici
data/
  mevzuat.json             Mevzuat ağacı (tür → mevzuat → madde)
mevzuat_pdf/               mevzuat.gov.tr'den indirilen resmî PDF'ler
sablon/
  noksanlik_bildirimi_sablon.docx    Biçimi taşıyan Word şablonu
ornek/                     Referans tutanak ve bildirim (depoya gönderilmez)
public/ templates/         Arayüz (saf CSS + JS, derleme adımı yok)
tools/
  sablon_olustur.py        Şablonu örnek bildirimden üretir
  mevzuat_kur.py           data/mevzuat.json iskeletini sıfırdan kurar
  mevzuat_ice_aktar.py     Resmî PDF'ten madde metinlerini aktarır
  dogrula.py               Üretilen belgeyi örnekle karşılaştırır
calisma/                   Yüklenen tutanaklar ve üretilen belgeler
```

---

## Bilinen sınırlar

* İmza tablosu örnek bildirimdeki gibi **en fazla iki iş müfettişi** taşır.
  Üçten fazla müfettişin imzalaması gerekirse tablo Word'de elle genişletilmelidir.
* Şablonun alt bilgisindeki adres, telefon ve faks **İstanbul Rehberlik ve
  Teftiş Grup Başkanlığına** aittir. Başka bir grup başkanlığında
  kullanacaksanız `sablon/noksanlik_bildirimi_sablon.docx` dosyasını Word'de
  açıp alt bilgiyi düzenleyin. E-posta adresi arayüzden girilir.
* `ornek/` klasöründeki referans belgeler gerçek kişi ve şirket bilgileri
  taşıdığı için depoya gönderilmez. `tools/dogrula.py` ve
  `tools/sablon_olustur.py` bu klasöre ihtiyaç duyar; depoyu klonlayan biri
  bu iki aracı çalıştıramaz, programın kendisi etkilenmez.

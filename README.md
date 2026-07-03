# Gemini Toplu Görsel Üretici

Excel listesi + referans görsellerden yola çıkarak, Google Gemini görsel üretim
API'si (`gemini-2.5-flash-image`) ile toplu, isme özel görseller üreten
Flask + HTML/CSS/JS uygulaması.

## Nasıl çalışır?

1. **Excel yükle** — Görsellerle eşleştirilecek bir sütun içeren `.xlsx`, `.xls`
   ya da `.csv` dosyası yükle (örn. "Ürün Adı", "Kod" gibi bir sütun).
2. **Görselleri yükle** — Dosya adları (uzantısız), seçtiğin excel sütunundaki
   değerlerle eşleşen referans görselleri toplu olarak yükle.
   Örn: `Kirmizi Sandalye.jpg` ↔ satırdaki `Kirmizi Sandalye` değeri.
3. **Prompt şablonu yaz** — Excel sütunlarını `{Sütun Adı}` şeklinde yer tutucu
   olarak kullanarak tek bir prompt şablonu yaz; her satır için otomatik
   doldurulur.
4. **Grubu oluştur** — Excel satırları ile görseller eşleştirilir, her biri
   için kişiselleştirilmiş prompt üretilir.
5. **Üret** — "Tümünü Üret" ile toplu üretim başlar; görseller tamamlandıkça
   sayfada dinamik olarak listelenir. Her kartın altındaki **Tekrarla**
   butonuyla istediğin görseli yeniden üretebilirsin.
6. **İndir** — "Tümünü ZIP indir" butonu ile tüm üretilen görselleri,
   belirlediğin klasör adıyla tek bir zip dosyası olarak indirebilirsin.

Eşleşen görseli olmayan excel satırları da yalnızca prompt metni kullanılarak
üretilebilir; eşleşmeyen görsel dosyaları ise uyarı olarak listelenir.

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env` dosyasını açıp `GEMINI_API_KEY` değerine
[Google AI Studio](https://aistudio.google.com/apikey) üzerinden aldığın
API anahtarını yaz. Anahtarı `.env` yerine, uygulama açıldıktan sonra sağ
üstteki **⚙️ API Ayarları** panelinden de geçici olarak girebilirsin (yalnızca
sunucu belleğinde tutulur, diske yazılmaz).

## Çalıştırma

```bash
python app.py
```

Ardından tarayıcıdan `http://127.0.0.1:5000` adresini aç.

## Proje yapısı

```
app.py                     Flask uygulaması ve API rotaları
config.py                  Ortam değişkenleri ve sabitler
utils.py                   Dosya adı temizleme yardımcıları
services/
  excel_service.py         Excel/CSV okuma ve önizleme
  matching.py               Görsel–satır eşleştirme ve prompt render
  gemini_service.py         Gemini görsel üretim API çağrıları
  batch_store.py            Bellek + disk üzerinde iş (batch) takibi
  zip_service.py            Üretilen görselleri zip'leme
templates/index.html        Tek sayfalık arayüz
static/css/style.css        Arayüz stilleri
static/js/app.js            Arayüz mantığı (fetch tabanlı SPA akışı)
data/                       Çalışma zamanı yüklemeleri ve üretilen görseller
```

## Notlar

- Görsel üretim modeli `.env` içindeki `GEMINI_IMAGE_MODEL` ile
  değiştirilebilir (varsayılan: `gemini-2.5-flash-image`).
- Uygulama tek kullanıcılı yerel kullanım için tasarlanmıştır; iş (batch)
  verileri bellekte ve `data/batches/<batch_id>/state.json` içinde tutulur.
- Excel'de eşleşme sütunu için değerler, dosya adlarıyla (uzantısız, boşluk/
  alt çizgi/tire farkları normalize edilerek) karşılaştırılır.

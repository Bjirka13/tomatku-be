# Kesesuaian Output

## Ringkasan

Hasil evaluasi menunjukkan bahwa output model dan frontend belum sepenuhnya langsung cocok dengan schema database. Secara umum:

- Model pipeline sudah cocok untuk `severity_level` dan `severity_pct`
- Schema DB membutuhkan `classification` dan `confidence_pct` yang saat ini belum diproduksi secara eksplisit oleh pipeline
- Frontend memang memakai konsep persentase dan label klasifikasi, tetapi format UI-nya perlu dikonversi agar sesuai dengan format yang disimpan di DB

Kesimpulan utama: `output model` perlu dibungkus oleh backend sebelum disimpan ke tabel `detection_logs`, dan frontend perlu membaca data dari database dengan mapping label yang sesuai.

---

## 1. Schema database yang harus dipenuhi

Berdasarkan file `tomatku-be/db/init.sql`:

```sql
CREATE TABLE IF NOT EXISTS detection_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    classification TEXT NOT NULL,
    confidence_pct NUMERIC(5, 2) NOT NULL,
    severity_level TEXT NOT NULL,
    severity_pct NUMERIC(5, 2) NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT detection_logs_classification_valid
        CHECK (classification IN ('healthy', 'early_blight', 'unknown')),
    CONSTRAINT detection_logs_confidence_valid
        CHECK (confidence_pct >= 0 AND confidence_pct <= 100),
    CONSTRAINT detection_logs_severity_level_valid
        CHECK (severity_level IN ('normal', 'ringan', 'sedang', 'parah')),
    CONSTRAINT detection_logs_severity_valid
        CHECK (severity_pct >= 0 AND severity_pct <= 100)
);
```

### Persyaratan DB yang penting

- `classification` harus salah satu: `healthy`, `early_blight`, atau `unknown`
- `confidence_pct` harus berupa angka 0 sampai 100
- `severity_level` harus salah satu: `normal`, `ringan`, `sedang`, atau `parah`
- `severity_pct` harus berupa angka 0 sampai 100

---

## 2. Output model saat ini

Berdasarkan file `tomatku-be/artifact/external_pipeline.py`, method `analyze()` mengembalikan payload seperti ini:

```python
return {
    "severity_level": severity_level,
    "severity_pct": round(float(severity_pct), 2),
    "leaf_pixels": leaf_pixels,
    "symptom_pixels": symptom_pixels,
    "leaf_mask": leaf_mask,
    "symptom_mask": symptom_mask,
}
```

### Cek kesesuaian

#### Cocok dengan DB

- `severity_level` = `normal | ringan | sedang | parah` ✅
- `severity_pct` = persentase, dibulatkan ke 2 desimal ✅

#### Belum cocok dengan DB

- Tidak ada `classification` ✅ tidak ada
- Tidak ada `confidence_pct` ✅ tidak ada

Jadi, output model saat ini belum bisa disimpan langsung ke `detection_logs` tanpa transformasi backend.

---

## 3. Kesesuaian dengan mapping model

Dalam `DEFAULT_CONFIG`:

```python
"model_class_mapping": {
    "0": "early_blight",
    "1": "healthy",
}
```

Fungsi `_normalize_classification()` juga mendukung:

```python
if value in {"healthy", "1"}:
    return "healthy"

if value in {"early_blight", "earlyblight", "0"}:
    return "early_blight"

if value == "unknown":
    return "unknown"
```

Artinya, model dan pipeline memang berorientasi pada klasifikasi dengan nilai:

- `healthy`
- `early_blight`
- `unknown`

Ini sudah konsisten dengan validasi database.

---

## 4. Kesesuaian di backend

Backend yang ideal harus menerima output model lalu memetakan ke format DB seperti ini:

```json
{
  "classification": "healthy",
  "confidence_pct": 87.5,
  "severity_level": "normal",
  "severity_pct": 8.42,
  "detected_at": "2026-09-23T12:00:00Z"
}
```

### Catatan penting

- `severity_pct` dari pipeline sudah dalam bentuk persen, dan nilainya 0-100, sehingga cocok untuk DB
- `confidence_pct` harus dihitung/diambil dari model atau dari confidence score model, bukan dibuat sembarangan
- `classification` harus berasal dari model output atau normalisasi kelas

### Kesimpulan backend

Backend perlu menambahkan mapping dan validasi seperti:

- model class -> `classification`
- model probability -> `confidence_pct`
- pipeline severity -> `severity_level`, `severity_pct`

Tanpa langkah ini, output pipeline belum valid untuk insert ke `detection_logs`.

---

## 5. Kesesuaian dengan frontend

Frontend di `tomatku-fe/src/utils/dummyData.ts` memakai field seperti:

```ts
healthyPercent: number;
earlyBlightPercent: number;
unknownPercent: number;
```

Dan di UI, chart memakai:

```ts
const healthyStroke = (currentStats.healthyPercent / 100) * circumference;
```

Artinya frontend memang memakai format persen `0-100` untuk display. Ini cocok untuk tampilan UI, tetapi tidak cocok untuk format tabular DB yang harus disimpan dalam bentuk `classification` + `confidence_pct` + `severity_pct`.

### Mapping yang perlu dipakai

| Database | Frontend/UI |
|---|---|
| `healthy` | Healthy |
| `early_blight` | Early Blight |
| `unknown` | Unknown |
| `severity_level = normal` | Normal |
| `severity_level = ringan` | Mild / Light |
| `severity_level = sedang` | Moderate |
| `severity_level = parah` | Severe |

Jadi frontend memang dapat menampilkan data dari DB, tapi perlu mapping label dan konversi persen apabila input datang dalam bentuk desimal/probabilitas.

---

## 6. Evaluasi final

### Status kesesuaian

#### Sesuai

- `severity_level` model ↔ DB valid values ✅
- `severity_pct` model ↔ DB numeric percent range ✅
- `classification` concept dari model ↔ DB valid values ✅
- `healthy` / `early_blight` / `unknown` naming concept ↔ DB ✅

#### Belum langsung sesuai

- output model belum punya `classification` ✅ belum ada
- output model belum punya `confidence_pct` ✅ belum ada
- output model belum dalam format siap insert DB ✅ belum siap

### Kesimpulan akhir

Model pipeline dan schema DB secara konsep sudah selaras, tetapi `output model` saat ini bukan payload final yang cocok untuk DB. Diperlukan layer backend untuk:

1. mengambil hasil model
2. menentukan `classification`
3. menghitung atau menyalurkan `confidence_pct`
4. memetakan `severity_level` dan `severity_pct`
5. menyimpan ke `detection_logs`

Dengan begitu, alur yang benar adalah:

`model -> backend normalization -> database -> frontend display`

bukan:

`model output langsung -> database`

---

## Format payload rekomendasi

```json
{
  "scan_id": "<uuid>",
  "classification": "early_blight",
  "confidence_pct": 91.24,
  "severity_level": "parah",
  "severity_pct": 42.7,
  "detected_at": "2026-09-23T12:34:56Z"
}
```

Payload seperti ini sudah sesuai dengan validasi schema `detection_logs`.
